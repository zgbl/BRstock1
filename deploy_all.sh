#!/bin/bash

# ── 配置信息 (根据你的项目修改) ──────────────────────────────
PROJECT_ID="brstock-494003"
REGION="us-central1"
API_SERVICE_NAME="brstock-demo"
JOB_NAME="brstock-pipeline"

# 环境变量
GEMINI_API_KEY="AIzaSyA8hiw_WJdvU9D90nyhkny1npZkMD5a-YA"
LOCAL_AI_URL="http://llm.blackrice.top/v1/chat/completions"
OPENROUTER_MODEL="${OPENROUTER_MODEL:-minimax/minimax-m2.5:free}"
SCHWAB_TOKEN_STORE="database"
DB_LOCAL_QUERY_CACHE="${DB_LOCAL_QUERY_CACHE:-1}"
DB_LOCAL_QUERY_CACHE_TTL_SECONDS="${DB_LOCAL_QUERY_CACHE_TTL_SECONDS:-86400}"
DB_LOCAL_QUERY_CACHE_DIR="${DB_LOCAL_QUERY_CACHE_DIR:-/tmp/brstock_db_query_cache}"
DB_MEMORY_QUERY_CACHE="${DB_MEMORY_QUERY_CACHE:-1}"
DB_MEMORY_QUERY_CACHE_TTL_SECONDS="${DB_MEMORY_QUERY_CACHE_TTL_SECONDS:-900}"
DB_MEMORY_QUERY_CACHE_MAX_ENTRIES="${DB_MEMORY_QUERY_CACHE_MAX_ENTRIES:-256}"

if [ -z "$OPENROUTER_MODEL" ] && [ -f ".env" ]; then
  OPENROUTER_MODEL=$(grep '^OPENROUTER_MODEL=' .env | cut -d= -f2- | sed 's/^["'\'']//;s/["'\'']$//')
fi

if [ -f ".env" ]; then
  DB_LOCAL_QUERY_CACHE=$(grep '^DB_LOCAL_QUERY_CACHE=' .env | cut -d= -f2- | sed 's/^["'\'']//;s/["'\'']$//' || true)
  DB_LOCAL_QUERY_CACHE_TTL_SECONDS=$(grep '^DB_LOCAL_QUERY_CACHE_TTL_SECONDS=' .env | cut -d= -f2- | sed 's/^["'\'']//;s/["'\'']$//' || true)
  DB_LOCAL_QUERY_CACHE_DIR=$(grep '^DB_LOCAL_QUERY_CACHE_DIR=' .env | cut -d= -f2- | sed 's/^["'\'']//;s/["'\'']$//' || true)
  DB_MEMORY_QUERY_CACHE=$(grep '^DB_MEMORY_QUERY_CACHE=' .env | cut -d= -f2- | sed 's/^["'\'']//;s/["'\'']$//' || true)
  DB_MEMORY_QUERY_CACHE_TTL_SECONDS=$(grep '^DB_MEMORY_QUERY_CACHE_TTL_SECONDS=' .env | cut -d= -f2- | sed 's/^["'\'']//;s/["'\'']$//' || true)
  DB_MEMORY_QUERY_CACHE_MAX_ENTRIES=$(grep '^DB_MEMORY_QUERY_CACHE_MAX_ENTRIES=' .env | cut -d= -f2- | sed 's/^["'\'']//;s/["'\'']$//' || true)
  DB_LOCAL_QUERY_CACHE="${DB_LOCAL_QUERY_CACHE:-1}"
  DB_LOCAL_QUERY_CACHE_TTL_SECONDS="${DB_LOCAL_QUERY_CACHE_TTL_SECONDS:-86400}"
  DB_LOCAL_QUERY_CACHE_DIR="${DB_LOCAL_QUERY_CACHE_DIR:-/tmp/brstock_db_query_cache}"
  DB_MEMORY_QUERY_CACHE="${DB_MEMORY_QUERY_CACHE:-1}"
  DB_MEMORY_QUERY_CACHE_TTL_SECONDS="${DB_MEMORY_QUERY_CACHE_TTL_SECONDS:-900}"
  DB_MEMORY_QUERY_CACHE_MAX_ENTRIES="${DB_MEMORY_QUERY_CACHE_MAX_ENTRIES:-256}"
fi

echo "🚀 开始全流程部署: $PROJECT_ID"
echo "🧹 Cloud Build 将按 .gcloudignore 排除 Moomoo/OpenD 安装包，避免上传几百 MB 的无用文件。"
echo "🧪 发布本地合成期权链校准参数到部署包；生产敏感配置通过 Secret Manager 注入。"

if [ -f "Data/option_synth_calibration.json" ]; then
  python3 services/backend_api/scripts/publish_calibration.py
else
  echo "⚠️ 未找到 Data/option_synth_calibration.json，本次部署将使用仓库中已有的 bundled calibration。"
fi

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
  --set-env-vars="GEMINI_API_KEY=$GEMINI_API_KEY,LOCAL_AI_URL=$LOCAL_AI_URL,OPENROUTER_MODEL=$OPENROUTER_MODEL,SCHWAB_TOKEN_STORE=$SCHWAB_TOKEN_STORE,DB_LOCAL_QUERY_CACHE=$DB_LOCAL_QUERY_CACHE,DB_LOCAL_QUERY_CACHE_TTL_SECONDS=$DB_LOCAL_QUERY_CACHE_TTL_SECONDS,DB_LOCAL_QUERY_CACHE_DIR=$DB_LOCAL_QUERY_CACHE_DIR,DB_MEMORY_QUERY_CACHE=$DB_MEMORY_QUERY_CACHE,DB_MEMORY_QUERY_CACHE_TTL_SECONDS=$DB_MEMORY_QUERY_CACHE_TTL_SECONDS,DB_MEMORY_QUERY_CACHE_MAX_ENTRIES=$DB_MEMORY_QUERY_CACHE_MAX_ENTRIES" \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest,OPENROUTER_API_KEY=OPENROUTER_API_KEY:latest,SCHWAB_CLIENT_ID=SCHWAB_CLIENT_ID:latest,SCHWAB_CLIENT_SECRET=SCHWAB_CLIENT_SECRET:latest,SCHWAB_REDIRECT_URI=SCHWAB_REDIRECT_URI:latest"

# 5. 部署/更新 Data Pipeline Job
echo "⚙️ [4/4] 正在部署 Data Pipeline Job..."
gcloud run jobs deploy $JOB_NAME \
  --image gcr.io/$PROJECT_ID/brstock-pipeline \
  --region $REGION \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest"

# 6. 立即触发一次数据抓取
echo "📡 正在触发一次数据抓取任务以确保数据库有值..."
gcloud run jobs execute $JOB_NAME --region $REGION

echo "✨ 部署全部完成！"
echo "🔗 请访问: https://stock.blackrice.top/ui/index.html"
