# BRStock AI - GCP Deployment Guide

本指南详细说明了如何将 BRStock 平台部署到 Google Cloud Platform (GCP) 的 **Cloud Run**。

## 1. 前置准备 (Prerequisites)

1.  **GCP 项目**: 确保你有一个已启用的 GCP 项目，并获取 `PROJECT_ID`。
2.  **Google Cloud SDK**: 本地已安装并初始化 `gcloud` 命令行工具。
3.  **启用 API**: 在 GCP 控制台或通过命令行启用以下服务：
    ```bash
    gcloud services enable run.googleapis.com \
                           artifactregistry.googleapis.com \
                           cloudbuild.googleapis.com
    ```

## 2. 核心配置文件检查

在开始之前，请确保根目录下已存在以下两个文件（我们之前已准备好）：
- **`Dockerfile`**: 定义了容器环境。
- **`services/backend_api/requirements.txt`**: 包含 `google-generativeai` 和 `python-dotenv`。

## 3. 部署步骤 (Step-by-Step)

### 第一步：登录并选择项目
```bash
gcloud auth login
gcloud config set project [YOUR_PROJECT_ID]
```

### 第二步：使用 Cloud Build 构建并推送镜像
Cloud Build 会直接在云端完成镜像打包，无需本地安装 Docker。
```bash
# 在项目根目录下执行
gcloud builds submit --tag gcr.io/[YOUR_PROJECT_ID]/brstock-app .
```

### 第三步：部署到 Cloud Run
执行以下命令进行部署。注意：我们将 `GEMINI_API_KEY` 作为环境变量注入。

```bash
gcloud run deploy brstock-demo \
  --image gcr.io/[YOUR_PROJECT_ID]/brstock-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GEMINI_API_KEY=[你的_GEMINI_API_KEY]" \
  --set-env-vars="LOCAL_AI_URL=[你的_CLOUDFLARE_TUNNEL_URL]"
```
*(注：如果你的本地 AI 还没有配置 Cloudflare 隧道，`LOCAL_AI_URL` 可以先填一个占位符。)*

## 4. 验证部署

1.  部署成功后，终端会打印出一个 **Service URL** (例如: `https://brstock-demo-xxx.a.run.app`)。
2.  **访问地址**：
    - 前端主页：`[Service URL]/ui/index.html`
    - 健康检查：`[Service URL]/api/health`
3.  **测试 AI 分析**：进入 Chart Analysis 页面，选择股票并点击分析。观察它是否能正确连接到 Gemini 2.5/3.x。

## 5. 进阶：使用 Secret Manager (安全推荐)

为了防止在部署命令中暴露 API Key，建议将 Key 存入 GCP Secret Manager：
1.  在 GCP Console 搜索 **Secret Manager**，创建一个名为 `GEMINI_API_KEY` 的秘密。
2.  在 Cloud Run 部署设置中，将该秘密映射为环境变量。

---

## 常见问题处理 (Troubleshooting)

- **403 权限错误**: 确保你的 Compute Engine 默认服务账号具有访问 Secret Manager 或相关 API 的权限。
- **300s 超时**: 如果 Gemini 响应太慢，可以在 Cloud Run 设置中将 **Request Timeout** 调大（默认通常是 300s，与我们代码一致）。
- **数据库残留**: Cloud Run 是无状态的。如果你的 SQLite 数据库需要持久化，建议迁移到 **GCP Firestore** 或 **Cloud SQL**，或者将初始化数据打包进镜像中（作为演示用）。
