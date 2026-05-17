#!/usr/bin/env python3
"""
Data Pipeline Entry Point
抓取 Yahoo Finance 股票数据写入 Neon DB (PostgreSQL)

Cloud Run Job 每次运行此脚本一次，执行完毕即退出。
"""
import yfinance as yf
import os
import re
import sys
from dotenv import load_dotenv
from sqlalchemy import text

# 加载根目录下的 .env
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
load_dotenv(os.path.join(project_root, ".env"))

# 将项目根目录加入 sys.path
if project_root not in sys.path:
    sys.path.append(project_root)

from internal.db_client.database import StockDB

DEFAULT_TARGETS = [
    symbol.strip().upper()
    for symbol in os.getenv(
        "MARKET_DATA_REFRESH_SYMBOLS",
        "QQQ,VOO,SPY,^VIX,TSLA,NVDA,AAPL,MSFT,AMZN,META,GOOGL",
    ).split(",")
    if symbol.strip()
]

def normalize_symbol(value: str):
    symbol = (value or "").strip().upper()
    if not re.fullmatch(r"\^?[A-Z][A-Z0-9.-]{0,14}", symbol):
        return None
    return symbol

def unique_symbols(symbols):
    out = []
    seen = set()
    for raw in symbols:
        symbol = normalize_symbol(raw)
        if symbol and symbol not in seen:
            out.append(symbol)
            seen.add(symbol)
    return out

def load_watchlist_symbols(db: StockDB):
    query = text("""
        SELECT DISTINCT ticker
        FROM user_watchlists
        WHERE ticker IS NOT NULL AND ticker <> ''
        ORDER BY ticker ASC
    """)
    try:
        with db.engine.connect() as conn:
            rows = conn.execute(query).fetchall()
        return unique_symbols(row[0] for row in rows)
    except Exception as e:
        print(f"⚠️ 无法读取 user_watchlists，将只刷新默认列表: {e}")
        return []

def load_refresh_symbols(db: StockDB):
    watchlist_symbols = load_watchlist_symbols(db)
    symbols = unique_symbols([*DEFAULT_TARGETS, *watchlist_symbols])
    print(f"📋 默认标的: {', '.join(DEFAULT_TARGETS) if DEFAULT_TARGETS else '-'}")
    print(f"📋 Watchlist 标的: {', '.join(watchlist_symbols) if watchlist_symbols else '-'}")
    return symbols

def fetch_and_update_to_db(symbols: list, db: StockDB = None):
    """
    抓取 Yahoo Finance 5分钟 K 线数据并写入数据库 (Neon DB / SQLite)。
    """
    db = db or StockDB()
    db_type = "Neon PostgreSQL" if "neon.tech" in db.db_url else "Local SQLite"
    print(f"📦 数据库类型: {db_type}")

    def fmt_ts(value):
        return value.isoformat(sep=" ") if value is not None else "无缓存记录"

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            table_1d = f"{symbol}_1d"
            table_5m = f"{symbol}_5m"
            latest_1d_df = db.get_stock_data(table_1d, limit=1, columns=["Close"])
            latest_5m_df = db.get_stock_data(table_5m, limit=1, columns=["Close"])
            latest_1d = pd.to_datetime(latest_1d_df.index[-1]).tz_localize(None) if not latest_1d_df.empty else None
            latest_5m = pd.to_datetime(latest_5m_df.index[-1]).tz_localize(None) if not latest_5m_df.empty else None
            print(f"🔎 {symbol}_1d: DB 最新 timestamp = {fmt_ts(latest_1d)}")
            print(f"🔎 {symbol}_5m: DB 最新 timestamp = {fmt_ts(latest_5m)}")
            
            # 1. Fetch Daily Data (1d) incrementally after initial history load
            if latest_1d is not None:
                start_1d = (latest_1d - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
                print(f"📡 {symbol}_1d: 从 Yahoo Finance 增量抓取，request start={start_1d}, latest_db={fmt_ts(latest_1d)}")
                daily_data = ticker.history(start=start_1d, interval="1d")
            else:
                print(f"📡 {symbol}_1d: DB 无历史数据，初始化抓取 period=30y")
                daily_data = ticker.history(period="30y", interval="1d")
            if not daily_data.empty:
                if hasattr(daily_data.index, 'tz') and daily_data.index.tz is not None:
                    daily_data.index = daily_data.index.tz_convert('UTC').tz_localize(None)
                else:
                    daily_data.index = pd.to_datetime(daily_data.index).tz_localize(None)
                fetched_1d_start = daily_data.index.min()
                fetched_1d_end = daily_data.index.max()
                fetched_1d_count = len(daily_data)
                if latest_1d is not None:
                    daily_data = daily_data[daily_data.index > latest_1d]
                print(
                    f"🧮 {symbol}_1d: Yahoo 返回 {fetched_1d_count} 条 "
                    f"({fmt_ts(fetched_1d_start)} -> {fmt_ts(fetched_1d_end)}), "
                    f"过滤后新增 {len(daily_data)} 条"
                )
                if not daily_data.empty:
                    db.save_stock_data(daily_data, table_1d)
                    print(f"✅ {symbol}_1d: {len(daily_data)} 条数据已写入")
                else:
                    print(f"ℹ️ {symbol}_1d: 无新增数据，跳过 DB 写入")
            else:
                print(f"ℹ️ {symbol}_1d: Yahoo 未返回新数据")
            
            # 2. Fetch Intraday Data (5m) incrementally after initial recent load
            if latest_5m is not None:
                start_5m = (latest_5m - pd.Timedelta(minutes=5)).strftime("%Y-%m-%d")
                print(f"📡 {symbol}_5m: 从 Yahoo Finance 增量抓取，request start={start_5m}, latest_db={fmt_ts(latest_5m)}")
                intraday_data = ticker.history(start=start_5m, interval="5m")
            else:
                print(f"📡 {symbol}_5m: DB 无历史数据，初始化抓取 period=30d")
                intraday_data = ticker.history(period="30d", interval="5m")
            if not intraday_data.empty:
                if hasattr(intraday_data.index, 'tz') and intraday_data.index.tz is not None:
                    intraday_data.index = intraday_data.index.tz_convert('UTC').tz_localize(None)
                else:
                    intraday_data.index = pd.to_datetime(intraday_data.index).tz_localize(None)
                fetched_5m_start = intraday_data.index.min()
                fetched_5m_end = intraday_data.index.max()
                fetched_5m_count = len(intraday_data)
                if latest_5m is not None:
                    intraday_data = intraday_data[intraday_data.index > latest_5m]
                print(
                    f"🧮 {symbol}_5m: Yahoo 返回 {fetched_5m_count} 条 "
                    f"({fmt_ts(fetched_5m_start)} -> {fmt_ts(fetched_5m_end)}), "
                    f"过滤后新增 {len(intraday_data)} 条"
                )
                if not intraday_data.empty:
                    db.save_stock_data(intraday_data, table_5m)
                    print(f"✅ {symbol}_5m: {len(intraday_data)} 条数据已写入")
                else:
                    print(f"ℹ️ {symbol}_5m: 无新增数据，跳过 DB 写入")
            else:
                print(f"ℹ️ {symbol}_5m: Yahoo 未返回新数据")

        except Exception as e:
            print(f"❌ 处理 {symbol} 时出错: {e}")

if __name__ == "__main__":
    print("🚀 BRStock Data Pipeline 启动...")
    db = StockDB()
    targets = load_refresh_symbols(db)
    print(f"   目标标的: {', '.join(targets)}")
    fetch_and_update_to_db(targets, db=db)
    print("✨ 数据抓取任务完成。")
