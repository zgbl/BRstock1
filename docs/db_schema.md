# BRstock1 数据库架构设计

## 总体设计原则

- **主数据库**：Neon DB (PostgreSQL)，作为唯一的生产数据源。
- **表命名规范**：全部使用小写，单词间用下划线分隔。
- **Neon Branch 策略**：利用 Neon 的分支（Branch）功能隔离环境，互不影响。

---

## Neon Branch 结构

```
blackrice (project)
├── production        ← Cloud Run 生产服务连接此分支（当前已使用）
├── dev               ← 本地开发、测试新功能、跑实验性脚本
└── (future) shadow   ← 未来用于数据库 schema 迁移前的预演
```

> **连接字符串切换方式**：只需将 `DATABASE_URL` 环境变量指向不同 Branch 的 Pooler 地址即可，代码无需改动。

---

## 表结构设计

### 1. `stocks` — 美股主列表（核心注册表）

这是所有股票代号的"花名册"，一切其他表都以 `ticker` 为外键。

```sql
CREATE TABLE IF NOT EXISTS stocks (
    ticker              VARCHAR(10)  PRIMARY KEY,       -- 股票代号, 如 AAPL
    name                VARCHAR(255),                   -- 公司全名
    exchange            VARCHAR(20),                    -- NYSE / NASDAQ / AMEX / OTC
    sector              VARCHAR(100),                   -- 行业大类 (Technology / Healthcare ...)
    industry            VARCHAR(150),                   -- 细分行业
    market_cap_category VARCHAR(20),                    -- Large / Mid / Small / Micro / Nano
    is_etf              BOOLEAN      DEFAULT FALSE,     -- 是否为 ETF
    is_active           BOOLEAN      DEFAULT TRUE,      -- 是否仍在交易
    country             VARCHAR(10)  DEFAULT 'US',
    created_at          TIMESTAMPTZ  DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  DEFAULT NOW()
);
```

**当前状态**：`ticker` 和 `name` 已填充，其余字段后续按需填充。

---

### 2. `{ticker}_5m` — 个股 5 分钟 OHLCV（动态表）

> **命名规则**：`{ticker小写}_5m`，例如 `qqq_5m`, `aapl_5m`

每支股票独立一张表，保留最近 60 天的 5 分钟 K 线数据（Yahoo Finance 上限）。
表结构由 `pandas.to_sql` + SQLAlchemy 自动创建，无需手动建表。

| 列名      | 类型             | 说明              |
|-----------|------------------|-------------------|
| timestamp | TIMESTAMP PK     | K 线时间 (UTC)    |
| open      | DOUBLE PRECISION | 开盘价            |
| high      | DOUBLE PRECISION | 最高价            |
| low       | DOUBLE PRECISION | 最低价            |
| close     | DOUBLE PRECISION | 收盘价            |
| volume    | BIGINT           | 成交量            |

> **扩展计划**：可在此基础上增加 `stock_daily_prices` 表（日线），结构类似但加 `adj_close` 字段。

---

### 3. `technical_snapshots` — 技术指标快照

存储每次数据抓取后计算出的最新技术指标，供 API 快速读取，避免每次请求都重新计算。

```sql
CREATE TABLE IF NOT EXISTS technical_snapshots (
    id              BIGSERIAL    PRIMARY KEY,
    ticker          VARCHAR(10)  NOT NULL REFERENCES stocks(ticker),
    computed_at     TIMESTAMPTZ  DEFAULT NOW(),
    rsi_14          DOUBLE PRECISION,
    macd            DOUBLE PRECISION,
    macd_signal     DOUBLE PRECISION,
    macd_hist       DOUBLE PRECISION,
    sma_20          DOUBLE PRECISION,
    sma_50          DOUBLE PRECISION,
    sma_200         DOUBLE PRECISION,
    ema_20          DOUBLE PRECISION,
    ema_50          DOUBLE PRECISION,
    bb_upper        DOUBLE PRECISION,
    bb_lower        DOUBLE PRECISION,
    bb_mid          DOUBLE PRECISION,
    vol_avg_20      BIGINT,
    signal          VARCHAR(10),    -- BUY / SELL / HOLD
    UNIQUE(ticker, computed_at)
);
```

---

### 4. `ai_analyses` — AI 分析结果缓存

缓存 Gemini 等 LLM 输出，避免重复调用 API，同时可按时间查询历史分析。

```sql
CREATE TABLE IF NOT EXISTS ai_analyses (
    id          BIGSERIAL   PRIMARY KEY,
    ticker      VARCHAR(10) NOT NULL REFERENCES stocks(ticker),
    lang        VARCHAR(5)  DEFAULT 'zh',         -- zh / en
    analyzed_at TIMESTAMPTZ DEFAULT NOW(),
    signal      VARCHAR(10),                       -- BUY / SELL / HOLD
    confidence  SMALLINT,                          -- 0-100
    analysis    TEXT,                              -- LLM 完整输出
    source      VARCHAR(50)                        -- 'Google Gemini' / 'Local AI'
);
CREATE INDEX ON ai_analyses (ticker, analyzed_at DESC);
```

---

## 表关系总览

```
stocks (主注册表)
├── {ticker}_5m         (行情数据，动态表，无外键约束)
├── technical_snapshots (指标快照，FK: ticker)
└── ai_analyses         (AI 分析，FK: ticker)
```

---

## 数据流向

```
Yahoo Finance (外部数据源)
        │
        ▼
Cloud Run Job (Data Pipeline)
  fetch_data.py
        │
        ├── 写入 {ticker}_5m   (原始行情)
        └── 计算指标后写入 technical_snapshots
        
用户请求
        │
        ▼
Cloud Run API (Backend)
  main.py
        ├── GET /api/stocks/{symbol}/history   → 读 {ticker}_5m
        ├── GET /api/stocks/{symbol}/summary   → 读 {ticker}_5m
        ├── GET /api/stocks/{symbol}/indicators → 读 {ticker}_5m 或 technical_snapshots
        └── GET /api/stocks/{symbol}/ai_analysis → 读/写 ai_analyses
```

---

## 下一步建议

| 优先级 | 任务 | 说明 |
|--------|------|------|
| 🔴 高  | 填充 `stocks` 表 | 把全部美股代号写入，本文档下方已提供脚本 |
| 🔴 高  | 建立 `technical_snapshots` 表 | Pipeline 完成抓取后直接持久化计算结果 |
| 🟡 中  | 建立 `ai_analyses` 表 | 缓存 AI 分析，减少 API 调用次数和延迟 |
| 🟡 中  | 增加日线数据 `stock_daily_prices` | 5m 数据只有 60 天，日线可存多年 |
| 🟢 低  | Neon `dev` 分支 | 正式创建并在本地开发时切换到 dev 分支 |
| 🟢 低  | 定时清理旧 5m 数据 | 保留最近 30 天，防止表膨胀 |
