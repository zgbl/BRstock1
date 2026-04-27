import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# 将项目根目录加入路径，方便引用 internal 模块
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

# 加载环境变量 (统一使用根目录下的 .env)
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH)

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import Depends, status

# 安全配置
SECRET_KEY = os.getenv("SECRET_KEY", "brstock_super_secret_key_9988")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 一周过期

# 使用 PBKDF2-SHA256 算法（不依赖外部 bcrypt 库，解决版本兼容性问题）
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

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
from pydantic import BaseModel
import pandas as pd
import numpy as np
import yfinance as yf
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from internal.db_client.database import StockDB
import requests
import json
print("--- SYSTEM STARTING: FastAPI initializing ---")
app = FastAPI(title="BRStock AI API", version="0.1.0")
db = StockDB()

# 确保数据库表存在
def init_db_tables():
    from sqlalchemy import text
    with db.engine.connect() as conn:
        # 用户表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                email VARCHAR(100) PRIMARY KEY,
                hashed_password VARCHAR(255),
                full_name VARCHAR(100),
                reset_pin VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        # 自选股表 (更新 user_id 长度)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_watchlists (
                user_id VARCHAR(100),
                ticker VARCHAR(10),
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, ticker)
            );
        """))
        conn.commit()

init_db_tables()

# ── 认证工具函数 ──────────────────────────────────────────────
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
    except JWTError:
        raise credentials_exception

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
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        # 排除掉可能存在的系统表或 alembic 表（如果有的话）
        symbols = [t for t in tables if not t.startswith('sqlite_')]
        return {"symbols": symbols}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/stocks/search")
def search_stocks(q: str):
    """搜索股票代号（基于 stocks 表）"""
    try:
        from sqlalchemy import text
        query = text("SELECT ticker, name FROM stocks WHERE ticker ILIKE :q OR name ILIKE :q LIMIT 10")
        with db.engine.connect() as conn:
            result = conn.execute(query, {"q": f"%{q}%"}).fetchall()
        return [{"ticker": r[0], "name": r[1]} for r in result]
    except Exception as e:
        print(f"Search error: {e}")
        return []

@app.post("/api/stocks/{symbol}/fetch")
def fetch_stock_on_demand(symbol: str):
    """按需抓取单支股票的数据"""
    symbol = symbol.upper()
    table_name = f"{symbol.lower()}_5m"
    
    try:
        print(f"📡 On-demand fetch for {symbol}...")
        
        # 1. Intraday 5m (last 60 days)
        df_5m = yf.download(symbol, period="60d", interval="5m")
        if not df_5m.empty:
            if isinstance(df_5m.columns, pd.MultiIndex): df_5m.columns = df_5m.columns.get_level_values(0)
            if df_5m.index.tz is not None: df_5m.index = df_5m.index.tz_localize(None)
            db.save_stock_data(df_5m, f"{symbol.lower()}_5m")
            
        # 2. Daily 1d (last 30 years)
        df_1d = yf.download(symbol, period="30y", interval="1d")
        if not df_1d.empty:
            if isinstance(df_1d.columns, pd.MultiIndex): df_1d.columns = df_1d.columns.get_level_values(0)
            if df_1d.index.tz is not None: df_1d.index = df_1d.index.tz_localize(None)
            db.save_stock_data(df_1d, f"{symbol.lower()}_1d")
            
        return {"status": "success", "message": f"Data for {symbol} (5m & 1d) updated."}
    except Exception as e:
        print(f"Fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    reset_pin: str

@app.post("/api/auth/register")
def register(user: UserRegister):
    from sqlalchemy import text
    try:
        # 存储用户 (包含 PIN)
        with db.engine.connect() as conn:
            query = text("""
                INSERT INTO users (email, hashed_password, full_name, reset_pin)
                VALUES (:email, :pw, :name, :pin)
            """)
            conn.execute(query, {
                "email": user.email,
                "pw": get_password_hash(user.password),
                "name": user.full_name,
                "pin": user.reset_pin
            })
            conn.commit()
        return {"message": "User registered successfully"}
    except Exception as e:
        print(f"❌ Registration Error: {e}")
        raise HTTPException(status_code=400, detail="Email already registered or invalid data")

# ── 密码重置接口 ──────────────────────────────────────────────
class ResetPasswordRequest(BaseModel):
    email: str
    reset_pin: str
    new_password: str

@app.post("/api/auth/reset-password")
def reset_password(req: ResetPasswordRequest):
    from sqlalchemy import text
    with db.engine.connect() as conn:
        # 1. 先查用户是否存在
        check_user = text("SELECT reset_pin FROM users WHERE email = :email")
        user = conn.execute(check_user, {"email": req.email}).fetchone()
        
        if not user:
            raise HTTPException(status_code=400, detail="User with this email not found")
        
        # 2. 验证 PIN
        if user[0] != req.reset_pin:
            raise HTTPException(status_code=400, detail="Incorrect Reset PIN")
        
        # 3. 更新密码
        update_query = text("UPDATE users SET hashed_password = :pw WHERE email = :email")
        conn.execute(update_query, {
            "pw": get_password_hash(req.new_password),
            "email": req.email
        })
        conn.commit()
        
    return {"message": "Password reset successfully"}

@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    from sqlalchemy import text
    query = text("SELECT hashed_password FROM users WHERE email = :email")
    with db.engine.connect() as conn:
        user = conn.execute(query, {"email": form_data.username}).fetchone()
    
    if not user or not verify_password(form_data.password, user[0]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/watchlist")
def get_watchlist(token: Optional[str] = Depends(oauth2_scheme_optional)):
    """获取自选股列表。如果未登录，返回默认推荐列表。"""
    default_stocks = ["QQQ", "VOO", "TSLA", "NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOGL"]
    if not token:
        return default_stocks

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        current_user = payload.get("sub")
        if not current_user:
            return default_stocks
        
        from sqlalchemy import text
        query = text("SELECT ticker FROM user_watchlists WHERE user_id = :user ORDER BY added_at ASC")
        with db.engine.connect() as conn:
            result = conn.execute(query, {"user": current_user}).fetchall()
        return [r[0] for r in result] if result else default_stocks
    except Exception:
        return default_stocks

@app.post("/api/watchlist/{symbol}")
def add_to_watchlist(symbol: str, current_user: str = Depends(get_current_user)):
    """将股票加入数据库自选列表"""
    symbol = symbol.upper()
    try:
        from sqlalchemy import text
        query = text("""
            INSERT INTO user_watchlists (user_id, ticker) 
            VALUES (:user, :ticker)
            ON CONFLICT (user_id, ticker) DO NOTHING
        """)
        with db.engine.connect() as conn:
            conn.execute(query, {"user": current_user, "ticker": symbol})
            conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/watchlist/{symbol}")
def remove_from_watchlist(symbol: str, current_user: str = Depends(get_current_user)):
    """从数据库自选列表删除股票代号"""
    symbol = symbol.upper()
    try:
        from sqlalchemy import text
        query = text("DELETE FROM user_watchlists WHERE user_id = :user AND ticker = :ticker")
        with db.engine.connect() as conn:
            conn.execute(query, {"user": current_user, "ticker": symbol})
            conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/{symbol}/history")
def get_stock_history(symbol: str, interval: str = "1d", limit: int = 1000):
    """
    返回指定股票的历史 K 线数据。支持 interval: 5m, 1d, 1w, 1m
    """
    symbol = symbol.lower()
    
    # 确定读取哪个表
    if interval == "5m":
        table_name = f"{symbol}_5m"
        # 5m 数据通常只看最近几百条
        fetch_limit = limit
    else:
        # 1d, 1w, 1m 统一从 1d 表读数据进行转换
        table_name = f"{symbol}_1d"
        # 如果是 1d 且没有指定 limit，默认给多一点（比如 30 年约 7500 天）
        fetch_limit = 10000 if limit == 1000 else limit

    print(f"DEBUG: Fetching history for {table_name} (interval={interval})")
    df = db.get_stock_data(table_name, limit=fetch_limit)

    if df.empty:
        print(f"INFO: No data found for {table_name}, returning empty list.")
        return {
            "symbol": symbol.upper(),
            "count": 0,
            "data": []
        }

    # 转换周期 (Resampling)
    if interval == "1w":
        df = df.resample('W-FRI').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
    elif interval == "1m":
        df = df.resample('M').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

    # 将 DataFrame 转成前端友好的 JSON 格式
    df = df.reset_index()
    df['timestamp'] = df['timestamp'].astype(str)
    records = df[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']].to_dict(orient='records')

    return {
        "symbol": symbol.upper(),
        "interval": interval,
        "count": len(records),
        "data": records
    }

@app.get("/api/stocks/{symbol}/summary")
def get_stock_summary(symbol: str):
    """返回单支股票的最新价格 + 简要统计（基于最近交易日）"""
    import pandas as pd
    table_name = f"{symbol.lower()}_5m"

    df = db.get_stock_data(table_name, limit=500)

    if df.empty:
        return {
            "symbol":     symbol.upper(),
            "price":      0,
            "open":       0,
            "high":       0,
            "low":        0,
            "volume":     0,
            "change":     0,
            "change_pct": 0,
        }


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

    # 获取股票名称 (从 metadata 表)
    stock_name = symbol.upper()
    try:
        from sqlalchemy import text
        with db.engine.connect() as conn:
            res = conn.execute(text("SELECT name FROM stocks WHERE ticker = :t"), {"t": symbol.upper()}).fetchone()
            if res:
                stock_name = res[0]
    except Exception:
        pass

    return {
        "symbol":     symbol.upper(),
        "name":       stock_name,
        "price":      close_p,
        "open":       day_open,
        "high":       day_high,
        "low":        day_low,
        "volume":     volume,
        "change":     change,
        "change_pct": pct,
    }

@app.get("/api/stocks/{symbol}/indicators")
def get_stock_indicators(symbol: str, interval: str = "1d"):
    """
    计算并返回当前股票的技术指标 (RSI, MACD, SMA/EMA)。
    支持 interval: 5m, 1d, 1w, 1m
    """
    print(f"--- [API CALLBACK] Calculating indicators for: {symbol} (interval: {interval}) ---")
    
    if interval == "5m":
        table_name = f"{symbol.lower()}_5m"
    else:
        table_name = f"{symbol.lower()}_1d"

    df = db.get_stock_data(table_name, limit=1000)

    if df.empty:
        return {
            "symbol": symbol.upper(),
            "rsi": {"period": 14, "latest": None, "signal": "unknown", "history": []},
            "macd": {"macd_latest": 0, "signal_latest": 0, "hist_latest": 0, "signal": "unknown", "history": []},
            "moving_averages": {"sma20_latest": None, "sma50_latest": None, "ema20_latest": None, "ema50_latest": None, "history": []}
        }


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

    # 最新收盘价
    close_p = float(df.iloc[-1]['Close'])

    return {
        "symbol": symbol.upper(),
        "price":  close_p,
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
def get_stock_ai_analysis(symbol: str, lang: str = "en"):
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
        price = indicators['price']
        rsi = indicators['rsi']['latest']
        rsi_sig = indicators['rsi']['signal']
        macd = indicators['macd']['macd_latest']
        macd_sig = indicators['macd']['signal']
        sma20 = indicators['moving_averages']['sma20_latest']
        sma50 = indicators['moving_averages']['sma50_latest']
        
        if lang == "en":
            prompt = f"""
            You are a senior stock market analyst. Analyze the stock {symbol} based on these indicators:
            - Current Price: ${price}
            - RSI (14): {rsi} (Signal: {rsi_sig})
            - MACD: {macd} (Signal: {macd_sig})
            - SMA 20: {sma20}
            - SMA 50: {sma50}
            
            Please provide:
            1. Trend Judgment (Bullish/Bearish/Neutral)
            2. Support and Resistance Predictions. **Crucial**: Resistance must be ABOVE the current price (${price}), and Support must be BELOW it. Use technical levels implied by the SMAs and recent price action.
            3. Suggested Action Strategy.
            
            **Note**: Do NOT use outdated historical data from your internal knowledge. Strictly use the provided real-time data above.
            Keep the answer concise and professional in English.
            """
            sys_msg = "You are a professional stock market analyst. Provide analysis in English."
        else:
            prompt = f"""
            你是一个资深的股票分析师。请根据以下技术指标对股票 {symbol} 进行简短而深刻的分析：
            - 当前价格: ${price}
            - RSI (14): {rsi} (信号: {rsi_sig})
            - MACD: {macd} (信号: {macd_sig})
            - SMA 20: {sma20}
            - SMA 50: {sma50}
            
            请给出：
            1. 趋势判断（看涨/看跌/中性）
            2. 关键支撑位和阻力位预测。**特别注意**：阻力位必须高于当前价格 (${price})，支撑位必须低于当前价格。请结合均线位置和数值给出。
            3. 建议的操作策略。
            
            **禁令**：严禁使用你内部过时的历史记忆。必须且仅能基于上方提供的实时数据进行逻辑推导。如果当前价格已经突破了某个整数关口（如200），请将其列为支撑位而非阻力位。
            
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

if __name__ == "__main__":
    import uvicorn
    # Cloud Run 会注入 PORT 环境变量，默认为 8080
    port = int(os.environ.get("PORT", 8080))
    # 必须监听在 0.0.0.0 上，否则外部无法访问
    uvicorn.run(app, host="0.0.0.0", port=port)
