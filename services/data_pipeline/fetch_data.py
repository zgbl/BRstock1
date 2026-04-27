#!/usr/bin/env python3
"""
Data Pipeline Entry Point
抓取 Yahoo Finance 股票数据写入 Neon DB (PostgreSQL)

Cloud Run Job 每次运行此脚本一次，执行完毕即退出。
"""
import yfinance as yf
import os
import sys
from dotenv import load_dotenv

# 加载根目录下的 .env
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
load_dotenv(os.path.join(project_root, ".env"))

# 将项目根目录加入 sys.path
if project_root not in sys.path:
    sys.path.append(project_root)

from internal.db_client.database import StockDB

# ── 配置要抓取的标的 ──────────────────────────────────────────
TARGETS = [
    "QQQ",   # NASDAQ ETF
    "VOO",   # S&P 500 ETF
    "TSLA",  # Tesla
    "NVDA",  # NVIDIA
    "AAPL",  # Apple
    "MSFT",  # Microsoft
    "AMZN",  # Amazon
    "META",  # Meta
    "GOOGL", # Google
]

def fetch_and_update_to_db(symbols: list):
    """
    抓取 Yahoo Finance 5分钟 K 线数据并写入数据库 (Neon DB / SQLite)。
    """
    db = StockDB()
    db_type = "Neon PostgreSQL" if "neon.tech" in db.db_url else "Local SQLite"
    print(f"📦 数据库类型: {db_type}")

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            
            # 1. Fetch Daily Data (1d) - at least 30 years
            print(f"📡 正在从 Yahoo Finance 获取 {symbol} 的 1d 数据 (30年)...")
            daily_data = ticker.history(period="30y", interval="1d")
            if not daily_data.empty:
                if hasattr(daily_data.index, 'tz') and daily_data.index.tz is not None:
                    daily_data.index = daily_data.index.tz_convert('UTC').tz_localize(None)
                db.save_stock_data(daily_data, f"{symbol}_1d")
                print(f"✅ {symbol}_1d: {len(daily_data)} 条数据已写入")
            
            # 2. Fetch Intraday Data (5m) - last 30 days
            print(f"📡 正在从 Yahoo Finance 获取 {symbol} 的 5m 数据 (30天)...")
            intraday_data = ticker.history(period="30d", interval="5m")
            if not intraday_data.empty:
                if hasattr(intraday_data.index, 'tz') and intraday_data.index.tz is not None:
                    intraday_data.index = intraday_data.index.tz_convert('UTC').tz_localize(None)
                db.save_stock_data(intraday_data, f"{symbol}_5m")
                print(f"✅ {symbol}_5m: {len(intraday_data)} 条数据已写入")

        except Exception as e:
            print(f"❌ 处理 {symbol} 时出错: {e}")

if __name__ == "__main__":
    print("🚀 BRStock Data Pipeline 启动...")
    print(f"   目标标的: {', '.join(TARGETS)}")
    fetch_and_update_to_db(TARGETS)
    print("✨ 数据抓取任务完成。")
