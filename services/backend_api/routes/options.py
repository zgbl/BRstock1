from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import json
import numpy as np
import pandas as pd
import yfinance as yf
from sqlalchemy import text
from config import db, synth_engine, get_moomoo_provider, get_schwab_provider
from dependencies import get_current_user
import options_synth
import options_calibration
from schwab_market_data import SchwabAuthError
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/options", tags=["options"])

class OptionBacktestRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    initial_capital: float = 50000
    params: dict = {}

class MoomooCommandRequest(BaseModel):
    command: str

class SchwabOAuthCodeRequest(BaseModel):
    code: str

class ChainCalibrationRequest(BaseModel):
    ticker: str = "QQQ"
    strike_count: int = 60
    dte_min: int = 5
    dte_max: int = 75
    delta_min: float = 0.15
    delta_max: float = 0.85
    max_spread_pct: float = 0.35
    min_bucket_samples: int = 3
    blend: float = 0.35
    save: bool = True

LOCAL_CALIBRATION_ONLY_MESSAGE = (
    "Schwab calibration is available only in local authenticated mode. "
    "Remote demo uses saved calibration parameters."
)

def _latest_synthetic_inputs(ticker: str, target_date=None):
    target_date = target_date or datetime.utcnow().date()
    start = target_date - timedelta(days=120)
    end = target_date + timedelta(days=1)
    df = yf.download(ticker, start=start.isoformat(), end=end.isoformat(), progress=False, auto_adjust=False)
    if df.empty:
        table_name = f"{ticker.lower()}_1d"
        df = db.get_stock_data(table_name, limit=160)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No historical price data for {ticker}")
        df = df.reset_index()
        if "timestamp" not in df.columns:
            df = df.rename(columns={"Date": "timestamp", "date": "timestamp"})
    else:
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns={"Date": "timestamp"})

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    df = df[df["timestamp"].dt.date <= target_date].tail(160)
    if len(df) < 25:
        raise HTTPException(status_code=400, detail=f"Insufficient price history for {ticker}")

    close = df["Close"].astype(float)
    delta = close.diff()
    avg_gain = delta.clip(lower=0).ewm(com=13, min_periods=14).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(com=13, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = float((100 - 100 / (1 + rs)).iloc[-1])
    hv_20 = float(np.log(close / close.shift(1)).rolling(20).std().iloc[-1] * np.sqrt(252))
    if not np.isfinite(rsi) or not np.isfinite(hv_20):
        raise HTTPException(status_code=400, detail=f"Insufficient indicator data for {ticker}")
    return {
        "actual_date": df.iloc[-1]["timestamp"].date(),
        "spot_price": float(close.iloc[-1]),
        "rsi": rsi,
        "hv_20": hv_20,
    }

def _index_synthetic_chain(chain):
    return {
        (str(o.get("type", "")).upper(), int(o.get("expiry_dte") or 0), float(o.get("strike") or 0)): o
        for o in chain
    }

def _real_chain_quality_filter(option, req: ChainCalibrationRequest):
    bid = options_calibration.safe_float(option.get("bid"))
    ask = options_calibration.safe_float(option.get("ask"))
    mid = options_calibration.safe_float(option.get("mid"))
    delta = options_calibration.safe_float(option.get("delta"))
    dte = int(option.get("expiry_dte") or 0)
    if bid is None or ask is None or mid is None or delta is None:
        return False
    if bid <= 0 or ask <= bid or mid <= 0:
        return False
    if dte < req.dte_min or dte > req.dte_max:
        return False
    if abs(delta) < req.delta_min or abs(delta) > req.delta_max:
        return False
    spread_pct = (ask - bid) / mid if mid else 999
    if spread_pct > req.max_spread_pct:
        return False
    return True

def _compare_real_vs_synthetic(ticker: str, real_options, synthetic_index):
    comparisons = []
    for real in real_options:
        option_type = str(real.get("type") or "").upper()
        dte = int(real.get("expiry_dte") or 0)
        strike = float(real.get("strike") or 0)
        synth = synthetic_index.get((option_type, dte, strike))
        if not synth:
            continue
        real_bid = options_calibration.safe_float(real.get("bid"))
        real_ask = options_calibration.safe_float(real.get("ask"))
        real_mid = options_calibration.safe_float(real.get("mid"))
        synth_bid = options_calibration.safe_float(synth.get("bid"))
        synth_ask = options_calibration.safe_float(synth.get("ask"))
        synth_mid = (synth_bid + synth_ask) / 2 if synth_bid is not None and synth_ask is not None else options_calibration.safe_float(synth.get("premium"))
        if not real_mid or not synth_mid:
            continue
        real_delta = options_calibration.safe_float(real.get("delta"))
        synth_delta = options_calibration.safe_float(synth.get("delta"))
        row = {
            "symbol": ticker.upper(),
            "contract": real.get("symbol"),
            "type": option_type,
            "expiry": real.get("expiry"),
            "expiry_dte": dte,
            "strike": strike,
            "real_bid": real_bid,
            "real_ask": real_ask,
            "real_mid": real_mid,
            "synth_bid": synth_bid,
            "synth_ask": synth_ask,
            "synth_mid": synth_mid,
            "real_spread": (real_ask - real_bid) if real_ask is not None and real_bid is not None else None,
            "synth_spread": (synth_ask - synth_bid) if synth_ask is not None and synth_bid is not None else None,
            "real_iv": options_calibration.safe_float(real.get("iv")),
            "synth_iv": options_calibration.safe_float(synth.get("iv")),
            "real_delta": real_delta,
            "synth_delta": synth_delta,
            "error_pct": options_calibration.pct_error(synth_mid, real_mid),
            "bucket_key": options_calibration.bucket_key(ticker, option_type, dte, synth_delta if synth_delta is not None else real_delta),
        }
        comparisons.append(row)
    return comparisons

def _apply_updates_to_rows(rows, updates):
    adjusted = []
    for row in rows:
        update = updates.get(row["bucket_key"]) or {}
        mid_multiplier = float(update.get("mid_multiplier") or 1.0)
        spread_multiplier = float(update.get("spread_multiplier") or 1.0)
        clone = dict(row)
        clone["adjusted_synth_mid"] = row["synth_mid"] * mid_multiplier
        clone["adjusted_synth_spread"] = (row.get("synth_spread") or 0) * spread_multiplier
        clone["adjusted_error_pct"] = options_calibration.pct_error(clone["adjusted_synth_mid"], row["real_mid"])
        adjusted.append(clone)
    return adjusted

@router.get("/moomoo/status")
def get_moomoo_status():
    """Check Moomoo OpenD connection status"""
    try:
        provider = get_moomoo_provider()
        status = provider.check_connection()
        if isinstance(status, dict):
            return {
                "status": status.get("status", "UNKNOWN"),
                "connected": bool(status.get("connected")),
                "provider": "moomoo",
                **({"error": status.get("error")} if status.get("error") else {}),
            }
        return {"status": "CONNECTED" if status else "DISCONNECTED", "connected": bool(status), "provider": "moomoo"}
    except Exception as e:
        return {"status": "DISCONNECTED", "connected": False, "error": str(e), "provider": "moomoo"}

@router.get("/chain/{ticker}")
async def get_options_chain(ticker: str):
    try:
        chain = get_schwab_provider().get_normalized_option_chain(
            ticker,
            contractType="ALL",
            strikeCount=20,
        )
        return {"ticker": ticker.upper(), "provider": "schwab", "chain": chain["options"], "options": chain["options"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/moomoo/chain/{ticker}")
async def get_moomoo_options_chain(ticker: str, current_user: str = Depends(get_current_user)):
    try:
        provider = get_moomoo_provider()
        code = ticker.upper().strip()
        if "." not in code:
            code = f"US.{code}"
        chain = provider.get_option_chain(code)
        return {"ticker": ticker.upper(), "provider": "moomoo", "options": chain}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/moomoo/command")
async def send_moomoo_command(req: MoomooCommandRequest, current_user: str = Depends(get_current_user)):
    command = req.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="command is required")

    allowed_prefixes = (
        "input_phone_verify_code",
        "req_phone_verify_code",
    )
    if not command.startswith(allowed_prefixes):
        raise HTTPException(status_code=400, detail="Unsupported Moomoo command")

    try:
        provider = get_moomoo_provider()
        response = provider.send_command(command)
        provider.reset_circuit_breaker()
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schwab/status")
def get_schwab_status():
    try:
        status = get_schwab_provider().status()
        return {
            **status,
            "connected": bool(status.get("access_token_valid") or status.get("has_refresh_token")),
            "status": "CONNECTED" if status.get("access_token_valid") or status.get("has_refresh_token") else "NEEDS_AUTH",
        }
    except Exception as e:
        return {"provider": "schwab", "configured": False, "connected": False, "status": "ERROR", "error": str(e)}

@router.get("/schwab/auth-url")
def get_schwab_auth_url():
    try:
        return {"provider": "schwab", "authorization_url": get_schwab_provider().get_authorization_url()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/schwab/exchange-code")
def exchange_schwab_code(req: SchwabOAuthCodeRequest):
    code = req.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="code is required")
    try:
        return {"provider": "schwab", "token": get_schwab_provider().exchange_code(code)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/schwab/quote/{ticker}")
def get_schwab_quote(ticker: str, fields: str = "quote,reference,regular"):
    try:
        return {"provider": "schwab", "ticker": ticker.upper(), "quote": get_schwab_provider().get_quote(ticker, fields=fields)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/schwab/chain/{ticker}")
def get_schwab_options_chain(
    ticker: str,
    contract_type: str = Query(None, alias="contractType"),
    strike_count: int = Query(10, alias="strikeCount"),
    raw: bool = False,
):
    try:
        provider = get_schwab_provider()
        params = {"contractType": contract_type or "ALL", "strikeCount": strike_count}
        if raw:
            chain = provider.get_option_chain(ticker, **params)
            return {"provider": "schwab", "ticker": ticker.upper(), "raw": chain}
        return provider.get_normalized_option_chain(ticker, **params)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/calibration/status")
def get_chain_calibration_status(current_user: str = Depends(get_current_user)):
    loaded = options_calibration.load_calibration_with_source()
    model = loaded["model"]
    schwab_status = {"configured": False, "connected": False, "status": "UNAVAILABLE"}
    try:
        status = get_schwab_provider().status()
        schwab_status = {
            "configured": bool(status.get("configured")),
            "connected": bool(status.get("access_token_valid") or status.get("has_refresh_token")),
            "status": "CONNECTED" if status.get("access_token_valid") or status.get("has_refresh_token") else "NEEDS_AUTH",
        }
    except Exception:
        pass
    can_run_live_calibration = bool(schwab_status.get("configured") and schwab_status.get("connected"))
    return {
        "version": model.get("version", 0),
        "updated_at": model.get("updated_at"),
        "bucket_count": len(model.get("buckets") or {}),
        "path": str(options_calibration.calibration_path()),
        "source_kind": loaded.get("source_kind"),
        "source_path": loaded.get("source_path"),
        "bundled_path": str(options_calibration.bundled_calibration_path()),
        "can_run_live_calibration": can_run_live_calibration,
        "schwab_status": schwab_status,
        "message": None if can_run_live_calibration else LOCAL_CALIBRATION_ONLY_MESSAGE,
        "buckets": model.get("buckets") or {},
    }

@router.post("/calibration/run")
def run_chain_calibration(req: ChainCalibrationRequest, current_user: str = Depends(get_current_user)):
    ticker = req.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker is required")

    try:
        provider = get_schwab_provider()
        status = provider.status()
        if not status.get("configured") or not (status.get("access_token_valid") or status.get("has_refresh_token")):
            raise HTTPException(status_code=403, detail=LOCAL_CALIBRATION_ONLY_MESSAGE)
        real_chain = provider.get_normalized_option_chain(
            ticker,
            contractType="ALL",
            strikeCount=max(min(int(req.strike_count or 60), 200), 10),
        )
        inputs = _latest_synthetic_inputs(ticker)
        spot = float(real_chain.get("underlying_price") or inputs["spot_price"])
        real_options = [o for o in real_chain.get("options", []) if _real_chain_quality_filter(o, req)]
        dtes = sorted({int(o.get("expiry_dte") or 0) for o in real_options})
        if not dtes:
            raise HTTPException(status_code=400, detail="No Schwab option quotes passed the quality filters.")

        synthetic_chain = synth_engine.generate_chain(
            inputs["actual_date"],
            spot,
            inputs["rsi"],
            inputs["hv_20"],
            dte_list=dtes,
            ticker=ticker,
            apply_calibration=False,
        )
        comparisons = _compare_real_vs_synthetic(ticker, real_options, _index_synthetic_chain(synthetic_chain))
        if not comparisons:
            raise HTTPException(status_code=400, detail="No matching synthetic contracts for the filtered Schwab chain.")

        updates = options_calibration.build_bucket_updates(comparisons, min_samples=max(int(req.min_bucket_samples or 3), 1))
        adjusted_rows = _apply_updates_to_rows(comparisons, updates)
        before = options_calibration.summarize_errors(comparisons, "error_pct")
        after = options_calibration.summarize_errors(adjusted_rows, "adjusted_error_pct")

        model = options_calibration.load_calibration()
        saved_model = model
        if req.save and updates:
            saved_model = options_calibration.merge_calibration_updates(model, updates, blend=req.blend)
            options_calibration.save_calibration(saved_model)
            synth_engine.load_calibration(force=True)

        report = {
            "ticker": ticker,
            "captured_at": datetime.utcnow().isoformat() + "Z",
            "schwab_status": real_chain.get("status"),
            "underlying_price": spot,
            "input_actual_date": inputs["actual_date"].isoformat(),
            "rsi": round(inputs["rsi"], 2),
            "hv_20": round(inputs["hv_20"], 6),
            "real_contracts_seen": len(real_chain.get("options") or []),
            "real_contracts_after_filter": len(real_options),
            "matched_contracts": len(comparisons),
            "dtes": dtes,
            "before": before,
            "after": after,
            "updated_bucket_count": len(updates),
            "saved": bool(req.save and updates),
            "calibration_version": saved_model.get("version", 0),
            "sample_rows": adjusted_rows[:40],
            "bucket_updates": updates,
        }
        options_calibration.append_report({k: v for k, v in report.items() if k != "sample_rows"})
        return report
    except HTTPException:
        raise
    except SchwabAuthError:
        raise HTTPException(status_code=403, detail=LOCAL_CALIBRATION_ONLY_MESSAGE)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/synth/chain/{ticker}")
async def get_synthetic_chain(ticker: str):
    try:
        table_name = f"{ticker.lower()}_1d"
        df = db.get_stock_data(table_name, limit=60)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")

        close = df['Close'].astype(float)
        spot = float(close.iloc[-1])

        # RSI
        delta = close.diff()
        avg_gain = delta.clip(lower=0).ewm(com=13, min_periods=14).mean()
        avg_loss = (-delta.clip(upper=0)).ewm(com=13, min_periods=14).mean()
        rs = avg_gain / avg_loss.replace(0, float('nan'))
        rsi_series = 100 - 100 / (1 + rs)
        rsi = round(float(rsi_series.iloc[-1]), 1)

        # HV 20d
        log_ret = np.log(close / close.shift(1))
        hv_20 = float(log_ret.rolling(20).std().iloc[-1] * np.sqrt(252))

        import datetime
        today = datetime.date.today()
        chain = synth_engine.generate_chain(today, spot, rsi, hv_20, ticker=ticker)

        return {
            "ticker": ticker.upper(),
            "spot_price": round(spot, 2),
            "rsi": rsi,
            "hv_20": round(hv_20, 4),
            "calibration": {
                "version": synth_engine.load_calibration().get("version", 0),
                "applied_count": sum(1 for option in chain if option.get("calibrated")),
            },
            "options": chain
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/synth/chain-by-date/{ticker}")
async def get_synthetic_chain_by_date(
    ticker: str,
    date: str = Query(..., description="Trading date in YYYY-MM-DD format"),
    dtes: str = Query("30,40,45,90,180,365", description="Comma-separated DTE list")
):
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    try:
        dte_list = sorted({
            int(x.strip()) for x in dtes.split(",")
            if x.strip()
        })
    except ValueError:
        raise HTTPException(status_code=400, detail="dtes must be comma-separated integers")

    if not dte_list:
        raise HTTPException(status_code=400, detail="At least one DTE is required")

    try:
        start = target_date - timedelta(days=120)
        end = target_date + timedelta(days=1)
        df = yf.download(ticker, start=start.isoformat(), end=end.isoformat(), progress=False, auto_adjust=False)
        if df.empty:
            table_name = f"{ticker.lower()}_1d"
            df = db.get_stock_data(table_name, limit=10000)
            if df.empty:
                raise HTTPException(status_code=404, detail=f"No data for {ticker}")
            df = df.reset_index()
            if "timestamp" not in df.columns:
                df = df.rename(columns={"Date": "timestamp", "date": "timestamp"})
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df[df["timestamp"].dt.date <= target_date].tail(120)
        else:
            df = df.reset_index()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.rename(columns={"Date": "timestamp"})
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        df = df.sort_values("timestamp")
        df = df[df["timestamp"].dt.date <= target_date]
        if len(df) < 25:
            raise HTTPException(status_code=400, detail=f"Insufficient data before {date}")

        actual_date = df.iloc[-1]["timestamp"].date()
        close = df["Close"].astype(float)
        spot = float(close.iloc[-1])

        delta = close.diff()
        avg_gain = delta.clip(lower=0).ewm(com=13, min_periods=14).mean()
        avg_loss = (-delta.clip(upper=0)).ewm(com=13, min_periods=14).mean()
        rs = avg_gain / avg_loss.replace(0, float("nan"))
        rsi_series = 100 - 100 / (1 + rs)
        rsi = float(rsi_series.iloc[-1])

        log_ret = np.log(close / close.shift(1))
        hv_20 = float(log_ret.rolling(20).std().iloc[-1] * np.sqrt(252))
        if not np.isfinite(rsi) or not np.isfinite(hv_20):
            raise HTTPException(status_code=400, detail=f"Insufficient indicator data before {date}")

        chain = synth_engine.generate_chain(actual_date, spot, rsi, hv_20, dte_list=dte_list, ticker=ticker)
        for option in chain:
            option["mid"] = round((option["bid"] + option["ask"]) / 2, 2)

        return {
            "ticker": ticker.upper(),
            "requested_date": date,
            "actual_date": actual_date.isoformat(),
            "spot_price": round(spot, 2),
            "rsi": round(rsi, 1),
            "hv_20": round(hv_20, 4),
            "calibration": {
                "version": synth_engine.load_calibration().get("version", 0),
                "applied_count": sum(1 for option in chain if option.get("calibrated")),
            },
            "dte_list": dte_list,
            "options": chain
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backtest/wheels")
async def backtest_wheels(req: OptionBacktestRequest, current_user: str = Depends(get_current_user)):
    backtester = options_synth.OptionBacktester(db, synth_engine)
    result = backtester.run_wheels(req.ticker, req.start_date, req.end_date, req.initial_capital, **req.params)
    if "error" in result: raise HTTPException(status_code=400, detail=result["error"])
    # DB Save logic...
    return result

@router.post("/backtest/leaps")
async def backtest_leaps(req: OptionBacktestRequest, current_user: str = Depends(get_current_user)):
    backtester = options_synth.OptionBacktester(db, synth_engine)
    result = backtester.run_leaps(req.ticker, req.start_date, req.end_date, req.initial_capital, **req.params)
    return result

@router.post("/backtest/spreads")
async def backtest_spreads(req: OptionBacktestRequest, current_user: str = Depends(get_current_user)):
    backtester = options_synth.OptionBacktester(db, synth_engine)
    result = backtester.run_spreads(req.ticker, req.start_date, req.end_date, req.initial_capital, **req.params)
    return result

@router.get("/backtest/history")
async def get_option_backtest_history(current_user: str = Depends(get_current_user)):
    query = text("SELECT * FROM options_backtest_results WHERE user_id = :user ORDER BY created_at DESC LIMIT 20")
    with db.engine.connect() as conn:
        res = conn.execute(query, {"user": current_user}).fetchall()
    return {"history": [dict(r._mapping) for r in res]}
