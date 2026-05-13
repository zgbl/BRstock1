# BRStock AI - Quickstart & Operations Guide

This guide contains the essential commands to run the project locally, deploy it to Google Cloud Platform (GCP), and manage the data pipeline. 

## 1. Local Development (启动 Local)

The application is built with FastAPI (Backend) and Vanilla JS/HTML/CSS (Frontend). The frontend is served statically by the backend.

**Prerequisites:**
Make sure you have your `.env` file set up in the root directory with necessary API keys (like `GEMINI_API_KEY` and `DATABASE_URL`).

**Start the Server:**
From the root of the project (`/Users/tuxy/Codes/Github2/BRstock1`), run:
```bash
# If using uvicorn directly
uvicorn services.backend_api.main:app --reload --port 8080

# Or via Python directly (since main.py has the uvicorn.run block)
python services/backend_api/main.py
```

**Access the App:**
- Web UI: [http://localhost:8080/ui/index.html](http://localhost:8080/ui/index.html)
- API Docs (Swagger): [http://localhost:8080/docs](http://localhost:8080/docs)

---

## 2. GCP Deployment (部署到 GCP)

The project is configured to be deployed to Google Cloud Run, utilizing both a web service (`brstock-demo`) and a background job for the data pipeline (`brstock-pipeline`).

All deployment steps are bundled into the provided shell script.

**Deploy Command:**
```bash
# From the root of the project
./deploy_all.sh
```

**What `deploy_all.sh` does:**
1. Sets the GCP project to `brstock-494003`.
2. Builds the Backend API Docker image and pushes it to GCR.
3. Builds the Data Pipeline Docker image (using `cloudbuild.yaml`).
4. Deploys the Backend API to Cloud Run (`brstock-demo`).
5. Deploys the Data Pipeline to Cloud Run Jobs (`brstock-pipeline`).
6. Triggers an immediate data fetch job to ensure the database is populated.

**Live URL:**
- [https://stock.blackrice.top/ui/index.html](https://stock.blackrice.top/ui/index.html)

---

## 3. Data Updates (更新数据)

Data fetching relies on the data pipeline job. You have two ways to update data manually:

### Option A: Trigger the Cloud Run Job (Full Update)
You can manually trigger the GCP Cloud Run job to fetch the latest stock data for all tracked symbols.
```bash
gcloud run jobs execute brstock-pipeline --region us-central1
```

### Option B: On-Demand Fetch via API (Single Stock)
If you just want to refresh or fetch historical data (5m and 1d) for a single ticker immediately, use the API endpoint:
```bash
# Example for fetching AAPL
curl -X POST "http://localhost:8080/api/stocks/AAPL/fetch"

# If hitting production:
curl -X POST "https://stock.blackrice.top/api/stocks/AAPL/fetch"
```

---

## 4. Other Useful Commands

**Testing the Options API Plan (WIP):**
If you are iterating on the Options real-time module:
1. Make sure your local `options_data.local.toml` is configured properly.
2. Start the local Moomoo OpenD gateway.
3. Use the Python CLI (once Phase 2 is built) to test updates before relying on the Web UI.
