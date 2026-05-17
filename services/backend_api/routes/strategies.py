import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from config import db, get_moomoo_provider
from dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["strategies"])

class StrategyRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    buy_conditions: dict
    sell_conditions: dict
    params: Optional[dict] = {}

class BacktestRequest(BaseModel):
    strategy_id: Optional[str] = None
    ticker: str
    start_date: str
    end_date: str
    initial_capital: float = 100000.0
    params: Optional[dict] = {}

def _as_float(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback

def _date_key(value):
    if hasattr(value, "date"):
        return str(value.date())
    return str(value)[:10]

def _normalize_date(value):
    return pd.to_datetime(value).date()

def _display_pct(value):
    return f"{_as_float(value, 0) * 100:.1f}%"

def update_stock_data_range_record(ticker, df):
    if df.empty:
        return
    dates = pd.to_datetime(df.index).date
    start = min(dates).isoformat()
    end = max(dates).isoformat()
    with db.engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stock_data_ranges (
                ticker TEXT NOT NULL,
                interval TEXT NOT NULL,
                data_start_date TEXT NOT NULL,
                data_end_date TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(
            text("DELETE FROM stock_data_ranges WHERE ticker = :ticker AND interval = :interval"),
            {"ticker": ticker.upper(), "interval": "1d"}
        )
        conn.execute(
            text("""
                INSERT INTO stock_data_ranges (ticker, interval, data_start_date, data_end_date, updated_at)
                VALUES (:ticker, :interval, :start, :end, CURRENT_TIMESTAMP)
            """),
            {"ticker": ticker.upper(), "interval": "1d", "start": start, "end": end}
        )

def get_stock_data_range_record(ticker):
    try:
        with db.engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT data_start_date, data_end_date
                    FROM stock_data_ranges
                    WHERE ticker = :ticker AND interval = :interval
                    LIMIT 1
                """),
                {"ticker": ticker.upper(), "interval": "1d"}
            ).fetchone()
        return dict(row._mapping) if row else None
    except Exception:
        return None

def get_backtest_price_frame(ticker, start_date, end_date):
    ticker = str(ticker).strip().upper()
    table_name = f"{ticker.lower()}_1d"
    start = _normalize_date(start_date)
    end = _normalize_date(end_date)

    cached = db.get_stock_data(
        table_name,
        limit=None,
        start=start,
        end=end,
        columns=["Open", "High", "Low", "Close", "Volume"],
    )
    if not cached.empty:
        cached = normalize_yfinance_frame(cached, ticker)

    bounds = db.get_stock_data_bounds(table_name)
    record = get_stock_data_range_record(ticker)
    has_range = False
    if bounds:
        data_start = bounds["start"].date()
        data_end = bounds["end"].date()
        has_range = data_start <= start and data_end >= end
    elif record:
        data_start = _normalize_date(record["data_start_date"])
        data_end = _normalize_date(record["data_end_date"])
        has_range = data_start <= start and data_end >= end

    if cached.empty or not has_range:
        raw = yf.download(ticker, start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(), progress=False, auto_adjust=False)
        frame = normalize_yfinance_frame(raw, ticker)
        if frame.empty or "Close" not in frame.columns:
            raise HTTPException(status_code=400, detail=f"No data found for {ticker}")
        frame.index = pd.to_datetime(frame.index).tz_localize(None)
        db.save_stock_data(frame, table_name)
        cached = db.get_stock_data(
            table_name,
            limit=None,
            start=start,
            end=end,
            columns=["Open", "High", "Low", "Close", "Volume"],
        )
        cached = normalize_yfinance_frame(cached, ticker)
        if not record:
            update_stock_data_range_record(ticker, frame)

    cached.index = pd.to_datetime(cached.index).tz_localize(None)
    filtered = cached[(cached.index.date >= start) & (cached.index.date <= end)].copy()
    if filtered.empty or "Close" not in filtered.columns:
        raise HTTPException(status_code=400, detail=f"No stored price data for {ticker} in requested range")
    return filtered

def run_core_etf_sleeve(assets, start_date, end_date, initial_capital, rebalance="quarterly"):
    clean_assets = []
    for asset in assets or []:
        ticker = str(asset.get("ticker", "")).strip().upper()
        weight = _as_float(asset.get("weight"), 0)
        if ticker and weight > 0:
            clean_assets.append({"ticker": ticker, "weight": weight})

    if not clean_assets:
        clean_assets = [{"ticker": "QQQ", "weight": 0.5}, {"ticker": "VOO", "weight": 0.5}]

    total_weight = sum(a["weight"] for a in clean_assets) or 1
    if total_weight > 1.000001:
        raise HTTPException(status_code=400, detail="Portfolio holding weights cannot exceed 100%")
    for asset in clean_assets:
        asset["weight"] = asset["weight"] / total_weight

    price_series = {}
    all_dates = set()
    for asset in clean_assets:
        frame = get_backtest_price_frame(asset["ticker"], start_date, end_date)
        if frame.empty or "Close" not in frame.columns:
            raise HTTPException(status_code=400, detail=f"No data found for core ETF {asset['ticker']}")
        closes = frame["Close"].dropna().astype(float)
        series = {_date_key(idx): float(value) for idx, value in closes.items()}
        price_series[asset["ticker"]] = series
        all_dates.update(series.keys())

    dates = sorted(all_dates)
    positions = {}
    asset_details = []
    for asset in clean_assets:
        ticker = asset["ticker"]
        first_date = next((d for d in dates if d in price_series[ticker]), None)
        if not first_date:
            continue
        first_price = price_series[ticker][first_date]
        allocated = initial_capital * asset["weight"]
        shares = allocated / first_price if first_price > 0 else 0
        positions[ticker] = {"shares": shares, "cost": allocated, "first_price": first_price}

    last_prices = {}
    curve = []
    rebalance_log = []
    last_rebalance_period = None
    for date in dates:
        value = 0
        components = {}
        for asset in clean_assets:
            ticker = asset["ticker"]
            if date in price_series[ticker]:
                last_prices[ticker] = price_series[ticker][date]
            if ticker in positions and ticker in last_prices:
                component_value = positions[ticker]["shares"] * last_prices[ticker]
                components[ticker] = round(component_value, 2)
                value += component_value

        dt = datetime.strptime(date, "%Y-%m-%d")
        if rebalance == "monthly":
            period_key = f"{dt.year}-{dt.month:02d}"
        elif rebalance == "quarterly":
            period_key = f"{dt.year}-Q{((dt.month - 1) // 3) + 1}"
        elif rebalance == "annual":
            period_key = str(dt.year)
        else:
            period_key = None

        if period_key and last_rebalance_period and period_key != last_rebalance_period and value > 0:
            for asset in clean_assets:
                ticker = asset["ticker"]
                if ticker in last_prices and last_prices[ticker] > 0:
                    target_value = value * asset["weight"]
                    positions[ticker]["shares"] = target_value / last_prices[ticker]
                    components[ticker] = round(target_value, 2)
            rebalance_log.append({
                "type": "CORE_REBALANCE",
                "date": date,
                "price": 0,
                "qty": "-",
                "pl": 0,
                "memo": f"Rebalanced core ETF sleeve to target weights ({rebalance})"
            })
        if period_key:
            last_rebalance_period = period_key

        curve.append({"date": date, "equity": round(value, 2), "components": components})

    final_components = curve[-1]["components"] if curve else {}
    for asset in clean_assets:
        ticker = asset["ticker"]
        cost = positions.get(ticker, {}).get("cost", 0)
        final_value = final_components.get(ticker, 0)
        asset_details.append({
            "ticker": ticker,
            "weight": round(asset["weight"], 4),
            "initial_value": round(cost, 2),
            "final_value": round(final_value, 2),
            "profit": round(final_value - cost, 2),
            "return_pct": round(((final_value - cost) / cost * 100), 2) if cost else 0
        })

    final_value = curve[-1]["equity"] if curve else initial_capital
    return {
        "initial_value": round(initial_capital, 2),
        "final_value": round(final_value, 2),
        "profit": round(final_value - initial_capital, 2),
        "return_pct": round(((final_value - initial_capital) / initial_capital * 100), 2) if initial_capital else 0,
        "assets": asset_details,
        "equity_curve": curve,
        "trades": [{
            "type": "CORE_BUY",
            "date": curve[0]["date"] if curve else start_date,
            "price": 0,
            "qty": "-",
            "pl": 0,
            "memo": ", ".join(f"{a['ticker']} {a['weight'] * 100:.1f}%" for a in clean_assets)
        }] + rebalance_log
    }

def build_benchmark_result(name, assets, req: BacktestRequest):
    try:
        benchmark = run_core_etf_sleeve(assets, req.start_date, req.end_date, req.initial_capital, rebalance="none")
        curve = []
        for point in benchmark.get("equity_curve", []):
            dt = datetime.strptime(point["date"], "%Y-%m-%d")
            curve.append({
                "time": int(dt.timestamp()),
                "value": point["equity"]
            })
        return {
            "name": name,
            "assets": benchmark.get("assets", []),
            "initial_value": benchmark.get("initial_value", round(req.initial_capital, 2)),
            "final_value": benchmark.get("final_value", round(req.initial_capital, 2)),
            "return_pct": benchmark.get("return_pct", 0),
            "profit": benchmark.get("profit", 0),
            "equity_curve": curve
        }
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        return {
            "name": name,
            "error": str(detail)
        }

def build_backtest_benchmarks(req: BacktestRequest, portfolio=False):
    if portfolio:
        return [
            build_benchmark_result("QQQ Buy & Hold", [{"ticker": "QQQ", "weight": 1.0}], req),
            build_benchmark_result("VOO Buy & Hold", [{"ticker": "VOO", "weight": 1.0}], req),
            build_benchmark_result("QQQ/VOO 50/50", [{"ticker": "QQQ", "weight": 0.5}, {"ticker": "VOO", "weight": 0.5}], req)
        ]
    ticker = str(req.ticker or "QQQ").strip().upper()
    return [
        build_benchmark_result(f"{ticker} Buy & Hold", [{"ticker": ticker, "weight": 1.0}], req)
    ]

def build_assumption_panel(req: BacktestRequest, strategy_id, params=None, portfolio=False):
    params = params or {}
    is_option = str(strategy_id) in {"system_wheels", "system_leaps", "system_bull_call", "system_bear_put", "system_bull_put"}
    is_portfolio_options = portfolio and _as_float(params.get("options_pct"), 0) > 0
    uses_options = is_option or is_portfolio_options

    if is_option:
        fill_model = (
            "Synthetic option bid/ask model. fill_slippage 0.00 uses mid; "
            "0.50 approximates natural ask for buys and natural bid for sells."
        )
    elif is_portfolio_options:
        option_params = params.get("option_params") or {}
        fill_model = (
            "Core sleeve uses daily close. Option sleeve uses synthetic bid/ask; "
            f"fill_slippage={option_params.get('fill_slippage', 0.10)}."
        )
    else:
        fill_model = "Daily close fill model for stock/ETF entries, exits, and benchmark calculations."

    if str(strategy_id) == "system_buy_hold":
        capital_basis = (
            f"Invested capital {_display_pct(params.get('allocation_pct', 1.0))}; "
            f"rebalance={params.get('rebalance', 'none')}."
        )
    elif portfolio:
        capital_basis = (
            f"Core sleeve {_display_pct(params.get('core_pct', 0.70))}, "
            f"options sleeve {_display_pct(params.get('options_pct', 0.30))}, "
            f"cash sleeve {_display_pct(max(1 - _as_float(params.get('core_pct'), 0.70) - _as_float(params.get('options_pct'), 0.30), 0))}."
        )
    elif is_option:
        capital_basis = (
            "Option strategy sizes positions from configured risk/capital utilization. "
            f"risk_pct={params.get('risk_pct', '-')}, capital_utilization={params.get('capital_utilization', params.get('risk_pct', '-'))}."
        )
    else:
        capital_basis = "Single-ticker signal strategy deploys available cash into whole shares at each buy signal."

    return {
        "data_source": "Local daily OHLCV cache backed by yfinance auto-fill when requested dates exceed stored coverage.",
        "data_range": {
            "requested_start": req.start_date,
            "requested_end": req.end_date
        },
        "strategy_parameters": params,
        "fill_model": fill_model,
        "capital_utilization_basis": capital_basis,
        "option_chain_source": (
            "Calibrated synthetic option chain generated from historical underlying prices, historical volatility, RSI context, Black-Scholes greeks, and Schwab snapshot-derived bucket adjustments when available."
            if uses_options else
            "Not used for this stock/ETF-only backtest."
        ),
        "benchmark_method": (
            "Portfolio tests compare against QQQ, VOO, and a QQQ/VOO 50/50 buy-and-hold basket."
            if portfolio else
            f"Strategy compares against buy-and-hold of {str(req.ticker or 'QQQ').upper()} over the same dates."
        )
    }

def attach_report_context(result, req: BacktestRequest, strategy_id, params=None, portfolio=False):
    result["assumptions"] = build_assumption_panel(req, strategy_id, params or {}, portfolio=portfolio)
    result["benchmarks"] = build_backtest_benchmarks(req, portfolio=portfolio)
    return result

def _run_option_sleeve(backtester, sid, ticker, start_date, end_date, initial_capital, params, df_opt):
    if sid == "system_wheels":
        return backtester.run_wheels(ticker, start_date, end_date, initial_capital, df=df_opt)
    if sid == "system_leaps":
        return backtester.run_leaps(
            ticker,
            start_date,
            end_date,
            initial_capital,
            delta_target=params.get("delta_target", 0.8),
            dte_target=params.get("dte_target", 365),
            capital_utilization=params.get("capital_utilization", params.get("risk_pct", 0.30)),
            roll_dte=params.get("roll_dte", 60),
            fill_slippage=params.get("fill_slippage", 0.10),
            df=df_opt
        )
    if sid == "system_bear_put":
        return backtester.run_spreads(
            ticker, start_date, end_date, initial_capital,
            strategy_type="BEAR_PUT",
            dte_target=params.get("dte_target", 40),
            risk_pct=params.get("risk_pct", 0.30),
            long_delta_target=params.get("long_delta_target", -0.60),
            short_delta_target=params.get("short_delta_target", -0.30),
            spread_width=params.get("spread_width", 20),
            delta_tolerance=params.get("delta_tolerance", 0.15),
            fill_slippage=params.get("fill_slippage", 0.10),
            open_interval_days=params.get("open_interval_days"),
            max_open_positions=params.get("max_open_positions", 4),
            entry_rsi_max=params.get("entry_rsi_max", 50),
            df=df_opt
        )
    if sid == "system_bull_put":
        return backtester.run_spreads(
            ticker, start_date, end_date, initial_capital,
            strategy_type="BULL_PUT",
            dte_target=params.get("dte_target", 40),
            risk_pct=params.get("risk_pct", 0.30),
            long_delta_target=params.get("long_delta_target", -0.10),
            short_delta_target=params.get("short_delta_target", -0.30),
            spread_width=params.get("spread_width", 20),
            delta_tolerance=params.get("delta_tolerance", 0.15),
            fill_slippage=params.get("fill_slippage", 0.10),
            open_interval_days=params.get("open_interval_days"),
            max_open_positions=params.get("max_open_positions", 4),
            df=df_opt
        )
    return backtester.run_spreads(
        ticker, start_date, end_date, initial_capital,
        strategy_type="BULL_CALL",
        dte_target=params.get("dte_target", 40),
        risk_pct=params.get("risk_pct", 0.30),
        long_delta_target=params.get("long_delta_target", 0.60),
        short_delta_target=params.get("short_delta_target", 0.30),
        spread_width=params.get("spread_width", 20),
        delta_tolerance=params.get("delta_tolerance", 0.15),
        fill_slippage=params.get("fill_slippage", 0.10),
        open_interval_days=params.get("open_interval_days"),
        max_open_positions=params.get("max_open_positions", 4),
        entry_rsi_min=params.get("entry_rsi_min", 50),
        df=df_opt
    )

def build_portfolio_backtest(req: BacktestRequest):
    from options_synth import OptionBacktester, OptionSynth

    params = req.params or {}
    core_pct = max(_as_float(params.get("core_pct"), 0.70), 0)
    options_pct = max(_as_float(params.get("options_pct"), 0.30), 0)
    total_pct = core_pct + options_pct
    if total_pct <= 0:
        raise HTTPException(status_code=400, detail="Portfolio sleeves must have positive allocation")
    if total_pct > 1.000001:
        raise HTTPException(status_code=400, detail="Portfolio sleeve allocations cannot exceed 100%")
    cash_pct = max(1 - total_pct, 0)

    core_capital = req.initial_capital * core_pct
    options_capital = req.initial_capital * options_pct
    cash_value = req.initial_capital * cash_pct
    option_strategy_id = params.get("option_strategy_id", "system_bull_call")
    option_ticker = str(params.get("option_ticker") or req.ticker or "QQQ").upper()
    option_params = params.get("option_params") or {}
    core_assets = params.get("core_assets") or [
        {"ticker": "QQQ", "weight": 0.5},
        {"ticker": "VOO", "weight": 0.5}
    ]

    core = run_core_etf_sleeve(core_assets, req.start_date, req.end_date, core_capital, params.get("rebalance", "quarterly"))

    option_underlying_prices = {}
    if options_capital > 0:
        df_opt = get_backtest_price_frame(option_ticker, req.start_date, req.end_date)
        if df_opt.empty:
            raise HTTPException(status_code=400, detail=f"No data found for options ticker {option_ticker}")
        option_underlying_prices = {
            _date_key(idx): round(float(value), 2)
            for idx, value in df_opt["Close"].dropna().astype(float).items()
        } if "Close" in df_opt.columns else {}

        backtester = OptionBacktester(db, OptionSynth())
        options = _run_option_sleeve(backtester, option_strategy_id, option_ticker, req.start_date, req.end_date, options_capital, option_params, df_opt)
        if "error" in options:
            raise HTTPException(status_code=400, detail=options["error"])
    else:
        options = {"final_capital": 0, "trades": [], "equity_curve": [], "metrics": {}}

    rebalance = params.get("rebalance", "quarterly")
    core_curve = {p["date"]: p for p in core["equity_curve"]}
    option_curve = {p["date"]: p for p in options.get("equity_curve", [])}
    all_dates = sorted(set(core_curve.keys()) | set(option_curve.keys()))
    core_value = core_capital
    options_value = options_capital
    last_core_index = core_capital
    last_options_index = options_capital
    last_rebalance_period = None
    portfolio_events = []
    equity_curve = []
    for date in all_dates:
        dt = datetime.strptime(date, "%Y-%m-%d")
        if rebalance == "monthly":
            period_key = f"{dt.year}-{dt.month:02d}"
        elif rebalance == "quarterly":
            period_key = f"{dt.year}-Q{((dt.month - 1) // 3) + 1}"
        elif rebalance == "annual":
            period_key = str(dt.year)
        else:
            period_key = None

        if date in core_curve:
            next_core_index = core_curve[date]["equity"]
            if last_core_index > 0:
                core_value *= next_core_index / last_core_index
            last_core_index = next_core_index
        if date in option_curve:
            next_options_index = option_curve[date]["equity"]
            if last_options_index > 0:
                options_value *= next_options_index / last_options_index
            last_options_index = next_options_index

        if period_key and last_rebalance_period and period_key != last_rebalance_period:
            total_value = core_value + options_value + cash_value
            before_core = core_value
            before_options = options_value
            before_cash = cash_value
            core_value = total_value * core_pct
            options_value = total_value * options_pct
            cash_value = total_value * cash_pct
            portfolio_events.append({
                "type": "PORTFOLIO_REBALANCE",
                "date": date,
                "core_before": round(before_core, 2),
                "options_before": round(before_options, 2),
                "cash_before": round(before_cash, 2),
                "core_after": round(core_value, 2),
                "options_after": round(options_value, 2),
                "cash_after": round(cash_value, 2),
                "memo": f"Rebalanced portfolio sleeves to Core {core_pct * 100:.1f}% / Options {options_pct * 100:.1f}% / Cash {cash_pct * 100:.1f}%"
            })
        if period_key:
            last_rebalance_period = period_key

        equity_curve.append({
            "time": int(dt.timestamp()),
            "value": round(core_value + options_value + cash_value, 2),
            "core_value": round(core_value, 2),
            "options_value": round(options_value, 2),
            "cash_value": round(cash_value, 2),
            "underlying_price": option_underlying_prices.get(date)
        })

    final_core = equity_curve[-1]["core_value"] if equity_curve else core_capital
    final_options = equity_curve[-1]["options_value"] if equity_curve else options_capital
    final_cash = equity_curve[-1].get("cash_value", cash_value) if equity_curve else cash_value
    final_value = final_core + final_options + final_cash
    total_profit = final_value - req.initial_capital
    core_profit = final_core - core_capital
    options_profit = final_options - options_capital
    closed_trades = [t for t in options.get("trades", []) if t.get("event") == "CLOSE" or str(t.get("type", "")).startswith(("SELL_", "CLOSE_"))]
    winning_trades = [t for t in closed_trades if t.get("pl", 0) > 0]

    core_scale = final_core / core["final_value"] if core.get("final_value") else 1
    scaled_core_assets = []
    for asset in core["assets"]:
        initial_value = asset.get("initial_value", 0)
        final_asset_value = asset.get("final_value", 0) * core_scale
        scaled_core_assets.append({
            **asset,
            "final_value": round(final_asset_value, 2),
            "profit": round(final_asset_value - initial_value, 2),
            "return_pct": round(((final_asset_value - initial_value) / initial_value * 100), 2) if initial_value else 0
        })

    sleeves = {
        "core": {
            "name": "Core ETF",
            "initial_value": round(core_capital, 2),
            "final_value": round(final_core, 2),
            "profit": round(core_profit, 2),
            "return_pct": round((core_profit / core_capital * 100), 2) if core_capital else 0,
            "contribution_pct": round((core_profit / total_profit * 100), 2) if total_profit else 0,
            "assets": scaled_core_assets,
            "events": core["trades"]
        },
        "options": {
            "name": "Options",
            "strategy_id": option_strategy_id,
            "ticker": option_ticker,
            "initial_value": round(options_capital, 2),
            "final_value": round(final_options, 2),
            "profit": round(options_profit, 2),
            "return_pct": round((options_profit / options_capital * 100), 2) if options_capital else 0,
            "contribution_pct": round((options_profit / total_profit * 100), 2) if total_profit else 0
        },
        "cash": {
            "name": "Cash",
            "initial_value": round(req.initial_capital * cash_pct, 2),
            "final_value": round(final_cash, 2),
            "profit": round(final_cash - (req.initial_capital * cash_pct), 2),
            "return_pct": 0,
            "contribution_pct": 0
        }
    }

    result = {
        "summary": {
            "strategy_name": "Portfolio: Core ETF + Options",
            "ticker": "PORTFOLIO",
            "initial_capital": req.initial_capital,
            "final_value": round(final_value, 2),
            "total_return": round((total_profit / req.initial_capital * 100), 2) if req.initial_capital else 0,
            "total_trades": len(options.get("trades", [])),
            "win_rate": round((len(winning_trades) / max(len(closed_trades), 1) * 100), 2),
            "ending_cash": options.get("metrics", {}).get("ending_cash"),
            "ending_locked_risk": options.get("metrics", {}).get("ending_locked_risk"),
            "ending_available_cash": options.get("metrics", {}).get("ending_available_cash")
        },
        "params": {
            "portfolio": params,
            "portfolio_rebalance_events": portfolio_events,
            **(options.get("metrics", {}) or {})
        },
        "sleeves": sleeves,
        "trades": options.get("trades", []),
        "equity_curve": equity_curve
    }
    return attach_report_context(result, req, "system_portfolio_combo", params, portfolio=True)

def build_buy_hold_backtest(req: BacktestRequest):
    params = req.params or {}
    allocation_pct = min(max(_as_float(params.get("allocation_pct"), 1.0), 0), 1)
    assets = params.get("assets") or params.get("core_assets") or [
        {"ticker": req.ticker or "QQQ", "weight": 1.0}
    ]
    total_weight = sum(max(_as_float(asset.get("weight"), 0), 0) for asset in assets)
    if total_weight > 1.000001:
        raise HTTPException(status_code=400, detail="Buy & Hold holding weights cannot exceed 100%")
    invested_capital = req.initial_capital * allocation_pct
    cash_value = req.initial_capital - invested_capital
    core = run_core_etf_sleeve(assets, req.start_date, req.end_date, invested_capital, params.get("rebalance", "none"))
    equity_curve = []
    for point in core["equity_curve"]:
        dt = datetime.strptime(point["date"], "%Y-%m-%d")
        equity_curve.append({
            "time": int(dt.timestamp()),
            "value": round(point["equity"] + cash_value, 2),
            "core_value": point["equity"],
            "cash_value": round(cash_value, 2)
        })
    final_invested = core["final_value"]
    final_value = final_invested + cash_value
    total_profit = final_value - req.initial_capital
    result = {
        "summary": {
            "strategy_name": "Long-Term Buy & Hold",
            "ticker": "PORTFOLIO",
            "initial_capital": req.initial_capital,
            "final_value": round(final_value, 2),
            "total_return": round((total_profit / req.initial_capital * 100), 2) if req.initial_capital else 0,
            "total_trades": len(core["assets"]),
            "win_rate": 100 if total_profit > 0 else 0
        },
        "params": {
            "buy_hold": params,
            "allocation_pct": allocation_pct
        },
        "sleeves": {
            "core": {
                "name": "Buy & Hold",
                "initial_value": round(invested_capital, 2),
                "final_value": round(final_invested, 2),
                "profit": round(final_invested - invested_capital, 2),
                "return_pct": core["return_pct"],
                "assets": core["assets"],
                "events": core["trades"]
            },
            "cash": {
                "name": "Cash",
                "initial_value": round(cash_value, 2),
                "final_value": round(cash_value, 2),
                "profit": 0,
                "return_pct": 0
            }
        },
        "trades": core["trades"],
        "equity_curve": equity_curve
    }
    return attach_report_context(result, req, "system_buy_hold", params, portfolio=True)

def normalize_yfinance_frame(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Return a single-ticker OHLCV frame with plain column names."""
    if not isinstance(df.columns, pd.MultiIndex):
        return df

    symbol = ticker.upper()
    for level in range(df.columns.nlevels):
        level_values = [str(v).upper() for v in df.columns.get_level_values(level)]
        if symbol in level_values:
            return df.xs(
                df.columns.get_level_values(level)[level_values.index(symbol)],
                axis=1,
                level=level,
            )

    # If yfinance returns a single-symbol MultiIndex without the symbol label,
    # keep the level that contains OHLCV names and drop the rest.
    ohlcv = {"OPEN", "HIGH", "LOW", "CLOSE", "ADJ CLOSE", "VOLUME"}
    for level in range(df.columns.nlevels):
        level_values = {str(v).upper() for v in df.columns.get_level_values(level)}
        if level_values & ohlcv:
            out = df.copy()
            out.columns = df.columns.get_level_values(level)
            return out

    out = df.copy()
    out.columns = [
        next((part for part in col if str(part).upper() in ohlcv), col[-1])
        for col in df.columns
    ]
    return out

@router.get("/strategies")
def get_strategies(current_user: str = Depends(get_current_user)):
    # Include system strategies
    system_strats = [
        {
            "id": "system_rsi",
            "name": "System RSI Strategy",
            "description": "Standard RSI mean reversion (Buy < 30, Sell > 70)",
            "buy_conditions": {"rsi_enabled": True, "rsi_below": 30},
            "sell_conditions": {"rsi_enabled": True, "rsi_above": 70},
            "params": {"initial_capital": 100000, "stop_loss": 5, "take_profit": 10}
        },
        {
            "id": "system_sma",
            "name": "System SMA Cross",
            "description": "SMA 20/50 Golden Cross strategy",
            "buy_conditions": {"sma_cross_up": True},
            "sell_conditions": {"sma_cross_down": True},
            "params": {"initial_capital": 10000}
        },
        {
            "id": "system_macd",
            "name": "System MACD",
            "description": "MACD Golden Cross/Death Cross",
            "buy_conditions": {"macd_cross_up": True},
            "sell_conditions": {"macd_cross_down": True},
            "params": {"initial_capital": 10000}
        },
        {
            "id": "system_bollinger",
            "name": "System Bollinger Bands",
            "description": "Buy at lower band, sell at upper band",
            "buy_conditions": {"bb_lower": True},
            "sell_conditions": {"bb_upper": True},
            "params": {"initial_capital": 10000}
        },
        {
            "id": "system_wheels",
            "name": "Option Strategy: WHEELS",
            "description": "Cash-secured put + Covered call cycle",
            "type": "option",
            "params": {"initial_capital": 50000}
        },
        {
            "id": "system_leaps",
            "name": "Option Strategy: LEAPS",
            "description": "Deep in-the-money long-term calls",
            "type": "option",
            "params": {"initial_capital": 50000}
        },
        {
            "id": "system_bull_call",
            "name": "Option: Bull Call Spread (Debit)",
            "description": "Buy low strike Call, Sell high strike Call.",
            "type": "option",
            "params": {"initial_capital": 100000}
        },
        {
            "id": "system_bear_put",
            "name": "Option: Bear Put Spread (Debit)",
            "description": "Buy high strike Put, Sell low strike Put.",
            "type": "option",
            "params": {"initial_capital": 100000}
        },
        {
            "id": "system_bull_put",
            "name": "Option: Bull Put Spread (Credit)",
            "description": "Sell high strike Put, Buy low strike Put.",
            "type": "option",
            "params": {"initial_capital": 100000}
        },
        {
            "id": "system_portfolio_combo",
            "name": "Portfolio: Core ETF + Options",
            "description": "Configurable ETF core sleeve plus one options strategy sleeve.",
            "type": "portfolio",
            "params": {"initial_capital": 100000, "core_pct": 0.70, "options_pct": 0.30}
        },
        {
            "id": "system_buy_hold",
            "name": "Long-Term Buy & Hold",
            "description": "Value-investing style portfolio: hold selected stocks or ETFs with configurable allocations.",
            "type": "portfolio",
            "params": {
                "initial_capital": 100000,
                "allocation_pct": 1.0,
                "assets": [{"ticker": "QQQ", "weight": 1.0}],
                "rebalance": "none"
            }
        }
    ]
    
    try:
        q = text("SELECT id, name, description, buy_conditions, sell_conditions, params FROM user_strategies WHERE user_id = :user")
        with db.engine.connect() as conn:
            rows = conn.execute(q, {"user": current_user}).fetchall()
        
        user_strats = []
        for r in rows:
            d = dict(r._mapping)
            # Ensure JSON fields are parsed if they come back as strings
            for field in ['buy_conditions', 'sell_conditions', 'params']:
                if isinstance(d.get(field), str):
                    d[field] = json.loads(d[field])
            user_strats.append(d)
            
        return system_strats + user_strats
    except Exception as e:
        print(f"Error loading strategies: {e}")
        return system_strats

@router.post("/strategies")
def create_strategy(req: StrategyRequest, current_user: str = Depends(get_current_user)):
    try:
        q = text("""
            INSERT INTO user_strategies (user_id, name, description, buy_conditions, sell_conditions, params)
            VALUES (:user, :name, :desc, :buy, :sell, :params)
            RETURNING id
        """)
        with db.engine.connect() as conn:
            res = conn.execute(q, {
                "user": current_user, "name": req.name, "desc": req.description,
                "buy": json.dumps(req.buy_conditions), "sell": json.dumps(req.sell_conditions),
                "params": json.dumps(req.params)
            })
            new_id = res.fetchone()[0]
            conn.commit()
        return {"id": new_id, "message": "Strategy created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/strategies/{strategy_id}")
def delete_strategy(strategy_id: int, current_user: str = Depends(get_current_user)):
    try:
        q = text("DELETE FROM user_strategies WHERE id = :id AND user_id = :user")
        with db.engine.connect() as conn:
            conn.execute(q, {"id": strategy_id, "user": current_user})
            conn.commit()
        return {"message": "Strategy deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backtest")
def run_backtest(req: BacktestRequest, current_user: str = Depends(get_current_user)):
    try:
        sid = str(req.strategy_id)
        strategy = None
        
        if sid.startswith("system_"):
            if sid == "system_rsi":
                strategy = {
                    "name": "System RSI",
                    "buy_conditions": {"rsi_enabled": True, "rsi_below": 30},
                    "sell_conditions": {"rsi_enabled": True, "rsi_above": 70},
                    "params": {"stop_loss": 0.05, "take_profit": 0.10}
                }
            elif sid == "system_sma":
                strategy = {
                    "name": "System SMA",
                    "buy_conditions": {"sma_cross_up": True},
                    "sell_conditions": {"sma_cross_down": True},
                    "params": {}
                }
            elif sid == "system_macd":
                strategy = {
                    "name": "System MACD",
                    "buy_conditions": {"macd_cross_up": True},
                    "sell_conditions": {"macd_cross_down": True},
                    "params": {}
                }
            elif sid == "system_bollinger":
                strategy = {
                    "name": "System Bollinger Bands",
                    "buy_conditions": {"bb_lower": True},
                    "sell_conditions": {"bb_upper": True},
                    "params": {}
                }
            elif sid == "system_portfolio_combo":
                return build_portfolio_backtest(req)
            elif sid == "system_buy_hold":
                return build_buy_hold_backtest(req)
            elif sid in ["system_wheels", "system_leaps", "system_bull_call", "system_bear_put", "system_bull_put"]:
                from options_synth import OptionBacktester, OptionSynth
                backtester = OptionBacktester(db, OptionSynth())
                params = req.params or {}
                
                # For Options backtest, we also fetch fresh data to ensure 5y+ availability
                df_opt = get_backtest_price_frame(req.ticker, req.start_date, req.end_date)
                
                res = {}
                if sid == "system_wheels":
                    res = backtester.run_wheels(req.ticker, req.start_date, req.end_date, req.initial_capital, df=df_opt)
                elif sid == "system_leaps":
                    res = backtester.run_leaps(
                        req.ticker,
                        req.start_date,
                        req.end_date,
                        req.initial_capital,
                        delta_target=params.get("delta_target", 0.8),
                        dte_target=params.get("dte_target", 365),
                        capital_utilization=params.get("capital_utilization", params.get("risk_pct", 0.30)),
                        roll_dte=params.get("roll_dte", 60),
                        fill_slippage=params.get("fill_slippage", 0.10),
                        df=df_opt
                    )
                elif sid == "system_bull_call":
                    res = backtester.run_spreads(
                        req.ticker, req.start_date, req.end_date, req.initial_capital,
                        strategy_type="BULL_CALL",
                        dte_target=params.get("dte_target", 40),
                        risk_pct=params.get("risk_pct", 0.30),
                        long_delta_target=params.get("long_delta_target", 0.60),
                        short_delta_target=params.get("short_delta_target", 0.30),
                        spread_width=params.get("spread_width", 20),
                        delta_tolerance=params.get("delta_tolerance", 0.15),
                        fill_slippage=params.get("fill_slippage", 0.10),
                        open_interval_days=params.get("open_interval_days"),
                        max_open_positions=params.get("max_open_positions", 4),
                        entry_rsi_min=params.get("entry_rsi_min", 50),
                        df=df_opt
                    )
                elif sid == "system_bear_put":
                    res = backtester.run_spreads(
                        req.ticker, req.start_date, req.end_date, req.initial_capital,
                        strategy_type="BEAR_PUT",
                        dte_target=params.get("dte_target", 40),
                        risk_pct=params.get("risk_pct", 0.30),
                        long_delta_target=params.get("long_delta_target", -0.60),
                        short_delta_target=params.get("short_delta_target", -0.30),
                        spread_width=params.get("spread_width", 20),
                        delta_tolerance=params.get("delta_tolerance", 0.15),
                        fill_slippage=params.get("fill_slippage", 0.10),
                        open_interval_days=params.get("open_interval_days"),
                        max_open_positions=params.get("max_open_positions", 4),
                        entry_rsi_max=params.get("entry_rsi_max", 50),
                        df=df_opt
                    )
                elif sid == "system_bull_put":
                    res = backtester.run_spreads(
                        req.ticker, req.start_date, req.end_date, req.initial_capital,
                        strategy_type="BULL_PUT",
                        dte_target=params.get("dte_target", 40),
                        risk_pct=params.get("risk_pct", 0.30),
                        long_delta_target=params.get("long_delta_target", -0.10),
                        short_delta_target=params.get("short_delta_target", -0.30),
                        spread_width=params.get("spread_width", 20),
                        delta_tolerance=params.get("delta_tolerance", 0.15),
                        fill_slippage=params.get("fill_slippage", 0.10),
                        open_interval_days=params.get("open_interval_days"),
                        max_open_positions=params.get("max_open_positions", 4),
                        df=df_opt
                    )
                
                if "error" in res:
                    raise HTTPException(status_code=400, detail=res["error"])
                
                # Normalize response for UI
                closed_trades = [t for t in res['trades'] if t.get('event') == 'CLOSE' or str(t.get('type', '')).startswith(('SELL_', 'CLOSE_'))]
                winning_trades = [t for t in closed_trades if t.get('pl', 0) > 0]
                total_return = (res['final_capital'] - req.initial_capital) / req.initial_capital
                result = {
                    "summary": {
                        "strategy_name": f"Option: {res.get('strategy', sid)}",
                        "ticker": req.ticker.upper(),
                        "initial_capital": req.initial_capital,
                        "final_value": res['final_capital'],
                        "total_return": round(total_return * 100, 2),
                        "total_trades": len(res['trades']),
                        "win_rate": round((len(winning_trades) / max(len(closed_trades), 1) * 100), 2),
                        "ending_cash": res.get("metrics", {}).get("ending_cash"),
                        "ending_locked_risk": res.get("metrics", {}).get("ending_locked_risk"),
                        "ending_locked_collateral": res.get("metrics", {}).get("ending_locked_collateral"),
                        "ending_available_cash": res.get("metrics", {}).get("ending_available_cash"),
                        "open_positions": res.get("metrics", {}).get("open_positions")
                    },
                    "params": res.get("metrics", {}),
                    "trades": res['trades'],
                    "equity_curve": [{
                        "time": int(datetime.strptime(e['date'], '%Y-%m-%d').timestamp()),
                        "value": e['equity'],
                        "underlying_price": e.get("underlying_price"),
                        "cash": e.get("cash"),
                        "option_value": e.get("option_value"),
                        "locked_risk": e.get("locked_risk"),
                        "locked_collateral": e.get("locked_collateral"),
                        "available_cash": e.get("available_cash"),
                        "active_positions": e.get("active_positions")
                    } for e in res['equity_curve']]
                }
                return attach_report_context(result, req, sid, {**params, **(res.get("metrics", {}) or {})}, portfolio=False)
        else:
            # Load from DB
            q = text("SELECT name, buy_conditions, sell_conditions, params FROM user_strategies WHERE id = :id AND user_id = :user")
            with db.engine.connect() as conn:
                res = conn.execute(q, {"id": int(sid), "user": current_user}).fetchone()
                if res:
                    r = dict(res._mapping)
                    strategy = {
                        "name": r['name'],
                        "buy_conditions": json.loads(r['buy_conditions']) if isinstance(r['buy_conditions'], str) else r['buy_conditions'],
                        "sell_conditions": json.loads(r['sell_conditions']) if isinstance(r['sell_conditions'], str) else r['sell_conditions'],
                        "params": json.loads(r['params']) if isinstance(r['params'], str) else r['params']
                    }

                    base_strategy_id = str((strategy.get("params") or {}).get("base_strategy_id", ""))
                    if base_strategy_id.startswith("system_"):
                        saved_params = dict(strategy.get("params") or {})
                        saved_params.pop("base_strategy_id", None)
                        saved_params.pop("saved_ticker", None)
                        saved_params.pop("saved_period", None)
                        merged_params = {**saved_params, **(req.params or {})}
                        delegated_req = BacktestRequest(
                            strategy_id=base_strategy_id,
                            ticker=req.ticker,
                            start_date=req.start_date,
                            end_date=req.end_date,
                            initial_capital=req.initial_capital,
                            params=merged_params
                        )
                        delegated = run_backtest(delegated_req, current_user)
                        if isinstance(delegated, dict) and delegated.get("summary"):
                            delegated["summary"]["strategy_name"] = strategy["name"]
                            delegated["summary"]["saved_strategy_id"] = sid
                        return delegated
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # Fetch data
        df = get_backtest_price_frame(req.ticker, req.start_date, req.end_date)
        if df.empty:
            raise HTTPException(status_code=400, detail="No data found for ticker")
        if "Close" not in df.columns:
            raise HTTPException(status_code=400, detail="Downloaded price data does not include Close prices")

        # Compute indicators
        df['rsi'] = 50 # Fallback
        try:
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
        except: pass
        
        df['sma20'] = df['Close'].rolling(window=20).mean()
        df['sma50'] = df['Close'].rolling(window=50).mean()
        
        # Bollinger Bands
        std = df['Close'].rolling(window=20).std()
        df['bb_upper'] = df['sma20'] + (std * 2)
        df['bb_lower'] = df['sma20'] - (std * 2)
        
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        # Simple Engine
        capital = req.initial_capital
        position = 0
        in_position = False
        entry_price = 0
        trades = []
        equity_curve = []

        buy_c = strategy.get("buy_conditions") or {}
        sell_c = strategy.get("sell_conditions") or {}
        params = strategy.get("params") or {}
        stop_loss = params.get('stop_loss', 0) / 100.0
        take_profit = params.get('take_profit', 0) / 100.0

        for i, (idx, row) in enumerate(df.iterrows()):
            price = float(row['Close'])
            date = idx
            equity = capital + position * price
            equity_curve.append({"time": int(date.timestamp()), "value": round(equity, 2)})

            buy_sig = False
            if buy_c.get('rsi_enabled') and pd.notna(row['rsi']) and row['rsi'] < buy_c.get('rsi_below', 30):
                buy_sig = True
            if buy_c.get('macd_cross_up') and i > 0:
                prev = df.iloc[i-1]
                if prev['macd'] <= prev['macd_signal'] and row['macd'] > row['macd_signal']:
                    buy_sig = True
            if buy_c.get('sma_cross_up') and i > 0:
                prev = df.iloc[i-1]
                if pd.notna(prev['sma20']) and prev['sma20'] <= prev['sma50'] and row['sma20'] > row['sma50']:
                    buy_sig = True
            if buy_c.get('bb_lower') and pd.notna(row['bb_lower']) and price < row['bb_lower']:
                buy_sig = True

            sell_sig = False
            if sell_c.get('rsi_enabled') and pd.notna(row['rsi']) and row['rsi'] > sell_c.get('rsi_above', 70):
                sell_sig = True
            if sell_c.get('macd_cross_down') and i > 0:
                prev = df.iloc[i-1]
                if prev['macd'] >= prev['macd_signal'] and row['macd'] < row['macd_signal']:
                    sell_sig = True
            if sell_c.get('sma_cross_down') and i > 0:
                prev = df.iloc[i-1]
                if pd.notna(prev['sma20']) and prev['sma20'] >= prev['sma50'] and row['sma20'] < row['sma50']:
                    sell_sig = True
            if sell_c.get('bb_upper') and pd.notna(row['bb_upper']) and price > row['bb_upper']:
                sell_sig = True

            if in_position:
                if stop_loss > 0 and price <= entry_price * (1 - stop_loss):
                    sell_sig = True
                if take_profit > 0 and price >= entry_price * (1 + take_profit):
                    sell_sig = True

            if buy_sig and not in_position:
                shares = int(capital / price)
                if shares > 0:
                    position = shares
                    capital -= position * price
                    entry_price = price
                    in_position = True
                    trades.append({"type": "BUY", "date": str(date.date()), "price": round(price, 2), "qty": position, "pl": 0})
            elif sell_sig and in_position:
                pl = position * (price - entry_price)
                capital += position * price
                trades.append({"type": "SELL", "date": str(date.date()), "price": round(price, 2), "qty": position, "pl": round(pl, 2)})
                position = 0
                in_position = False
                entry_price = 0

        # Final close
        if in_position and not df.empty:
            final_price = float(df.iloc[-1]['Close'])
            pl = position * (final_price - entry_price)
            capital += position * final_price
            trades.append({"type": "CLOSE", "date": str(df.index[-1].date()), "price": round(final_price, 2), "qty": position, "pl": round(pl, 2)})

        final_capital = round(capital, 2)
        total_return_ratio = (final_capital - req.initial_capital) / req.initial_capital
        winning = [t for t in trades if t.get('type') in ('SELL', 'CLOSE') and t.get('pl', 0) > 0]
        num_sell_trades = len([t for t in trades if t.get('type') in ('SELL', 'CLOSE')])
        win_rate = round((len(winning) / (num_sell_trades or 1)) * 100, 1)

        # Save to DB
        try:
            db_strat_id = int(sid) if sid.isdigit() else None
            save_q = text("""
                INSERT INTO backtest_results
                (user_id, strategy_id, ticker, start_date, end_date, initial_capital, final_capital, total_return, total_trades, winning_trades, losing_trades, trades, equity_curve)
                VALUES (:user, :sid, :ticker, :start, :end, :init, :final, :ret, :total, :win, :lose, :trades, :equity)
            """)
            with db.engine.connect() as conn:
                conn.execute(save_q, {
                    "user": current_user, "sid": db_strat_id, "ticker": req.ticker.upper(),
                    "start": req.start_date, "end": req.end_date,
                    "init": req.initial_capital, "final": final_capital, "ret": total_return_ratio,
                    "total": num_sell_trades, "win": len(winning),
                    "lose": num_sell_trades - len(winning),
                    "trades": json.dumps(trades), "equity": json.dumps(equity_curve)
                })
                conn.commit()
        except Exception as db_err:
            print(f"DB save failed (non-fatal): {db_err}")

        result = {
            "summary": {
                "strategy_name": strategy['name'],
                "ticker": req.ticker.upper(),
                "initial_capital": req.initial_capital,
                "final_value": final_capital,
                "total_return": round(total_return_ratio * 100, 2),
                "total_trades": num_sell_trades,
                "win_rate": win_rate
            },
            "trades": trades,
            "equity_curve": equity_curve
        }
        strategy_params = {
            "buy_conditions": buy_c,
            "sell_conditions": sell_c,
            **(params or {})
        }
        return attach_report_context(result, req, sid, strategy_params, portfolio=False)
    except HTTPException: raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backtest/history", tags=["backtest"])
def get_backtest_history(current_user: str = Depends(get_current_user)):
    try:
        q = text("""
            SELECT id, ticker, start_date, end_date, initial_capital, final_capital as final_value, 
                   (total_return * 100) as total_return, total_trades, winning_trades, 
                   trades, equity_curve, created_at
            FROM backtest_results WHERE user_id = :user ORDER BY created_at DESC LIMIT 20
        """)
        with db.engine.connect() as conn:
            rows = conn.execute(q, {"user": current_user}).fetchall()
        
        history = []
        for r in rows:
            d = dict(r._mapping)
            if isinstance(d.get('trades'), str): d['trades'] = json.loads(d['trades'])
            if isinstance(d.get('equity_curve'), str): d['equity_curve'] = json.loads(d['equity_curve'])
            # Win rate calculation for history
            d['win_rate'] = round((d['winning_trades'] / (d['total_trades'] or 1)) * 100, 1)
            history.append(d)
        return {"history": history}
    except Exception as e:
        print(f"History load error: {e}")
        return {"history": []}
