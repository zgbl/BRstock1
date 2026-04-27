#!/usr/bin/env python3
"""
populate_stocks.py
本地运行脚本：
  - 第一步：从 NASDAQ Screener HTTP API 获取全部美股代号列表
  - 第二步（可选）：用 yfinance 获取 sector/industry/market_cap 等字段
  - 将结果写入 Neon DB 的 stocks 表

运行方式：
    python services/data_pipeline/populate_stocks.py
    python services/data_pipeline/populate_stocks.py --enrich  (开启 yfinance 数据填充，较慢)
"""

import os
import sys
import requests
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ── 加载环境变量 ───────────────────────────────────────────────
load_dotenv()
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_Qc0yJfgdbxO5@ep-proud-snow-aj4t7adu-pooler.c-3.us-east-2.aws.neon.tech/neondb?sslmode=require"
)

# ── 数据源说明 ─────────────────────────────────────────────────
# yfinance 只能根据已知代号查询数据，无法列出"全部美股"。
# 所以第一步用 NASDAQ Screener HTTP API 获取代号列表（官方免费，无需注册）。
# 第二步可选地用 yfinance 来填充 sector / industry / market_cap 等字段。

NASDAQ_SCREENER_URL = (
    "https://api.nasdaq.com/api/screener/stocks"
    "?tableonly=true&limit=10000&exchange={exchange}&download=true"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Accept": "application/json",
}

def fetch_exchange(exchange: str) -> pd.DataFrame:
    """从 NASDAQ Screener 获取指定交易所的全部股票代号"""
    url = NASDAQ_SCREENER_URL.format(exchange=exchange)
    print(f"   📡 正在获取 {exchange}...")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    rows = resp.json().get("data", {}).get("rows", [])
    if not rows:
        print(f"   ⚠️  {exchange}: 无数据返回")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # NASDAQ Screener 返回的字段：symbol, name, lastsale, netchange, pctchange, marketCap, country, ipo, sector, industry, volume
    result = pd.DataFrame({
        "ticker":    df["symbol"].str.strip(),
        "name":      df["name"].str.strip(),
        "exchange":  exchange,
        "sector":    df.get("sector",   pd.Series([""] * len(df))).fillna(""),
        "industry":  df.get("industry", pd.Series([""] * len(df))).fillna(""),
        "is_etf":    False,  # Screener 不区分 ETF，ETF 代号通常不在此列表里
        "is_active": True,
    })
    print(f"   ✅ {exchange}: {len(result)} 支")
    return result

def fetch_all_us_stocks() -> pd.DataFrame:
    """获取 NASDAQ / NYSE / AMEX 全部上市标的"""
    print("📡 正在从 NASDAQ 官方 Screener API 下载美股代号列表...")
    frames = []
    for exchange in ["NASDAQ", "NYSE", "AMEX"]:
        try:
            df = fetch_exchange(exchange)
            if not df.empty:
                frames.append(df)
        except Exception as e:
            print(f"   ❌ {exchange} 失败: {e}")

    if not frames:
        raise RuntimeError("所有交易所数据源均失败，请检查网络连接")

    combined = pd.concat(frames, ignore_index=True)
    # 过滤掉含特殊字符的测试性代号（如 $, ^, . 等）
    combined = combined[~combined["ticker"].str.contains(r"[$\^\.~%]", regex=True, na=False)]
    combined = combined.drop_duplicates(subset=["ticker"], keep="first")
    return combined

def enrich_with_yfinance(df: pd.DataFrame, sample_size: int = None) -> pd.DataFrame:
    """
    用 yfinance 填充 sector / industry / market_cap_category。
    注意：这一步非常慢（约每秒 1-2 支），仅在 --enrich 模式下运行。
    yfinance 的作用：拿着已知代号去查详细信息（而不是用来"列出"所有代号）。
    """
    import yfinance as yf

    tickers = df["ticker"].tolist()
    if sample_size:
        tickers = tickers[:sample_size]
        print(f"ℹ️  Enrich 模式（样本 {sample_size} 支）")
    else:
        print(f"ℹ️  Enrich 模式（全量 {len(tickers)} 支，预计耗时 {len(tickers)//2} 秒）")

    enriched = []
    for i, ticker in enumerate(tickers):
        try:
            info = yf.Ticker(ticker).fast_info
            mc = getattr(info, "market_cap", None)
            if mc:
                if mc > 200e9:   cat = "Large"
                elif mc > 10e9:  cat = "Mid"
                elif mc > 2e9:   cat = "Small"
                elif mc > 300e6: cat = "Micro"
                else:            cat = "Nano"
            else:
                cat = None
            enriched.append({"ticker": ticker, "market_cap_category": cat})
        except Exception:
            enriched.append({"ticker": ticker, "market_cap_category": None})

        if (i + 1) % 50 == 0:
            print(f"   Enrich 进度: {i+1}/{len(tickers)}", end="\r")

    enrich_df = pd.DataFrame(enriched)
    df = df.merge(enrich_df, on="ticker", how="left")
    return df

def create_stocks_table(engine):
    """如果 stocks 表不存在则创建"""
    ddl = """
    CREATE TABLE IF NOT EXISTS stocks (
        ticker              VARCHAR(10)  PRIMARY KEY,
        name                VARCHAR(255),
        exchange            VARCHAR(30),
        sector              VARCHAR(100),
        industry            VARCHAR(150),
        market_cap_category VARCHAR(20),
        is_etf              BOOLEAN      DEFAULT FALSE,
        is_active           BOOLEAN      DEFAULT TRUE,
        country             VARCHAR(10)  DEFAULT 'US',
        created_at          TIMESTAMPTZ  DEFAULT NOW(),
        updated_at          TIMESTAMPTZ  DEFAULT NOW()
    );
    """
    with engine.connect() as conn:
        conn.execute(text(ddl))
        conn.commit()
    print("✅ stocks 表已确认存在。")

def upsert_stocks(engine, df: pd.DataFrame):
    """批量 upsert：存在则更新，不存在则插入"""
    # 确保必要列存在
    for col in ["sector", "industry", "market_cap_category"]:
        if col not in df.columns:
            df[col] = None

    records = df[[
        "ticker", "name", "exchange", "sector", "industry",
        "market_cap_category", "is_etf", "is_active"
    ]].where(pd.notna(df), other=None).to_dict(orient="records")

    total = len(records)
    upsert_sql = text("""
        INSERT INTO stocks (ticker, name, exchange, sector, industry, market_cap_category, is_etf, is_active)
        VALUES (:ticker, :name, :exchange, :sector, :industry, :market_cap_category, :is_etf, :is_active)
        ON CONFLICT (ticker) DO UPDATE SET
            name                = EXCLUDED.name,
            exchange            = EXCLUDED.exchange,
            sector              = COALESCE(EXCLUDED.sector, stocks.sector),
            industry            = COALESCE(EXCLUDED.industry, stocks.industry),
            market_cap_category = COALESCE(EXCLUDED.market_cap_category, stocks.market_cap_category),
            is_etf              = EXCLUDED.is_etf,
            updated_at          = NOW();
    """)

    BATCH = 500
    with engine.connect() as conn:
        for i in range(0, total, BATCH):
            batch = records[i:i+BATCH]
            conn.execute(upsert_sql, batch)
            conn.commit()
            done = min(i + BATCH, total)
            print(f"   写入进度: {done}/{total}", end="\r")
    print()

def main():
    enrich_mode = "--enrich" in sys.argv

    print("🚀 开始填充 stocks 表（美股全代号）")
    print(f"   模式: {'基础代号 + yfinance enrich' if enrich_mode else '仅基础代号（快速模式）'}")

    try:
        engine = create_engine(DATABASE_URL)
        # 测试连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("🔗 数据库连接成功。")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        sys.exit(1)

    create_stocks_table(engine)

    try:
        df_all = fetch_all_us_stocks()
    except Exception as e:
        print(f"❌ 下载数据失败: {e}")
        sys.exit(1)

    print(f"\n📊 共计 {len(df_all)} 支股票待写入（NASDAQ + NYSE + AMEX）")

    if enrich_mode:
        df_all = enrich_with_yfinance(df_all)

    upsert_stocks(engine, df_all)

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM stocks")).scalar()

    print(f"\n✨ 完成！stocks 表现在共有 {count:,} 条记录。")
    print("   下一步：运行 fetch_data.py 来抓取你关注的股票的行情数据。")

if __name__ == "__main__":
    main()
