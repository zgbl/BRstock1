import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# 将项目根目录加入路径，方便引用 internal 模块
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

# 加载环境变量 (使用绝对路径确保从项目任何地方启动都能读到)
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# 配置 Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY and GEMINI_API_KEY.strip():
    print(f"✅ Gemini API Key found (Starts with: {GEMINI_API_KEY[:4]}...)")
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("⚠️ Gemini API Key NOT found or empty in .env. Falling back to Local AI.")

# 本地 AI 地址
LOCAL_AI_URL = os.getenv("LOCAL_AI_URL", "http://192.168.0.162:8912/v1/chat/completions")

from fastapi import FastAPI, HTTPException
import pandas as pd
import numpy as np
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from internal.db_client.database import StockDB
import requests
import json
print("--- SYSTEM STARTING: FastAPI initializing ---")
app = FastAPI(title="BRStock AI API", version="0.1.0")
db = StockDB()

# ── 全局请求日志 (调试必备) ──────────────────────────────────
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"Incoming Request: {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"Request Finished: {request.url.path} (Status: {response.status_code})")
    return response

# ── API Routes ──────────────────────────────────────────────

@app.get("/api/health")
def health():
    """服务器健康检查"""
    return {"status": "ok", "version": "0.1.0"}

@app.get("/api/stocks")
def list_stocks():
    """返回当前数据库中所有可用的股票代码列表"""
    import sqlite3
    try:
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
        return {"symbols": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/{symbol}/history")
def get_stock_history(symbol: str, limit: int = 200):
    """
    返回指定股票的历史 K 线数据 (5m)。
    """
    table_name = f"{symbol.upper()}_5m"
    print(f"DEBUG: Fetching history for {table_name}")
    df = db.get_stock_data(table_name, limit=limit)

    if df.empty:
        print(f"ERROR: No data found for {table_name}")
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}. Run the data pipeline first.")

    # 将 DataFrame 转成前端友好的 JSON 格式
    df = df.reset_index()
    df['timestamp'] = df['timestamp'].astype(str)
    records = df[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']].to_dict(orient='records')

    latest = records[-1]
    first  = records[0]
    change = round(latest['Close'] - first['Open'], 2)
    pct    = round(change / (first['Open'] if first['Open'] != 0 else 1) * 100, 2)

    return {
        "symbol": symbol.upper(),
        "count": len(records),
        "latest_price": latest['Close'],
        "change": change,
        "change_pct": pct,
        "data": records
    }

@app.get("/api/stocks/{symbol}/summary")
def get_stock_summary(symbol: str):
    """返回单支股票的最新价格 + 简要统计（基于最近交易日）"""
    import pandas as pd
    table_name = f"{symbol.upper()}_5m"
    df = db.get_stock_data(table_name, limit=500)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}.")

    # 最新收盘价
    close_p = float(df.iloc[-1]['Close'])

    # 只取最近一个交易日的数据
    df.index = pd.to_datetime(df.index, utc=True)
    latest_date = df.index.normalize().max()
    today_df = df[df.index.normalize() == latest_date]

    day_open  = float(today_df.iloc[0]['Open'])   # 当日第一根K线开盘价
    day_high  = float(today_df['High'].max())
    day_low   = float(today_df['Low'].min())
    volume    = int(today_df['Volume'].sum())

    change = round(close_p - day_open, 2)
    pct    = round(change / (day_open if day_open != 0 else 1) * 100, 2)

    return {
        "symbol":     symbol.upper(),
        "price":      close_p,
        "open":       day_open,
        "high":       day_high,
        "low":        day_low,
        "volume":     volume,
        "change":     change,
        "change_pct": pct,
    }

@app.get("/api/stocks/{symbol}/indicators")
def get_stock_indicators(symbol: str):
    """
    计算并返回当前股票的技术指标 (RSI, MACD, SMA/EMA)。
    """
    print(f"--- [API CALLBACK] Calculating indicators for: {symbol} ---")
    table_name = f"{symbol.upper()}_5m"
    df = db.get_stock_data(table_name, limit=500)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}.")

    close = df['Close'].astype(float)
    n = len(close)

    # ── RSI (14) ──────────────────────────────────────────────
    def calc_rsi(series, period=14):
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, float('nan'))
        return 100 - 100 / (1 + rs)

    rsi_series = calc_rsi(close, 14)
    rsi_latest = float(round(rsi_series.iloc[-1], 2)) if not rsi_series.empty else None

    # 构建 RSI 历史序列（给前端画图）
    df_idx = df.reset_index()
    rsi_history = []
    for i, row in df_idx.iterrows():
        v = rsi_series.iloc[i]
        if not pd.isna(v):
            rsi_history.append({
                "timestamp": str(row['timestamp']),
                "value": round(float(v), 2)
            })

    # ── MACD (12, 26, 9) ──────────────────────────────────────
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line

    macd_latest   = float(round(macd_line.iloc[-1], 4))
    signal_latest = float(round(signal_line.iloc[-1], 4))
    hist_latest   = float(round(histogram.iloc[-1], 4))

    macd_history = []
    for i, row in df_idx.iterrows():
        ts = str(row['timestamp'])
        ml, sl, hl = macd_line.iloc[i], signal_line.iloc[i], histogram.iloc[i]
        if any(pd.isna(x) for x in [ml, sl, hl]):
            continue
        macd_history.append({
            "timestamp": ts,
            "macd":      round(float(ml), 4),
            "signal":    round(float(sl), 4),
            "histogram": round(float(hl), 4)
        })

    # ── Moving Averages (SMA & EMA 20/50) ────────────────────
    sma20 = close.rolling(window=20).mean()
    sma50 = close.rolling(window=50).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    def safe_float(val):
        return float(round(val, 4)) if not pd.isna(val) else None

    ma_history = []
    for i, row in df_idx.iterrows():
        entry = {
            "timestamp": str(row['timestamp']),
            "sma20":  safe_float(sma20.iloc[i]),
            "sma50":  safe_float(sma50.iloc[i]),
            "ema20":  safe_float(ema20.iloc[i]),
            "ema50":  safe_float(ema50.iloc[i]),
        }
        # 至少有一条均线有值才加入
        if any(v is not None for k, v in entry.items() if k != 'timestamp'):
            ma_history.append(entry)

    # ── RSI 解读 ──────────────────────────────────────────────
    if rsi_latest is not None:
        if rsi_latest >= 70:
            rsi_signal = "overbought"
        elif rsi_latest <= 30:
            rsi_signal = "oversold"
        else:
            rsi_signal = "neutral"
    else:
        rsi_signal = "unknown"

    # ── MACD 解读 ─────────────────────────────────────────────
    macd_signal_str = "bullish" if macd_latest > signal_latest else "bearish"

    return {
        "symbol": symbol.upper(),
        "rsi": {
            "period":  14,
            "latest":  rsi_latest,
            "signal":  rsi_signal,
            "history": rsi_history
        },
        "macd": {
            "fast":         12,
            "slow":         26,
            "signal_period": 9,
            "macd_latest":   macd_latest,
            "signal_latest": signal_latest,
            "hist_latest":   hist_latest,
            "signal":        macd_signal_str,
            "history":       macd_history
        },
        "moving_averages": {
            "sma20_latest": safe_float(sma20.iloc[-1]),
            "sma50_latest": safe_float(sma50.iloc[-1]),
            "ema20_latest": safe_float(ema20.iloc[-1]),
            "ema50_latest": safe_float(ema50.iloc[-1]),
            "history":      ma_history
        }
    }

@app.get("/api/stocks/{symbol}/ai_analysis")
def get_stock_ai_analysis(symbol: str, lang: str = "zh"):
    """
    获取 AI 对技术指标的详细分析。
    """
    import requests
    import google.generativeai as genai
    print(f"--- Received AI Analysis Request for: {symbol} (lang: {lang}) ---")
    try:
        # 1. 获取指标数据
        print(f"DEBUG: Fetching indicators for {symbol}")
        indicators = get_stock_indicators(symbol)
        
        # 2. 格式化数据为 Prompt
        rsi = indicators['rsi']['latest']
        rsi_sig = indicators['rsi']['signal']
        macd = indicators['macd']['macd_latest']
        macd_sig = indicators['macd']['signal']
        sma20 = indicators['moving_averages']['sma20_latest']
        sma50 = indicators['moving_averages']['sma50_latest']
        
        if lang == "en":
            prompt = f"""
            You are a senior stock market analyst. Analyze the stock {symbol} based on these indicators:
            - RSI (14): {rsi} (Signal: {rsi_sig})
            - MACD: {macd} (Signal: {macd_sig})
            - SMA 20: {sma20}
            - SMA 50: {sma50}
            
            Please provide:
            1. Trend Judgment (Bullish/Bearish/Neutral)
            2. Support and Resistance Predictions (based on indicators)
            3. Suggested Action Strategy.
            
            Keep the answer concise and professional in English.
            """
            sys_msg = "You are a professional stock market analyst. Provide analysis in English."
        else:
            prompt = f"""
            你是一个资深的股票分析师。请根据以下技术指标对股票 {symbol} 进行简短而深刻的分析：
            - RSI (14): {rsi} (信号: {rsi_sig})
            - MACD: {macd} (信号: {macd_sig})
            - SMA 20: {sma20}
            - SMA 50: {sma50}
            
            请给出：
            1. 趋势判断（看涨/看跌/中性）
            2. 关键支撑位和阻力位预测（基于指标暗示）
            3. 建议的操作策略。
            
            回答请简洁明了，使用中文。
            """
            sys_msg = "You are a professional stock market analyst. Provide concise analysis in Chinese."
        
        # --- 策略：Gemini 优先，Local 备选 ---
        analysis_text = None
        source = "Unknown"

        # 1. 尝试 Gemini (最新系列)
        if GEMINI_API_KEY:
            try:
                print(f"--- Attempting Gemini Analysis for {symbol} (Model: gemini-3-flash-preview) ---")
                #model = genai.GenerativeModel('gemini-2.5-flash') # 'gemini-2.5-flash' works
                model = genai.GenerativeModel('gemini-3-flash-preview') # 'gemini-3-flash-preview' works
                full_prompt = f"{sys_msg}\n\n{prompt}"
                response = model.generate_content(
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=4096,
                    )
                )
                analysis_text = response.text
                source = "Google Gemini (2.5-flash)"
            except Exception as e:
                print(f"Gemini Error, falling back to Local AI: {e}")

        # 2. 如果 Gemini 失败或未配置，尝试 Local AI
        if not analysis_text:
            try:
                print(f"--- Attempting Local AI Analysis for {symbol} ({LOCAL_AI_URL}) ---")
                payload = {
                    "model": "google/gemma-4-e4b",
                    "messages": [
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4096
                }
                # 注意：本地调用超时时间设长一点以便 Reasoning
                res = requests.post(LOCAL_AI_URL, json=payload, timeout=300)
                if res.status_code == 200:
                    analysis_text = res.json()['choices'][0]['message']['content']
                    source = "Local AI (LM Studio)"
                else:
                    print(f"Local AI Error: {res.text}")
            except Exception as e:
                print(f"Local AI also failed: {e}")

        # 3. 返回结果
        if analysis_text:
            return {
                "symbol": symbol.upper(),
                "analysis": analysis_text,
                "source": source
            }
        else:
            return {
                "symbol": symbol.upper(),
                "analysis": "AI 分析暂时不可用：Gemini 与本地模型均调用失败。请检查配置。"
            }
        
    except Exception as e:
        print(f"AI Analysis Error: {e}")
        # 如果 LLM 不通，返回一个友好的错误信息
        return {
            "symbol": symbol.upper(),
            "analysis": f"AI 分析暂时不可用: {str(e)}"
        }

# ── Root redirect ───────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui/index.html")

# ── Serve Frontend Static Files ─────────────────────────────
# 重要：static mount 必须放在所有 API 路由注册之后。
# 挂载到 /ui 子路径，彻底避免拦截 /api/* 请求。
WEB_UI_PATH = PROJECT_ROOT / "services" / "web_ui"
app.mount("/ui", StaticFiles(directory=str(WEB_UI_PATH), html=True), name="web_ui")
