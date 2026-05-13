import os
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import text

# Import config
import config

# Use absolute imports for routers to avoid any ambiguity
from routes.auth import router as auth_router
from routes.stocks import router as stocks_router
from routes.options import router as options_router
from routes.strategies import router as strategies_router

app = FastAPI(title="BRStock AI API", version="1.0.1")
MARKET_TZ = ZoneInfo("America/New_York")

# --- Initialize Database ---
def init_db():
    try:
        with config.db.engine.connect() as conn:
            # Basic tables
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    email VARCHAR(100) PRIMARY KEY, hashed_password VARCHAR(255),
                    full_name VARCHAR(100), reset_pin VARCHAR(20), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_watchlists (
                    user_id VARCHAR(100), ticker VARCHAR(10),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    display_order INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, ticker)
                );
            """))
            try:
                conn.execute(text("ALTER TABLE user_watchlists ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 0"))
            except Exception:
                try:
                    conn.execute(text("ALTER TABLE user_watchlists ADD COLUMN display_order INTEGER DEFAULT 0"))
                except Exception:
                    pass
            # Fix backtest_results table if it exists
            try:
                conn.execute(text("ALTER TABLE backtest_results ALTER COLUMN strategy_id DROP NOT NULL"))
                conn.execute(text("ALTER TABLE backtest_results DROP CONSTRAINT IF EXISTS backtest_results_strategy_id_fkey"))
            except:
                pass
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS market_data_refresh_runs (
                    refresh_date VARCHAR(10) PRIMARY KEY,
                    refreshed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20),
                    detail TEXT
                );
            """))
            conn.commit()
    except Exception as e:
        print(f"DB Init Error: {e}")

init_db()

def _today_refresh_record():
    today = datetime.now(MARKET_TZ).date().isoformat()
    try:
        with config.db.engine.connect() as conn:
            row = conn.execute(
                text("SELECT refresh_date, status FROM market_data_refresh_runs WHERE refresh_date = :d"),
                {"d": today},
            ).fetchone()
            return row
    except Exception as e:
        print(f"Market data refresh state check failed: {e}")
        return None

def _record_today_refresh(status: str, detail: str):
    today = datetime.now(MARKET_TZ).date().isoformat()
    try:
        with config.db.engine.begin() as conn:
            conn.execute(
                text("DELETE FROM market_data_refresh_runs WHERE refresh_date = :d"),
                {"d": today},
            )
            conn.execute(
                text("""
                    INSERT INTO market_data_refresh_runs
                    (refresh_date, refreshed_at, status, detail)
                    VALUES (:d, CURRENT_TIMESTAMP, :s, :detail)
                """),
                {"d": today, "s": status, "detail": detail[:4000]},
            )
    except Exception as e:
        print(f"Market data refresh state write failed: {e}")

def _should_run_after_close_refresh(now=None):
    current = now or datetime.now(MARKET_TZ)
    if current.weekday() >= 5:
        return False
    after_close_window = current.replace(hour=16, minute=15, second=0, microsecond=0)
    return current >= after_close_window and not _today_refresh_record()

async def _market_data_after_close_loop():
    await asyncio.sleep(5)
    while True:
        try:
            if _should_run_after_close_refresh():
                from routes.stocks import get_dynamic_refresh_symbols, refresh_market_data_batch
                symbols = get_dynamic_refresh_symbols()
                print(f"Starting after-close market data refresh: {', '.join(symbols)}")
                result = await asyncio.to_thread(refresh_market_data_batch, symbols, True)
                failures = {
                    symbol: payload.get("error")
                    for symbol, payload in result.get("results", {}).items()
                    if isinstance(payload, dict) and payload.get("error")
                }
                status = "partial" if failures else "ok"
                _record_today_refresh(status, json.dumps(result, default=str))
                print(f"After-close market data refresh finished: {status}")
        except Exception as e:
            _record_today_refresh("error", str(e))
            print(f"After-close market data refresh failed: {e}")
        await asyncio.sleep(15 * 60)

@app.on_event("startup")
async def start_market_data_after_close_scheduler():
    if os.getenv("DISABLE_MARKET_DATA_SCHEDULER", "").lower() in {"1", "true", "yes"}:
        print("After-close market data scheduler disabled.")
        return
    asyncio.create_task(_market_data_after_close_loop())

# --- Register Routers ---
# Note: These routers already have "/api/..." prefixes defined in their files
app.include_router(auth_router)
app.include_router(stocks_router)
app.include_router(options_router)
app.include_router(strategies_router)

# ── Legacy URL Compatibility Shims ─────────────────────────────
# IMPORTANT: These ensure the frontend app.js (which uses old paths) still works.

@app.get("/api/watchlist")
async def watchlist_compat(request: Request):
    from routes.stocks import get_watchlist
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    token = auth_header[7:]
    try:
        from jose import jwt
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        user = payload.get("sub")
        return get_watchlist(current_user=user)
    except Exception:
        return JSONResponse(status_code=401, content={"detail": "Invalid token"})

@app.get("/api/users/me")
async def users_me_compat(request: Request):
    from routes.auth import get_me
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    token = auth_header[7:]
    try:
        from jose import jwt
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        user = payload.get("sub")
        return get_me(current_user=user)
    except Exception:
        return JSONResponse(status_code=401, content={"detail": "Invalid token"})

@app.post("/api/backtest")
async def backtest_compat(request: Request):
    from routes.strategies import run_backtest, BacktestRequest
    body = await request.json()
    
    # Validation fallback: ensure strategy_id is a string and not null
    if "strategy_id" in body and body["strategy_id"] is None:
        # If it's null (NaN from frontend), we can't guess, but we shouldn't crash pydantic
        # Let's try to see if it's a system strategy by default or return 400
        return JSONResponse(status_code=400, content={"detail": "strategy_id cannot be null. Please select a valid strategy."})
    
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    try:
        from jose import jwt
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        user = payload.get("sub")
        req = BacktestRequest(**body)
        return run_backtest(req, current_user=user)
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})

@app.get("/api/backtest/history")
async def backtest_history_compat(request: Request):
    from routes.strategies import get_backtest_history
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    try:
        from jose import jwt
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        user = payload.get("sub")
        return get_backtest_history(current_user=user)
    except Exception:
        return JSONResponse(status_code=401, content={"detail": "Invalid token"})

# --- Static Files & Frontend ---
WEB_UI_DIR = config.PROJECT_ROOT / "services" / "web_ui"
if WEB_UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(WEB_UI_DIR), html=True), name="ui")

@app.get("/")
def read_root():
    return RedirectResponse(url="/ui/index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
