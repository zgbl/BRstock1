from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
import json
import html
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np
import requests
from sqlalchemy import text
from pydantic import BaseModel
from config import db, GEMINI_API_KEY, LOCAL_AI_URL, OPENROUTER_API_KEY, OPENROUTER_MODEL, get_schwab_provider
from dependencies import get_current_user

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

NEWS_CACHE = {"ts": 0, "items": []}
NEWS_CACHE_TTL_SECONDS = 15 * 60
MARKET_TZ = ZoneInfo("America/New_York")
DEFAULT_REFRESH_SYMBOLS = [
    symbol.strip().upper()
    for symbol in os.getenv(
        "MARKET_DATA_REFRESH_SYMBOLS",
        "QQQ,VOO,SPY,^VIX,TSLA,NVDA,AAPL,MSFT,AMZN,META,GOOGL",
    ).split(",")
    if symbol.strip()
]

def _normalize_market_symbol(value: str):
    symbol = (value or "").strip().upper()
    if not re.fullmatch(r"\^?[A-Z][A-Z0-9.-]{0,14}", symbol):
        return None
    return symbol

def _unique_market_symbols(symbols):
    out = []
    seen = set()
    for raw in symbols:
        symbol = _normalize_market_symbol(raw)
        if symbol and symbol not in seen:
            out.append(symbol)
            seen.add(symbol)
    return out

def get_dynamic_refresh_symbols():
    try:
        with db.engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT DISTINCT ticker
                FROM user_watchlists
                WHERE ticker IS NOT NULL AND ticker <> ''
                ORDER BY ticker ASC
            """)).fetchall()
        watchlist_symbols = [row[0] for row in rows]
    except Exception as e:
        print(f"Unable to read watchlist symbols for refresh: {e}")
        watchlist_symbols = []
    return _unique_market_symbols([*DEFAULT_REFRESH_SYMBOLS, *watchlist_symbols])

NEWS_FEEDS = [
    {"source": "CNBC", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
    {"source": "CNBC Business", "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html"},
    {"source": "CNBC Economy", "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html"},
    {"source": "CNBC Earnings", "url": "https://www.cnbc.com/id/15839135/device/rss/rss.html"},
    {"source": "Yahoo Finance", "url": "https://finance.yahoo.com/news/rssindex"},
]

TICKER_NAME_KEYWORDS = {
    "AAPL": ["AAPL", "APPLE"],
    "MSFT": ["MSFT", "MICROSOFT"],
    "AMZN": ["AMZN", "AMAZON"],
    "GOOGL": ["GOOGL", "GOOGLE", "ALPHABET"],
    "META": ["META", "FACEBOOK"],
    "NVDA": ["NVDA", "NVIDIA"],
    "TSLA": ["TSLA", "TESLA"],
    "QQQ": ["QQQ", "NASDAQ", "NAS100"],
    "VOO": ["VOO", "S&P 500", "SP 500", "S&P"],
    "SPY": ["SPY", "S&P 500", "SP 500", "S&P"],
}

POSITIVE_NEWS_WORDS = {
    "gain", "gains", "jump", "jumps", "rise", "rises", "rally", "surge", "surges",
    "beat", "beats", "upgrade", "upgrades", "record", "optimism", "growth", "strong"
}
NEGATIVE_NEWS_WORDS = {
    "fall", "falls", "drop", "drops", "slump", "slumps", "plunge", "plunges",
    "miss", "misses", "downgrade", "downgrades", "cuts", "risk", "warning", "weak",
    "tariff", "lawsuit", "probe", "inflation", "recession"
}

class WatchlistOrderRequest(BaseModel):
    tickers: List[str]

def _strip_html(value: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", value or "")
    return html.unescape(re.sub(r"\s+", " ", cleaned)).strip()

def _parse_rss_datetime(value: str):
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None

def _classify_news_tag(text_value: str) -> str:
    upper = text_value.upper()
    if any(k in upper for k in ["EARNINGS", "REVENUE", "PROFIT", "EPS"]):
        return "EARNINGS"
    if any(k in upper for k in ["FED", "RATE", "INFLATION", "JOBS", "GDP", "ECONOMY"]):
        return "MACRO"
    if any(k in upper for k in ["AI", "CHIP", "SEMICONDUCTOR", "TECH", "SOFTWARE"]):
        return "TECH"
    if any(k in upper for k in ["OIL", "ENERGY", "CRUDE"]):
        return "ENERGY"
    if any(k in upper for k in ["MARKET", "STOCK", "NASDAQ", "S&P", "DOW"]):
        return "MARKET"
    return "BUSINESS"

def _classify_sentiment(text_value: str) -> str:
    words = set(re.findall(r"[A-Za-z]+", text_value.lower()))
    pos = len(words & POSITIVE_NEWS_WORDS)
    neg = len(words & NEGATIVE_NEWS_WORDS)
    if pos > neg:
        return "bullish"
    if neg > pos:
        return "bearish"
    return "neutral"

def _match_ticker(text_value: str, preferred_tickers: List[str]) -> str:
    upper = text_value.upper()
    candidates = preferred_tickers or list(TICKER_NAME_KEYWORDS.keys())
    for ticker in candidates:
        ticker_upper = ticker.upper()
        keywords = TICKER_NAME_KEYWORDS.get(ticker_upper, [ticker_upper])
        if any(keyword in upper for keyword in keywords):
            return ticker_upper
    return "MARKET"

def _time_ago(published_at):
    if not published_at:
        return "recent"
    delta = datetime.now(timezone.utc) - published_at
    minutes = max(int(delta.total_seconds() // 60), 0)
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 48:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"

def _fetch_rss_items():
    now = time.time()
    if NEWS_CACHE["items"] and now - NEWS_CACHE["ts"] < NEWS_CACHE_TTL_SECONDS:
        return NEWS_CACHE["items"]

    items = []
    headers = {"User-Agent": "BRStockAI/1.0 (+https://localhost)"}
    for feed in NEWS_FEEDS:
        try:
            resp = requests.get(feed["url"], headers=headers, timeout=8)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item"):
                title = _strip_html(item.findtext("title"))
                link = _strip_html(item.findtext("link"))
                description = _strip_html(item.findtext("description"))
                published_at = _parse_rss_datetime(item.findtext("pubDate") or item.findtext("published"))
                if not title or not link:
                    continue
                text_value = f"{title} {description}"
                items.append({
                    "title": title,
                    "summary": description,
                    "url": link,
                    "source": feed["source"],
                    "published_at": published_at.isoformat() if published_at else None,
                    "published_ts": published_at.timestamp() if published_at else 0,
                    "tag": _classify_news_tag(text_value),
                    "sentiment": _classify_sentiment(text_value),
                })
        except Exception as e:
            print(f"News feed failed ({feed['source']}): {e}")

    deduped = {}
    for item in items:
        deduped[item["url"]] = item
    out = sorted(deduped.values(), key=lambda x: x.get("published_ts", 0), reverse=True)
    NEWS_CACHE["ts"] = now
    NEWS_CACHE["items"] = out
    return out

def _as_price_frame(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if raw.empty:
        return raw
    if isinstance(raw.columns, pd.MultiIndex):
        symbol = ticker.upper()
        for level in range(raw.columns.nlevels):
            values = [str(v).upper() for v in raw.columns.get_level_values(level)]
            if symbol in values:
                return raw.xs(raw.columns.get_level_values(level)[values.index(symbol)], axis=1, level=level)
        out = raw.copy()
        out.columns = raw.columns.get_level_values(-1)
        return out
    return raw

def _latest_price_snapshot(ticker: str):
    try:
        import yfinance as yf
        raw = yf.download(ticker, period="9mo", interval="1d", progress=False, auto_adjust=False, threads=False)
        df = _as_price_frame(raw, ticker).dropna(how="all")
        if df.empty or "Close" not in df.columns:
            table_name = f"{ticker.lower()}_1d"
            df = db.get_stock_data(table_name, limit=220)
        if df.empty or "Close" not in df.columns:
            return None

        close = df["Close"].astype(float).dropna()
        if len(close) < 2:
            return None
        latest = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        change = latest - prev
        change_pct = (change / prev * 100) if prev else 0

        delta = close.diff()
        gain = delta.clip(lower=0).ewm(com=13, min_periods=14).mean()
        loss = (-delta.clip(upper=0)).ewm(com=13, min_periods=14).mean()
        rs = gain / loss.replace(0, float("nan"))
        rsi = float((100 - 100 / (1 + rs)).iloc[-1]) if len(close) >= 15 else None

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = float((macd_line - signal_line).iloc[-1])

        sma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else None
        sma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
        latest_idx = close.index[-1]
        latest_date = latest_idx.date().isoformat() if hasattr(latest_idx, "date") else str(latest_idx)[:10]

        score = 50
        if change_pct > 0:
            score += 8
        elif change_pct < 0:
            score -= 8
        if rsi is not None:
            if 45 <= rsi <= 65:
                score += 8
            elif rsi >= 75:
                score -= 10
            elif rsi <= 30:
                score -= 6
        if sma20 and latest > sma20:
            score += 8
        elif sma20 and latest < sma20:
            score -= 8
        if sma50 and latest > sma50:
            score += 6
        elif sma50 and latest < sma50:
            score -= 6
        if macd_hist > 0:
            score += 8
        elif macd_hist < 0:
            score -= 8
        score = max(5, min(95, round(score)))
        action = "BUY" if score >= 65 else ("SELL" if score <= 35 else "HOLD")

        return {
            "ticker": ticker.upper(),
            "price": round(latest, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "rsi": round(rsi, 1) if rsi is not None and np.isfinite(rsi) else None,
            "sma20": round(sma20, 2) if sma20 and np.isfinite(sma20) else None,
            "sma50": round(sma50, 2) if sma50 and np.isfinite(sma50) else None,
            "macd_hist": round(macd_hist, 4) if np.isfinite(macd_hist) else None,
            "score": score,
            "signal": action,
            "as_of": latest_date,
        }
    except Exception as e:
        print(f"Quote snapshot failed ({ticker}): {e}")
        return None

def _is_us_regular_market_open(now=None):
    current = now or datetime.now(MARKET_TZ)
    if current.tzinfo is None:
        current = current.replace(tzinfo=MARKET_TZ)
    else:
        current = current.astimezone(MARKET_TZ)
    if current.weekday() >= 5:
        return False
    market_open = current.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = current.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= current <= market_close

def _epoch_ms_to_iso(value):
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None

def _schwab_summary(symbol: str):
    try:
        payload = get_schwab_provider().get_quote(symbol)
        item = payload.get(symbol.upper()) or next(iter(payload.values()), None)
        if not item:
            return None
        quote = item.get("quote") or {}
        regular = item.get("regular") or {}
        reference = item.get("reference") or {}
        price = quote.get("lastPrice") or quote.get("mark") or regular.get("regularMarketLastPrice")
        previous_close = quote.get("closePrice")
        if price is None:
            return None
        change = quote.get("netChange")
        change_pct = quote.get("netPercentChange")
        if change is None and previous_close:
            change = float(price) - float(previous_close)
        if change_pct is None and previous_close:
            change_pct = (float(change or 0) / float(previous_close)) * 100
        return {
            "symbol": symbol.upper(),
            "name": reference.get("description") or symbol.upper(),
            "price": round(float(price), 2),
            "open": round(float(quote.get("openPrice") or 0), 2),
            "previous_close": round(float(previous_close or 0), 2),
            "high": round(float(quote.get("highPrice") or 0), 2),
            "low": round(float(quote.get("lowPrice") or 0), 2),
            "volume": int(quote.get("totalVolume") or 0),
            "change": round(float(change or 0), 2),
            "change_pct": round(float(change_pct or 0), 2),
            "provider": "schwab",
            "realtime": bool(item.get("realtime")),
            "as_of": _epoch_ms_to_iso(
                quote.get("quoteTime")
                or quote.get("quoteTimeInLong")
                or quote.get("tradeTime")
                or quote.get("tradeTimeInLong")
                or regular.get("regularMarketTradeTime")
                or regular.get("regularMarketTradeTimeInLong")
            ),
        }
    except Exception as e:
        print(f"Schwab summary failed ({symbol}): {e}")
        return None

def _build_rule_brief(snapshots, news_items):
    if not snapshots:
        return {
            "market_overview": "Market data is not available for the selected watchlist yet.",
            "technical_analysis": "Add or refresh ticker data to generate a technical brief.",
            "news_sentiment": "News feed is available, but no watchlist-aware market summary could be produced.",
            "risk_assessment": "Risk level cannot be estimated without current market data.",
            "risk_level": "Unknown",
            "risk_score": 50,
        }

    leaders = sorted(snapshots, key=lambda x: x["change_pct"], reverse=True)
    winners = [s for s in snapshots if s["change_pct"] > 0]
    losers = [s for s in snapshots if s["change_pct"] < 0]
    avg_change = sum(s["change_pct"] for s in snapshots) / len(snapshots)
    high_rsi = [s for s in snapshots if s.get("rsi") is not None and s["rsi"] >= 70]
    low_rsi = [s for s in snapshots if s.get("rsi") is not None and s["rsi"] <= 35]
    bullish_news = [n for n in news_items if n.get("sentiment") == "bullish"]
    bearish_news = [n for n in news_items if n.get("sentiment") == "bearish"]

    top = leaders[0]
    weak = leaders[-1]
    market_overview = (
        f"Watchlist average move is {avg_change:+.2f}% based on the latest available daily market data. "
        f"{top['ticker']} leads at {top['change_pct']:+.2f}% (${top['price']}); "
        f"{weak['ticker']} is weakest at {weak['change_pct']:+.2f}% (${weak['price']}). "
        f"{len(winners)} of {len(snapshots)} tracked names are positive."
    )

    technical_lines = []
    for s in snapshots[:6]:
        trend = "above" if s.get("sma20") and s["price"] >= s["sma20"] else "below"
        rsi_text = f"RSI {s['rsi']}" if s.get("rsi") is not None else "RSI n/a"
        technical_lines.append(
            f"{s['ticker']}: {s['signal']} score {s['score']}%, {rsi_text}, price {trend} SMA20"
        )
    technical_analysis = " ".join(technical_lines)

    news_sentiment = (
        f"Today's real news feed shows {len(bullish_news)} bullish, {len(bearish_news)} bearish, "
        f"and {max(len(news_items) - len(bullish_news) - len(bearish_news), 0)} neutral items in the current sample. "
    )
    if news_items:
        news_sentiment += f"Latest headline: {news_items[0]['title']}"

    risk_score = 35
    risk_score += len(losers) * 5
    risk_score += len(high_rsi) * 6
    risk_score += len(low_rsi) * 4
    risk_score += len(bearish_news) * 3
    risk_score = max(10, min(90, risk_score))
    risk_level = "High" if risk_score >= 65 else ("Low" if risk_score <= 35 else "Medium")
    risk_assessment = (
        f"Portfolio risk is {risk_level.lower()}. Watch elevated signals from "
        f"{', '.join(s['ticker'] for s in high_rsi[:3]) or 'no major overbought names'} and weakness in "
        f"{', '.join(s['ticker'] for s in losers[:3]) or 'no major decliners'}. "
        "Use position sizing and confirm data freshness before acting."
    )

    return {
        "market_overview": market_overview,
        "technical_analysis": technical_analysis,
        "news_sentiment": news_sentiment,
        "risk_assessment": risk_assessment,
        "risk_level": risk_level,
        "risk_score": risk_score,
    }

# ── Watchlist ─────────────────────────────────────────────────
@router.get("/watchlist")
def get_watchlist(current_user: str = Depends(get_current_user)):
    query = text("""
        SELECT ticker
        FROM user_watchlists
        WHERE user_id = :user
        ORDER BY display_order ASC, added_at ASC, ticker ASC
    """)
    with db.engine.connect() as conn:
        res = conn.execute(query, {"user": current_user}).fetchall()
    return [r[0] for r in res]

@router.post("/watchlist/{ticker}")
def add_to_watchlist(ticker: str, current_user: str = Depends(get_current_user)):
    ticker = ticker.upper().strip()
    try:
        query = text("""
            INSERT INTO user_watchlists (user_id, ticker, display_order)
            VALUES (
                :user,
                :ticker,
                COALESCE((SELECT MAX(display_order) + 1 FROM user_watchlists WHERE user_id = :user), 0)
            )
        """)
        with db.engine.connect() as conn:
            conn.execute(query, {"user": current_user, "ticker": ticker})
            conn.commit()
        return {"message": f"Added {ticker} to watchlist"}
    except Exception:
        return {"message": "Ticker already in watchlist"}

@router.delete("/watchlist/{ticker}")
def remove_from_watchlist(ticker: str, current_user: str = Depends(get_current_user)):
    query = text("DELETE FROM user_watchlists WHERE user_id = :user AND ticker = :ticker")
    with db.engine.connect() as conn:
        conn.execute(query, {"user": current_user, "ticker": ticker.upper()})
        conn.commit()
    return {"message": f"Removed {ticker} from watchlist"}

@router.put("/watchlist/order")
def update_watchlist_order(req: WatchlistOrderRequest, current_user: str = Depends(get_current_user)):
    cleaned = []
    seen = set()
    for ticker in req.tickers:
        symbol = ticker.upper().strip()
        if symbol and symbol not in seen:
            cleaned.append(symbol)
            seen.add(symbol)

    with db.engine.connect() as conn:
        for idx, ticker in enumerate(cleaned):
            conn.execute(
                text("""
                    UPDATE user_watchlists
                    SET display_order = :display_order
                    WHERE user_id = :user AND ticker = :ticker
                """),
                {"display_order": idx, "user": current_user, "ticker": ticker},
            )
        conn.commit()
    return {"message": "Watchlist order updated", "tickers": cleaned}

# ── Search ────────────────────────────────────────────────────
@router.get("/search")
def search_stocks(q: str = ""):
    """Search for stocks by ticker or name using yfinance."""
    q = q.strip().upper()
    if not q or len(q) < 1:
        return []
    try:
        import yfinance as yf
        # yfinance search (available in newer versions)
        results = yf.Search(q, max_results=8)
        quotes = results.quotes if hasattr(results, 'quotes') else []
        out = []
        for item in quotes:
            ticker = item.get("symbol", "")
            name = item.get("longname") or item.get("shortname") or ticker
            if ticker:
                out.append({"ticker": ticker, "name": name})
        if out:
            return out
    except Exception as e:
        print(f"yfinance search failed: {e}")

    # Fallback: match against a curated ticker list
    COMMON_TICKERS = [
        ("AAPL", "Apple Inc."), ("MSFT", "Microsoft Corporation"), ("AMZN", "Amazon.com Inc."),
        ("GOOGL", "Alphabet Inc."), ("META", "Meta Platforms Inc."), ("NVDA", "NVIDIA Corporation"),
        ("TSLA", "Tesla Inc."), ("QQQ", "Invesco QQQ Trust"), ("VOO", "Vanguard S&P 500 ETF"),
        ("SPY", "SPDR S&P 500 ETF"), ("AMD", "Advanced Micro Devices"), ("NFLX", "Netflix Inc."),
        ("BABA", "Alibaba Group"), ("DIS", "The Walt Disney Company"), ("BRK-B", "Berkshire Hathaway"),
        ("JPM", "JPMorgan Chase"), ("BAC", "Bank of America"), ("WMT", "Walmart Inc."),
        ("JNJ", "Johnson & Johnson"), ("V", "Visa Inc."), ("MA", "Mastercard Inc."),
        ("PYPL", "PayPal Holdings"), ("INTC", "Intel Corporation"), ("CRM", "Salesforce Inc."),
        ("ORCL", "Oracle Corporation"), ("IBM", "International Business Machines"),
        ("UBER", "Uber Technologies"), ("LYFT", "Lyft Inc."), ("SNAP", "Snap Inc."),
        ("TWTR", "Twitter/X Corp"), ("HOOD", "Robinhood Markets"), ("COIN", "Coinbase Global"),
        ("GS", "Goldman Sachs"), ("MS", "Morgan Stanley"), ("C", "Citigroup Inc."),
        ("T", "AT&T Inc."), ("VZ", "Verizon Communications"), ("XOM", "ExxonMobil"),
        ("CVX", "Chevron Corporation"), ("PFE", "Pfizer Inc."), ("MRNA", "Moderna Inc."),
    ]
    matched = [
        {"ticker": t, "name": n}
        for t, n in COMMON_TICKERS
        if q in t or q in n.upper()
    ]
    return matched[:8]

# ── Market News ───────────────────────────────────────────────
@router.get("/news")
def get_market_news(tickers: str = "", limit: int = 12, today_only: bool = True):
    preferred = [
        t.strip().upper()
        for t in tickers.split(",")
        if t.strip()
    ]
    limit = max(1, min(limit, 30))
    all_items = _fetch_rss_items()
    today_utc = datetime.now(timezone.utc).date()

    def hydrate(item):
        published_at = None
        if item.get("published_at"):
            try:
                published_at = datetime.fromisoformat(item["published_at"])
            except Exception:
                published_at = None
        text_value = f"{item.get('title', '')} {item.get('summary', '')}"
        return {
            **{k: v for k, v in item.items() if k != "published_ts"},
            "ticker": _match_ticker(text_value, preferred),
            "time": _time_ago(published_at),
            "is_today": bool(published_at and published_at.date() == today_utc),
        }

    hydrated = [hydrate(item) for item in all_items]
    today_items = [item for item in hydrated if item["is_today"]]
    selected = today_items if (today_only and today_items) else hydrated
    scope = "today" if (today_only and today_items) else ("latest_fallback" if today_only else "latest")

    if preferred:
        directly_matched = [item for item in selected if item["ticker"] in preferred]
        market_items = [item for item in selected if item["ticker"] == "MARKET"]
        selected = directly_matched + market_items + [
            item for item in selected
            if item["ticker"] not in preferred and item["ticker"] != "MARKET"
        ]

    return {
        "items": selected[:limit],
        "count": len(selected[:limit]),
        "scope": scope,
        "sources": sorted({item["source"] for item in selected[:limit]}),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

@router.get("/ai-brief")
def get_ai_market_brief(tickers: str = "QQQ,VOO,TSLA", limit: int = 8):
    selected_tickers = []
    seen = set()
    for ticker in tickers.split(","):
        symbol = ticker.strip().upper()
        if symbol and symbol not in seen:
            selected_tickers.append(symbol)
            seen.add(symbol)
    if not selected_tickers:
        selected_tickers = ["QQQ", "VOO", "TSLA"]
    selected_tickers = selected_tickers[:12]

    snapshots = [
        snapshot
        for snapshot in (_latest_price_snapshot(ticker) for ticker in selected_tickers)
        if snapshot
    ]
    news_payload = get_market_news(",".join(selected_tickers), limit=limit, today_only=True)
    news_items = news_payload.get("items", [])
    brief = _build_rule_brief(snapshots, news_items)

    return {
        "tickers": selected_tickers,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_source": "Yahoo Finance daily market data + RSS financial news",
        "analysis_source": "BRStock rule engine",
        "news_scope": news_payload.get("scope"),
        "signals": snapshots,
        "brief": brief,
    }

# ── History ───────────────────────────────────────────────────
@router.get("/{symbol}/history")
def get_stock_history(symbol: str, interval: str = "1d", limit: int = 1000):
    if interval == "5m":
        table_name = f"{symbol.lower()}_5m"
        fetch_limit = limit
    else:
        table_name = f"{symbol.lower()}_1d"
        fetch_limit = 10000 if limit == 1000 else limit

    df = db.get_stock_data(table_name, limit=fetch_limit)
    if df.empty:
        return {"symbol": symbol.upper(), "count": 0, "data": []}

    if interval == "1w":
        df = df.resample('W-FRI').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    elif interval == "1m":
        df = df.resample('ME').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()

    df = df.reset_index()
    df['timestamp'] = df['timestamp'].astype(str)
    records = df[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']].to_dict(orient='records')
    return {"symbol": symbol.upper(), "interval": interval, "count": len(records), "data": records}

# ── Indicators ────────────────────────────────────────────────
@router.get("/{symbol}/indicators")
def get_stock_indicators(symbol: str, interval: str = "1d"):
    """Compute RSI, MACD, SMA, EMA history for charting."""
    if interval == "5m":
        table_name = f"{symbol.lower()}_5m"
        fetch_limit = 500
    else:
        table_name = f"{symbol.lower()}_1d"
        fetch_limit = 10000

    df = db.get_stock_data(table_name, limit=fetch_limit)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    close = df["Close"].astype(float)

    # ── RSI (14) ──────────────────────────────────────────────
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=13, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(com=13, min_periods=14).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi_series = (100 - 100 / (1 + rs)).round(2)

    # ── MACD (12/26/9) ────────────────────────────────────────
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = (ema12 - ema26).round(4)
    signal_line = macd_line.ewm(span=9, adjust=False).mean().round(4)
    histogram = (macd_line - signal_line).round(4)

    # ── Moving Averages ───────────────────────────────────────
    sma20 = close.rolling(20).mean().round(3)
    sma50 = close.rolling(50).mean().round(3)
    ema20 = close.ewm(span=20, adjust=False).mean().round(3)
    ema50 = close.ewm(span=50, adjust=False).mean().round(3)

    # Build timestamp list
    df_out = df.reset_index()
    timestamps = df_out["timestamp"].astype(str).tolist()

    def to_list(series):
        return [None if (v != v) else float(v) for v in series]

    rsi_hist = [
        {"timestamp": ts, "value": v}
        for ts, v in zip(timestamps, to_list(rsi_series))
        if v is not None
    ]
    macd_hist = [
        {"timestamp": ts, "macd": m, "signal": s, "histogram": h}
        for ts, m, s, h in zip(timestamps, to_list(macd_line), to_list(signal_line), to_list(histogram))
        if m is not None
    ]
    ma_hist = [
        {"timestamp": ts, "sma20": s20, "sma50": s50, "ema20": e20, "ema50": e50}
        for ts, s20, s50, e20, e50 in zip(timestamps, to_list(sma20), to_list(sma50), to_list(ema20), to_list(ema50))
    ]

    latest_rsi = rsi_hist[-1]["value"] if rsi_hist else None
    latest_macd = macd_hist[-1]["macd"] if macd_hist else None

    return {
        "symbol": symbol.upper(),
        "interval": interval,
        "rsi": {
            "latest": latest_rsi,
            "signal": "overbought" if latest_rsi and latest_rsi >= 70 else (
                      "oversold" if latest_rsi and latest_rsi <= 30 else "neutral"),
            "history": rsi_hist,
        },
        "macd": {
            "macd_latest": latest_macd,
            "signal": "bullish" if latest_macd and latest_macd >= 0 else "bearish",
            "history": macd_hist,
        },
        "moving_averages": {
            "sma20_latest": float(sma20.iloc[-1]) if not pd.isna(sma20.iloc[-1]) else None,
            "sma50_latest": float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else None,
            "ema20_latest": float(ema20.iloc[-1]) if not pd.isna(ema20.iloc[-1]) else None,
            "ema50_latest": float(ema50.iloc[-1]) if not pd.isna(ema50.iloc[-1]) else None,
            "history": ma_hist,
        },
    }

# ── Summary ───────────────────────────────────────────────────
@router.get("/{symbol}/summary")
def get_stock_summary(symbol: str):
    use_live_quote = _is_us_regular_market_open()
    if use_live_quote and (schwab := _schwab_summary(symbol)):
        return schwab

    table_name = f"{symbol.lower()}_5m"
    df = db.get_stock_data(table_name, limit=500)
    if df.empty:
        return {
            "symbol": symbol.upper(),
            "price": 0,
            "open": 0,
            "high": 0,
            "low": 0,
            "volume": 0,
            "change": 0,
            "change_pct": 0,
            "provider": "database",
            "as_of": None,
            "market_open": use_live_quote,
        }

    close_p = float(df.iloc[-1]['Close'])
    df.index = pd.to_datetime(df.index, utc=True)
    latest_ts = df.index.max()
    latest_date = df.index.normalize().max()
    today_df = df[df.index.normalize() == latest_date]

    day_open = float(today_df.iloc[0]['Open'])
    day_high = float(today_df['High'].max())
    day_low = float(today_df['Low'].min())
    volume = int(today_df['Volume'].sum())
    prev_df = df[df.index.normalize() < latest_date]
    prev_close = float(prev_df.iloc[-1]['Close']) if not prev_df.empty else day_open
    change = round(close_p - prev_close, 2)
    pct = round(change / (prev_close if prev_close != 0 else 1) * 100, 2)

    stock_name = symbol.upper()
    try:
        with db.engine.connect() as conn:
            res = conn.execute(text("SELECT name FROM stocks WHERE ticker = :t"), {"t": symbol.upper()}).fetchone()
            if res:
                stock_name = res[0]
    except:
        pass

    return {"symbol": symbol.upper(), "name": stock_name, "price": close_p, "open": day_open,
            "previous_close": round(prev_close, 2), "high": day_high, "low": day_low,
            "volume": volume, "change": change, "change_pct": pct, "provider": "database",
            "as_of": latest_ts.isoformat() if hasattr(latest_ts, "isoformat") else str(latest_ts),
            "market_open": use_live_quote}

def refresh_symbol_market_data(symbol: str, force: bool = False, max_age_hours: int = 72):
    symbol = symbol.upper().strip()
    table_5m = f"{symbol.lower()}_5m"
    table_1d = f"{symbol.lower()}_1d"

    cached_5m = db.get_stock_data(table_5m, limit=1)
    cached_1d = db.get_stock_data(table_1d, limit=1)
    if not force and not cached_5m.empty and not cached_1d.empty:
        latest_5m = pd.to_datetime(cached_5m.index[-1]).tz_localize(None)
        now = pd.Timestamp.now().tz_localize(None)
        age_hours = max((now - latest_5m).total_seconds() / 3600, 0)
        if age_hours <= max_age_hours:
            return {
                "message": f"Using cached data for {symbol}",
                "provider": "database",
                "cached": True,
                "latest_5m": str(latest_5m),
                "age_hours": round(age_hours, 2),
                "5m_rows": int(len(cached_5m)),
                "1d_rows": int(len(cached_1d)),
            }

    schwab_error = None
    try:
        schwab = get_schwab_provider()
        df_5m = schwab.get_price_history_frame(
            symbol,
            period_type="day",
            period=10,
            frequency_type="minute",
            frequency=5,
        )
        if not df_5m.empty:
            db.save_stock_data(df_5m, table_5m)

        df_1d = schwab.get_price_history_frame(
            symbol,
            period_type="year",
            period=10,
            frequency_type="daily",
            frequency=1,
        )
        if not df_1d.empty:
            db.save_stock_data(df_1d, table_1d)

        if not df_5m.empty or not df_1d.empty:
            return {
                "message": f"Fetched Schwab market data for {symbol}",
                "provider": "schwab",
                "cached": False,
                "5m_rows": len(df_5m),
                "1d_rows": len(df_1d),
            }
    except Exception as e:
        schwab_error = str(e)

    import yfinance as yf
    ticker = yf.Ticker(symbol)

    df_5m = ticker.history(period="60d", interval="5m")
    if not df_5m.empty:
        df_5m.index.name = 'timestamp'
        db.save_stock_data(df_5m, table_5m)

    df_1d = ticker.history(period="max", interval="1d")
    if not df_1d.empty:
        df_1d.index.name = 'timestamp'
        db.save_stock_data(df_1d, table_1d)

    return {
        "message": f"Fetched data for {symbol}",
        "provider": "yfinance",
        "schwab_error": schwab_error,
        "cached": False,
        "5m_rows": len(df_5m),
        "1d_rows": len(df_1d),
    }

def refresh_market_data_batch(symbols=None, force: bool = True):
    selected = _unique_market_symbols(symbols) if symbols else get_dynamic_refresh_symbols()
    results = {}
    for symbol in dict.fromkeys(selected):
        try:
            results[symbol] = refresh_symbol_market_data(symbol, force=force, max_age_hours=0)
        except Exception as e:
            results[symbol] = {"error": str(e)}
    return {
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "symbols": list(results.keys()),
        "results": results,
    }

# ── Fetch (Data Pipeline Trigger) ────────────────────────────
@router.post("/{symbol}/fetch")
def fetch_stock_data(symbol: str, force: bool = False, max_age_hours: int = 72):
    try:
        return refresh_symbol_market_data(symbol, force=force, max_age_hours=max_age_hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh-after-close")
def refresh_after_close(symbols: str = ""):
    requested = _unique_market_symbols(symbols.split(",")) if symbols else None
    return refresh_market_data_batch(requested, force=True)

# ── AI Analysis ───────────────────────────────────────────────
def _rule_based_technical_analysis(symbol, price, rsi, rsi_sig, macd, macd_sig, sma20, sma50, language="en"):
    above_sma20 = price >= sma20 if sma20 is not None else None
    above_sma50 = price >= sma50 if sma50 is not None else None

    if above_sma20 and above_sma50 and macd > 0:
        trend_en = "The primary technical bias is bullish: price is above both the 20-day and 50-day moving averages, and MACD remains positive."
        trend_zh = "主要技术倾向偏多：价格位于 20 日和 50 日均线之上，MACD 仍为正。"
    elif not above_sma20 and not above_sma50 and macd < 0:
        trend_en = "The primary technical bias is defensive: price is below both key moving averages and MACD is negative."
        trend_zh = "主要技术倾向偏防守：价格低于关键均线，MACD 为负。"
    else:
        trend_en = "The technical picture is mixed: momentum and moving-average confirmation are not fully aligned."
        trend_zh = "技术图形偏混合：动量和均线确认并不完全一致。"

    if rsi >= 75:
        rsi_en = "RSI is very elevated, so the setup may be extended even if momentum is still strong."
        rsi_zh = "RSI 已明显偏高，即使动量仍强，也要防止短线过热。"
    elif rsi >= 70:
        rsi_en = "RSI is overbought, which argues for patience on new entries or smaller position size."
        rsi_zh = "RSI 进入超买区，新开仓应更有耐心或降低仓位。"
    elif rsi <= 30:
        rsi_en = "RSI is oversold, so a rebound is possible, but confirmation from price action is still needed."
        rsi_zh = "RSI 进入超卖区，可能有反弹，但仍需要价格行为确认。"
    else:
        rsi_en = "RSI is in a workable range, so the signal depends more on trend and support/resistance behavior."
        rsi_zh = "RSI 处于可操作区间，信号更多取决于趋势和支撑阻力表现。"

    support = min(v for v in [sma20, sma50, price * 0.97] if v is not None)
    resistance = max(v for v in [price * 1.03, price + abs(price - sma20 if sma20 else 0)] if v is not None)

    if language == "zh":
        return (
            f"趋势判断：{trend_zh} 当前价格约 ${price:.2f}，RSI {rsi:.1f}（{rsi_sig}），MACD {macd:.3f}（{macd_sig}）。{rsi_zh}\n\n"
            f"关键价位：短线支撑关注 ${support:.2f} 附近；若继续上行，第一阻力可关注 ${resistance:.2f} 附近。20 日均线 ${sma20:.2f}，50 日均线 ${sma50:.2f}。\n\n"
            "策略建议：如果已有仓位，可以继续持有但收紧风险控制；如果准备新开仓，建议等待回踩支撑或 RSI 降温后再评估。若价格跌破短线支撑且 MACD 转弱，应降低仓位或暂停追高。"
        )

    return (
        f"Trend: {trend_en} Current price is about ${price:.2f}; RSI is {rsi:.1f} ({rsi_sig}) and MACD is {macd:.3f} ({macd_sig}). {rsi_en}\n\n"
        f"Key levels: near-term support is around ${support:.2f}. If the move continues, first resistance is around ${resistance:.2f}. SMA20 is ${sma20:.2f}; SMA50 is ${sma50:.2f}.\n\n"
        "Strategy view: if already long, the setup supports staying involved while tightening risk controls. For a new entry, wait for a pullback toward support or an RSI cooldown. If price loses near-term support while MACD weakens, reduce exposure instead of chasing."
    )

def _friendly_ai_status(source, provider_errors=None, language="en"):
    provider_errors = provider_errors or []
    if source and source.startswith("OpenRouter"):
        return "Live AI model connected." if language == "en" else "实时 AI 模型已连接。"
    if source == "Gemini":
        return "Live AI model connected." if language == "en" else "实时 AI 模型已连接。"
    if source == "Local AI":
        return "Private local model connected." if language == "en" else "本地私有模型已连接。"

    quota_related = any("quota" in str(item).lower() or "429" in str(item) for item in provider_errors)
    if quota_related:
        return (
            "Live model allowance is temporarily exhausted, so BRStock generated this report with its built-in technical engine."
            if language == "en" else
            "实时模型额度暂时用尽，BRStock 已使用内置技术分析引擎生成本报告。"
        )
    return (
        "Live model is temporarily unavailable, so BRStock generated this report with its built-in technical engine."
        if language == "en" else
        "实时模型暂时不可用，BRStock 已使用内置技术分析引擎生成本报告。"
    )

def _provider_unavailable_label(provider_name, exc=None, status_code=None):
    if status_code:
        return f"{provider_name} unavailable ({status_code}); using fallback."
    if exc:
        return f"{provider_name} unavailable ({type(exc).__name__}); using fallback."
    return f"{provider_name} unavailable; using fallback."

@router.get("/{symbol}/analysis")
def analyze_stock(symbol: str, provider: str = "auto", language: str = "zh"):
    import requests as req_lib

    table_name = f"{symbol.lower()}_1d"
    df = db.get_stock_data(table_name, limit=100)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    close = df['Close'].astype(float)
    price = round(float(close.iloc[-1]), 2)

    # RSI
    delta = close.diff()
    avg_gain = delta.clip(lower=0).ewm(com=13, min_periods=14).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(com=13, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, float('nan'))
    rsi = round(float((100 - 100 / (1 + rs)).iloc[-1]), 1)

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = round(float((ema12 - ema26).iloc[-1]), 3)

    # SMA
    sma20 = round(float(close.rolling(20).mean().iloc[-1]), 2)
    sma50 = round(float(close.rolling(50).mean().iloc[-1]), 2)

    rsi_sig = "Oversold" if rsi < 30 else ("Overbought" if rsi > 70 else "Neutral")
    macd_sig = "Bullish" if macd > 0 else "Bearish"

    if language == "en":
        prompt = f"""Analyze stock {symbol}: Price ${price}, RSI {rsi} ({rsi_sig}), MACD {macd} ({macd_sig}), SMA20 {sma20}, SMA50 {sma50}.
Provide: 1) Trend 2) Key S/R levels 3) Strategy recommendation. Be concise."""
        sys_msg = "You are a professional stock market analyst."
    else:
        prompt = f"""分析股票 {symbol}：当前价格 ${price}，RSI {rsi}（{rsi_sig}），MACD {macd}（{macd_sig}），SMA20 {sma20}，SMA50 {sma50}。
请给出：1) 趋势判断 2) 支撑/阻力位 3) 操作建议。回答简洁，使用中文。"""
        sys_msg = "你是一个资深股票分析师，请用中文回答。"

    analysis_text = None
    source = "Unknown"
    provider_errors = []

    # Try OpenRouter first in auto mode because the Gemini free-tier quota can
    # be exhausted while OpenRouter/Minimax is still available.
    if (provider in ["auto", "openrouter"]) and OPENROUTER_API_KEY:
        try:
            resp = req_lib.post("https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://stock.blackrice.top",
                    "X-Title": "BRStock AI",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
                    "max_tokens": 420,
                    "temperature": 0.2,
                },
                timeout=18)
            if not resp.ok:
                detail = f"OpenRouter unavailable ({resp.status_code})"
                provider_errors.append(detail)
                print(_provider_unavailable_label("OpenRouter", status_code=resp.status_code))
            else:
                data = resp.json()
                analysis_text = data["choices"][0]["message"]["content"]
                source = f"OpenRouter ({OPENROUTER_MODEL})"
        except Exception as e:
            provider_errors.append("OpenRouter unavailable")
            print(_provider_unavailable_label("OpenRouter", exc=e))

    # Try Gemini
    if not analysis_text and (provider in ["auto", "gemini"]) and GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            analysis_text = response.text
            source = "Gemini"
        except Exception as e:
            provider_errors.append(f"Gemini unavailable: {type(e).__name__}")
            print(_provider_unavailable_label("Gemini", exc=e))

    # Local AI fallback
    if not analysis_text:
        try:
            resp = req_lib.post(LOCAL_AI_URL,
                json={"model": "local", "messages": [{"role": "user", "content": prompt}]},
                timeout=30)
            data = resp.json()
            choices = data.get("choices") or []
            if choices:
                analysis_text = choices[0]["message"]["content"]
                source = "Local AI"
            else:
                provider_errors.append("Local AI unavailable")
                print(_provider_unavailable_label("Local AI"))
        except Exception as e:
            provider_errors.append("Local AI unavailable")
            print(_provider_unavailable_label("Local AI", exc=e))

    if not analysis_text:
        analysis_text = _rule_based_technical_analysis(symbol.upper(), price, rsi, rsi_sig, macd, macd_sig, sma20, sma50, language)
        source = "BRStock Technical Engine"

    return {
        "symbol": symbol.upper(),
        "price": price,
        "rsi": rsi,
        "macd": macd,
        "sma20": sma20,
        "sma50": sma50,
        "analysis": analysis_text,
        "source": source,
        "status_message": _friendly_ai_status(source, provider_errors, language),
    }
