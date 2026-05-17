# BRStock Neon DB Network 流量优化记录

## 背景

BRStock 生产环境使用 Neon PostgreSQL 作为行情、用户、回测等数据的主数据库。近期 Neon DB Network 流量异常偏高。虽然 Yahoo Finance 行情拉取频率已经降低到工作日收盘后一次，但 DB network 流量仍然可能被后端的读写方式放大。

本次优化重点不是继续降低外部行情 API 调用频率，而是减少应用与 Neon 之间不必要的数据传输。

## 主要问题

### 1. 写入行情时全表回读再全量重写

原 `StockDB.save_stock_data()` 在表存在时会：

1. `SELECT * FROM "{table_name}"` 读取整张历史表。
2. 在 Python 内存中 concat、去重、排序。
3. `DROP TABLE`。
4. 再把完整 DataFrame 写回 DB。

这会导致每次更新一只股票，都可能把该股票的完整历史行情从 Neon 拉到 Cloud Run，再完整写回 Neon。即使 Yahoo 只在收盘后拉一次，Neon network 仍然会按“全量历史表”反复计算。

### 2. 多个接口按超大 limit 读取历史数据

一些接口存在“先从 DB 拉很多行，再在 Python 过滤/计算”的模式：

- 策略回测读取 `limit=100000`。
- 期权回测读取 `limit=10000`。
- 日线 history/indicators 默认会拉较多历史数据。
- analysis、summary 等接口读取了超过实际需要的列。

这些查询在用户频繁打开图表、指标、回测页面时，会反复产生 Neon -> Cloud Run 的 outbound data transfer。

### 3. 缺少 Cloud Run 实例内缓存和本地读缓存

Cloud Run 同一个实例内的重复请求本可以直接复用内存结果。此前每次请求都会重新走 DB 查询。

同时，Cloud Run 的 `/tmp` 在实例生命周期内可复用，也适合做 read-through 文件缓存。此前未使用。

### 4. Yahoo/Schwab 行情 refresh 仍有全量拉取路径

虽然调度频率降低了，但代码路径中仍存在：

- Yahoo fallback: `5m=60d`、`1d=max`
- Data pipeline job: `5m=30d`、`1d=30y`
- Schwab price history: 固定窗口拉取

这会增加外部 API 请求的数据量，也会增加后续写 DB 的数据量。

## 已完成优化

### 1. Postgres/Neon 写入改为增量 merge

文件：

- `internal/db_client/database.py`

优化后，Postgres/Neon 路径不再全表回读、全表重写。新的写入流程：

1. 将新拉取的数据写入临时表。
2. 按 `timestamp` 删除目标表中冲突的旧行。
3. 从临时表插入新行。
4. 删除临时表。
5. 清理本地缓存。

核心效果：

- 避免 `SELECT *` 拉完整历史表。
- 避免 `DROP TABLE` 后全量重建。
- DB network 从“每次搬完整历史表”下降为“只上传本次新增/更新的行情行”。

### 2. DB 读取支持日期范围和列裁剪

文件：

- `internal/db_client/database.py`

`get_stock_data()` 新增参数：

```python
get_stock_data(table_name, limit=1000, start=None, end=None, columns=None)
```

优化能力：

- `start/end`：只读取请求日期区间。
- `columns`：只读取业务需要的字段，例如只算 RSI/MACD 时只读 `Close`。
- `limit=None`：用于明确按日期范围读取，不再依赖巨大 limit。

典型效果：

- 指标接口只取 `Close`，不再拉 `Open/High/Low/Volume`。
- analysis 只取最近 100 条 `Close`。
- 回测只取用户指定时间范围内的 OHLCV。

### 3. 策略回测避免读取 100000 行

文件：

- `services/backend_api/routes/strategies.py`

优化前：

```python
cached = db.get_stock_data(table_name, limit=100000)
filtered = cached[(cached.index.date >= start) & (cached.index.date <= end)]
```

优化后：

```python
cached = db.get_stock_data(
    table_name,
    limit=None,
    start=start,
    end=end,
    columns=["Open", "High", "Low", "Close", "Volume"],
)
```

同时新增 `get_stock_data_bounds()`，用单行 `MIN(timestamp), MAX(timestamp)` 判断表覆盖范围，避免为了判断覆盖范围读取全量数据。

### 4. 期权回测按区间读取

文件：

- `services/backend_api/options_synth.py`

Wheels、LEAPS、spread 等期权回测从 `limit=10000` 改为：

- 按 `start_date/end_date` 读取。
- 只读 `Open/High/Low/Close/Volume`。

这样长历史表不会因为一次短区间回测被完整传输到后端。

### 5. 股票接口列裁剪

文件：

- `services/backend_api/routes/stocks.py`

已优化接口包括：

- history：只读 OHLCV。
- indicators：只读 `Close`。
- summary：只读 OHLCV 最近窗口。
- analysis：只读最近 100 条 `Close`。
- refresh 前 freshness check：只读最新一条 `Close`。

这类优化对高频页面访问尤其有效，因为图表和仪表盘通常会重复访问这些接口。

### 6. Cloud Run 实例内 memory cache

文件：

- `internal/db_client/database.py`

新增实例内 LRU cache。查询命中顺序：

1. Cloud Run 实例内存 cache。
2. `/tmp` 本地文件 cache。
3. Neon DB。

配置项：

```bash
DB_MEMORY_QUERY_CACHE=1
DB_MEMORY_QUERY_CACHE_TTL_SECONDS=900
DB_MEMORY_QUERY_CACHE_MAX_ENTRIES=256
```

默认策略：

- 仅在 Postgres/Neon 连接时启用。
- TTL 默认 15 分钟。
- 最多缓存 256 个查询结果。
- 写入行情后清空内存 cache，避免读取旧数据。

适用场景：

- 同一 Cloud Run 实例上用户反复刷新同一个图表。
- Dashboard 同一批 ticker 多次请求 summary/indicators。
- 短时间内重复执行相同回测参数。

### 7. Cloud Run `/tmp` 本地文件 cache

文件：

- `internal/db_client/database.py`

新增 read-through 文件缓存，缓存路径默认：

```bash
/tmp/brstock_db_query_cache
```

配置项：

```bash
DB_LOCAL_QUERY_CACHE=1
DB_LOCAL_QUERY_CACHE_TTL_SECONDS=86400
DB_LOCAL_QUERY_CACHE_DIR=/tmp/brstock_db_query_cache
```

默认建议：

- 行情只在工作日收盘更新一次时，TTL 可设置为 `86400` 秒。
- Cloud Run 实例存活期间，重复查询可以直接从 `/tmp` 读取。
- 写入行情后会清空缓存。

### 8. 部署脚本接入缓存配置

文件：

- `deploy_all.sh`
- `.env`
- `.env.example`

`deploy_all.sh` 会从 `.env` 读取以下配置，并注入 Cloud Run：

```bash
DB_LOCAL_QUERY_CACHE
DB_LOCAL_QUERY_CACHE_TTL_SECONDS
DB_LOCAL_QUERY_CACHE_DIR
DB_MEMORY_QUERY_CACHE
DB_MEMORY_QUERY_CACHE_TTL_SECONDS
DB_MEMORY_QUERY_CACHE_MAX_ENTRIES
```

当前推荐配置：

```bash
DB_LOCAL_QUERY_CACHE=1
DB_LOCAL_QUERY_CACHE_TTL_SECONDS=86400
DB_LOCAL_QUERY_CACHE_DIR=/tmp/brstock_db_query_cache

DB_MEMORY_QUERY_CACHE=1
DB_MEMORY_QUERY_CACHE_TTL_SECONDS=900
DB_MEMORY_QUERY_CACHE_MAX_ENTRIES=256
```

### 9. Yahoo Finance 改为增量拉取

文件：

- `services/backend_api/routes/stocks.py`
- `services/data_pipeline/fetch_data.py`

优化前：

- API fallback 每次可能拉 `5m=60d`、`1d=max`。
- Pipeline job 每次可能拉 `5m=30d`、`1d=30y`。

优化后：

1. 先读取本地/DB 中该 ticker 对应表的最新 timestamp。
2. 如果已有数据：
   - 1d 从最新日线前 1 天开始拉。
   - 5m 从最新 5 分钟线前 5 分钟开始拉。
   - 拉回后只保留 `timestamp > latest_timestamp` 的新行。
3. 如果没有数据，才执行首次历史初始化：
   - API fallback 初始化仍可拉较大历史。
   - Pipeline 初始化拉 `1d=30y`、`5m=30d`。

这样日常收盘后任务通常只会拉当天或最近少量数据。

### 10. Schwab price history 同步改为增量

文件：

- `services/backend_api/schwab_market_data.py`
- `services/backend_api/routes/stocks.py`

Schwab provider 新增 `start_datetime/end_datetime` 支持，会转换为 Schwab API 的 `startDate/endDate` 毫秒时间戳。

API refresh 主路径现在也会基于最新 timestamp 增量拉取，而不是固定窗口拉取。

## 流量下降点总结

| 优化点 | 优化前 | 优化后 | 主要降低的流量 |
|---|---|---|---|
| 行情写入 | 全表回读 + 全表重写 | 临时表增量 merge | Neon read + write |
| 策略回测 | 读 100000 行再过滤 | SQL 按日期区间读取 | Neon read |
| 期权回测 | 读 10000 行再过滤 | SQL 按日期区间读取 | Neon read |
| 指标/分析 | 读取多余列 | 只读必要列 | Neon read |
| 重复查询 | 每次请求 DB | memory cache + `/tmp` cache | Neon read |
| Yahoo refresh | 固定大窗口/全量 | 基于最新 timestamp 增量 | 外部 API + DB write |
| Schwab refresh | 固定窗口 | 基于最新 timestamp 增量 | 外部 API + DB write |

## 性能收益

预期性能改善主要体现在：

1. API 延迟降低  
   缓存命中时不需要等待 Neon 查询，图表/指标类接口响应会更快。

2. Cloud Run CPU 和内存压力降低  
   避免在 Python 中处理完整历史表，减少 DataFrame concat/filter 的成本。

3. Neon network 流量降低  
   高频查询由 cache 承接，低频查询也只传必要区间和列。

4. Neon 写入压力降低  
   增量 merge 避免全表 drop/recreate，写入数据量显著减少。

5. 外部行情 API 数据量降低  
   日常更新只拉新增 bar，而不是反复拉 30 天、60 天或 max 历史。

## 当前注意事项

### Cloud Run cache 是实例级的

Cloud Run 横向扩容后，每个实例都有自己的内存 cache 和 `/tmp` cache。因此：

- cache 命中率取决于请求是否落在同一个实例。
- 实例冷启动后 cache 会重新建立。
- 这属于性能优化，不是持久化数据源。

### 写入会清空本地缓存

每次 `save_stock_data()` 写入 Postgres/Neon 后，会清空内存和 `/tmp` query cache，避免读到旧数据。

当前实现为清空整个 query cache，而不是只清某个 ticker 的相关 key。这样更保守，逻辑简单，避免 cache key 反查复杂度。

### 空库首次初始化仍然会拉历史

增量拉取依赖已有最新 timestamp。首次部署或新 ticker 第一次加入时，仍需要初始化历史数据。这是必要成本。

## 建议后续优化

### 1. 增加 ticker 级缓存失效

当前写入后清空整个 cache。后续可以让 cache key 带 table 前缀索引，实现只清理被写入 ticker 对应的缓存。

### 2. 为行情表加唯一索引

如果 Neon 表结构允许，建议为每张行情表加：

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_<table>_timestamp ON "<table>" (timestamp);
```

后续可将 `DELETE + INSERT` 改为 PostgreSQL `ON CONFLICT DO UPDATE`，写入更标准，也更快。

### 3. 统一行情表结构

当前每个 ticker 一个表，例如 `aapl_1d`、`qqq_5m`。长期看可以考虑统一为：

```text
market_bars(ticker, interval, timestamp, open, high, low, close, volume)
```

并建立复合索引：

```sql
(ticker, interval, timestamp)
```

这样更便于批量查询、缓存和维护 schema。

### 4. 前端请求去重

如果前端 dashboard 同时触发多个相同接口，可以在 `services/web_ui/app.js` 增加 in-flight request dedupe，避免浏览器端重复请求后端。

### 5. 监控 cache 命中率

后续可加轻量日志或 metrics：

- memory cache hit
- file cache hit
- DB query fallback
- refresh 新增行数

这样可以更准确地判断 Neon 流量下降来自哪一层优化。

## 验证说明

本次优化过程中，为避免继续增加 Neon/Yahoo/Schwab 流量，只做了本地静态和语法级验证：

```bash
python3 -m py_compile ...
bash -n deploy_all.sh
```

没有执行会访问 Neon、Yahoo Finance 或 Schwab 的集成测试。

