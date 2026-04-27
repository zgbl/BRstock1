#!/bin/bash

# ── 配置信息 (根据你的项目修改) ──────────────────────────────
PROJECT_ID="brstock-494003"
REGION="us-central1"
API_SERVICE_NAME="brstock-demo"
JOB_NAME="brstock-pipeline"

# 环境变量
DATABASE_URL="postgresql://neondb_owner:npg_Qc0yJfgdbxO5@ep-proud-snow-aj4t7adu-pooler.c-3.us-east-2.aws.neon.tech/neondb?sslmode=require"
GEMINI_API_KEY="AIzaSyA8hiw_WJdvU9D90nyhkny1npZkMD5a-YA"
LOCAL_AI_URL="http://llm.blackrice.top/v1/chat/completions"

echo "🚀 开始全流程部署: $PROJECT_ID"

# 1. 设置项目
gcloud config set project $PROJECT_ID

# 2. 构建并推送 API 镜像
echo "📦 [1/4] 正在构建 API 镜像..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/brstock-app .

# 3. 构建并推送 Pipeline 镜像
echo "📦 [2/4] 正在构建 Pipeline 镜像..."
gcloud builds submit --config cloudbuild.yaml .

# 4. 部署/更新 Backend API 服务
echo "🚀 [3/4] 正在部署 Backend API 到 Cloud Run..."
gcloud run deploy $API_SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/brstock-app \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=$DATABASE_URL,GEMINI_API_KEY=$GEMINI_API_KEY,LOCAL_AI_URL=$LOCAL_AI_URL"

# 5. 部署/更新 Data Pipeline Job
echo "⚙️ [4/4] 正在部署 Data Pipeline Job..."
gcloud run jobs deploy $JOB_NAME \
  --image gcr.io/$PROJECT_ID/brstock-pipeline \
  --region $REGION \
  --set-env-vars="DATABASE_URL=$DATABASE_URL"

# 6. 立即触发一次数据抓取
echo "📡 正在触发一次数据抓取任务以确保数据库有值..."
gcloud run jobs execute $JOB_NAME --region $REGION

echo "✨ 部署全部完成！"
echo "🔗 请访问: https://stock.blackrice.top/ui/index.html"
