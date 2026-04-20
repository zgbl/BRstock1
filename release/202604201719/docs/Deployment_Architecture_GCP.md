# 🚀 GCP Serverless 部署架构与实现路线图

为了向投资人展示 MVP 且保持极低的运行成本（甚至免费），建议采用 Google Cloud Platform (GCP) 的 **Serverless (无服务器)** 架构。

---

## 🏗 核心架构设计

| 组件 | 推荐方案 | 理由 | 费用 |
| :--- | :--- | :--- | :--- |
| **数据抓取器** | **Cloud Functions** (Python) | 适合每日定时运行几分钟的脚本。 | 免费额度内 ($0) |
| **定时任务** | **Cloud Scheduler** | 类似于 linux 的 crontab，触发抓取器。 | 3个任务内免费 ($0) |
| **后端 API** | **Cloud Run** (FastAPI) | 资源自动缩放到 0，只有当有人访问网页时才启动。 | 免费额度内 ($0) |
| **数据存储** | **Supabase (PostgreSQL)** 或 **Cloud Storage (GCS)** | GCP 内部 Cloud SQL 比较贵，10GB 方案有技巧。 | **Supabase** 免费 / **GCS** 极低 |
| **前端托管** | **Vercel** / **Netlify** | 展示效果最好，全球加速，部署最简单。 | 免费项目 ($0) |

---

## 🗄 数据库 (10GB) 深度方案建议

由于 GCP 的 **Cloud SQL (Managed Postgres/MySQL)** 即使最小规格每月也要 ~$10-$15，没有永久免费额度。针对你的需求有三个替代方案：

1.  **方案 A：离线文件方案 (Serverless Data Lake) —— [最省钱/推荐]**
    *   将股票数据存为 **Parquet** 格式（比 CSV 小很多，读写极快）。
    *   保存在 **Google Cloud Storage (GCS)** 存储桶中。
    *   后端 Cloud Run 启动时，内存加载这些 Parquet 文件进行计算。10GB 存储费约 $0.2/月。
2.  **方案 B：外部免费云数据库 —— [开发体验最像正式版]**
    *   使用 **Supabase** 或 **Neon.tech**。
    *   它们提供 500MB - 1GB 的免费 PostgreSQL。对于 QQQ/VOO/TSLA 这种级别的 5m 历史数据，1GB 够用很久。
3.  **方案 C：GCP BigQuery —— [适合大数据量展示]**
    *   10GB 存储免费，查询前 1TB 免费。
    *   非常适合处理数百万行股票数据，缺点是实时写入和点查询（Point Query）响应稍微比 Postgres 慢一点。

---

## 🗺 部署路线实施计划

### 第一阶段：云端化准备 (Week 1)
*   **[Python] 容器化**：将现有的 `fetch_data.py` 编写成 Dockerfile，准备部署到 Cloud Run 或 Cloud Functions。
*   **[Database] 建立存储**：在 GCP 创建一个 Storage Bucket 或注册一个 Supabase 数据库，修改代码将 `to_csv` 改为写入云端。

### 第二阶段：部署计算层 (Week 2)
*   **部署 Cloud Functions**：将抓取程序部署上去，配置 Cloud Scheduler 每天收盘后运行。
*   **部署 Cloud Run 后端**：使用 FastAPI 编写接口，能从云端读取数据并返回 JSON。
*   **验证连接**：确保互联网可以通过 API 地址拿到股票数据。

### 第三阶段：展示层与演示 (Week 3)
*   **前端部署**：使用 React/Vue 编写简单的可视化看板，部署到 Vercel。
*   **域名与 HTTPS**：配置一个专业的子域名，方便给投资人发送链接预览。

---

## 📈 给投资人的展示建议 (Investor Pitch Points)
1.  **极低运维成本**：展示通过 Serverless 架构，我们在极低（甚至 $0）成本下实现了高可用的金融分析平台。
2.  **可扩展性**：虽然目前只抓 3 支股票，但由于使用了分布式云计算（Cloud Run），未来支持 3000 支股票只需要横向增加算力，架构无需重构。
3.  **AI 分析深度**：重点展示 AI 报告生成的独特性，不仅仅是图表。

---
*文件路径：`/BRstock1/docs/Deployment_Architecture_GCP.md`*
