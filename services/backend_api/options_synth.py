import numpy as np
import pandas as pd
from scipy.stats import norm
from datetime import datetime, timedelta
from pathlib import Path
import json
import options_calibration

class OptionSynth:
    def __init__(self, risk_free_rate=0.04, use_calibration=True):
        self.r = risk_free_rate
        self.use_calibration = use_calibration
        self._calibration_version = None
        self._calibration_mtime = None
        self._calibration_source_path = None
        self._calibration = None

    def load_calibration(self, force=False):
        if not self.use_calibration:
            return {"version": 0, "buckets": {}}
        loaded = options_calibration.load_calibration_with_source()
        path = loaded.get("source_path")
        try:
            source_path = Path(path) if path else None
            mtime = source_path.stat().st_mtime if source_path and source_path.exists() else None
        except Exception:
            mtime = None
        if not force and self._calibration is not None and path == self._calibration_source_path and mtime == self._calibration_mtime:
            return self._calibration
        model = loaded["model"]
        version = model.get("version")
        if force or self._calibration is None or version != self._calibration_version or path != self._calibration_source_path or mtime != self._calibration_mtime:
            self._calibration = model
            self._calibration_version = version
            self._calibration_mtime = mtime
            self._calibration_source_path = path
        return self._calibration or {"version": 0, "buckets": {}}

    def calibration_adjustment(self, ticker, option_type, dte, delta):
        if not ticker:
            return None
        model = self.load_calibration()
        key = options_calibration.bucket_key(ticker, option_type, dte, delta)
        adjustment = (model.get("buckets") or {}).get(key)
        if not adjustment:
            return None
        return {"key": key, **adjustment}

    def _normalize_inputs(self, S, K, T, sigma):
        S = float(S)
        K = float(K)
        T = max(float(T), 0.0)
        sigma = max(float(sigma), 0.0001)
        return S, K, T, sigma

    def black_scholes(self, S, K, T, r, sigma, q=0, option_type='call'):
        """
        S: Current Price, K: Strike Price, T: Years to expiry
        r: Risk-free rate, sigma: Implied Volatility, q: Dividend yield
        """
        S, K, T, sigma = self._normalize_inputs(S, K, T, sigma)
        if T <= 0:
            if option_type == 'call':
                return max(S - K, 0)
            return max(K - S, 0)

        d1 = (np.log(S/K) + (r - q + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)

        if option_type == 'call':
            price = S*np.exp(-q*T)*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)
        else:
            price = K*np.exp(-r*T)*norm.cdf(-d2) - S*np.exp(-q*T)*norm.cdf(-d1)

        return max(price, 0.01)

    def calc_greeks(self, S, K, T, r, sigma, q=0, option_type='call'):
        """Calculate Greeks: Delta, Gamma, Theta, Vega"""
        S, K, T, sigma = self._normalize_inputs(S, K, T, sigma)
        if T <= 0:
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
            
        d1 = (np.log(S/K) + (r - q + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)

        gamma = np.exp(-q*T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))
        vega = S * np.exp(-q*T) * norm.pdf(d1) * np.sqrt(T) / 100

        if option_type == 'call':
            delta = np.exp(-q*T) * norm.cdf(d1)
            theta = (-(S*sigma*np.exp(-q*T)*norm.pdf(d1))/(2*np.sqrt(T))
                     - r*K*np.exp(-r*T)*norm.cdf(d2)
                     + q*S*np.exp(-q*T)*norm.cdf(d1)) / 365
        else:
            delta = np.exp(-q*T) * (norm.cdf(d1) - 1)
            theta = (-(S*sigma*np.exp(-q*T)*norm.pdf(d1))/(2*np.sqrt(T))
                     + r*K*np.exp(-r*T)*norm.cdf(-d2)
                     - q*S*np.exp(-q*T)*norm.cdf(-d1)) / 365

        return {'delta': delta, 'gamma': gamma, 'theta': theta, 'vega': vega}

    def _strike_step(self, spot):
        """Use realistic-enough strike spacing for liquid US names."""
        if spot >= 1000:
            return 10
        if spot >= 100:
            return 5
        if spot >= 25:
            return 2.5
        return 1

    def calc_synthetic_iv(self, rsi, hv_20, strike, spot):
        """
        Map RSI and technical indicators to Implied Volatility.
        """
        # Sentiment Multiplier based on RSI
        sentiment_multiplier = 1.0
        if rsi < 20: sentiment_multiplier = 1.8
        elif rsi < 30: sentiment_multiplier = 1.5
        elif rsi < 45: sentiment_multiplier = 1.2
        elif rsi < 55: sentiment_multiplier = 1.0
        elif rsi < 70: sentiment_multiplier = 0.9
        else: sentiment_multiplier = 1.1

        # Skew Factor (Volatility Smile)
        moneyness = strike / spot
        skew = 1.0
        if moneyness < 0.95:
            skew = 1.0 + 0.3 * (0.95 - moneyness)
        elif moneyness > 1.05:
            skew = 1.0 + 0.1 * (moneyness - 1.05)

        iv = hv_20 * sentiment_multiplier * skew
        return max(iv, 0.05) # Minimum 5% IV

    def generate_chain(self, date, spot, rsi, hv_20, r=None, q=0.0, dte_list=None, ticker=None, apply_calibration=True):
        if r is None: r = self.r

        step = self._strike_step(spot)
        base = np.floor(spot * 0.7 / step) * step
        top = np.ceil(spot * 1.3 / step) * step + step
        strikes = np.arange(base, top, step)

        if dte_list is None:
            dte_list = [30, 45, 90, 180, 365]
        chain = []
        
        for dte in dte_list:
            T = dte / 365.0
            expiry_date = pd.to_datetime(date) + pd.Timedelta(days=int(dte))
            for K in strikes:
                iv = self.calc_synthetic_iv(rsi, hv_20, K, spot)
                for opt_type in ['call', 'put']:
                    premium = self.black_scholes(spot, K, T, r, iv, q, opt_type)
                    greeks = self.calc_greeks(spot, K, T, r, iv, q, opt_type)
                    adjustment = None
                    adjusted_iv = iv
                    if apply_calibration and ticker:
                        adjustment = self.calibration_adjustment(ticker, opt_type.upper(), dte, greeks["delta"])
                        if adjustment:
                            adjusted_iv = max(iv + float(adjustment.get("iv_shift") or 0), 0.01)
                            premium = self.black_scholes(spot, K, T, r, adjusted_iv, q, opt_type)
                            greeks = self.calc_greeks(spot, K, T, r, adjusted_iv, q, opt_type)
                            premium *= float(adjustment.get("mid_multiplier") or 1.0)
                            greeks["delta"] += float(adjustment.get("delta_bias") or 0.0)
                    intrinsic = max(spot - K, 0) if opt_type == 'call' else max(K - spot, 0)
                    premium = max(premium, intrinsic + 0.01)
                    extrinsic = max(premium - intrinsic, 0)

                    moneyness = abs(K - spot) / spot
                    spread_pct = 0.02 + moneyness * 0.05
                    if adjustment:
                        spread_pct *= float(adjustment.get("spread_multiplier") or 1.0)
                    bid = premium * (1 - spread_pct / 2)
                    ask = premium * (1 + spread_pct / 2)

                    option = {
                        'date': str(date),
                        'expiry_date': expiry_date.date().isoformat(),
                        'expiry_dte': dte,
                        'strike': round(float(K), 2),
                        'type': opt_type.upper(),
                        'moneyness': round(float(K / spot), 4),
                        'distance_pct': round(float(moneyness), 4),
                        'intrinsic': round(float(intrinsic), 2),
                        'extrinsic': round(float(extrinsic), 2),
                        'premium': round(float(premium), 2),
                        'bid': round(max(float(bid), 0.01), 2),
                        'ask': round(max(float(ask), 0.01), 2),
                        'iv': round(float(adjusted_iv), 4),
                        'delta': round(float(greeks['delta']), 4),
                        'gamma': round(float(greeks['gamma']), 6),
                        'theta': round(float(greeks['theta']), 4),
                        'vega': round(float(greeks['vega']), 4),
                    }
                    if adjustment:
                        option["calibrated"] = True
                        option["calibration_key"] = adjustment.get("key")
                        option["calibration_version"] = self._calibration_version
                    chain.append(option)
        return chain

class OptionBacktester:
    def __init__(self, db_client, synth_engine):
        self.db = db_client
        self.synth = synth_engine

    def run_wheels(self, ticker, start_date, end_date, initial_capital=50000, put_delta=-0.3, call_delta=0.3, dte_target=30, df=None):
        # 1. Get daily stock data
        if df is None:
            table_name = f"{ticker.lower()}_1d"
            df = self.db.get_stock_data(table_name, limit=10000)
            if df.empty:
                return {"error": f"No data for {ticker}"}
            df = df.reset_index()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        else:
            # Handle yfinance format
            df = df.reset_index()
            if 'Date' in df.columns: df = df.rename(columns={'Date': 'timestamp'})
            elif 'date' in df.columns: df = df.rename(columns={'date': 'timestamp'})
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)].sort_values('timestamp')
        
        if len(df) < 20:
            return {"error": f"Insufficient data for {ticker} in range {start_date} to {end_date} (found {len(df)} rows)"}

        # 2. Calculate technicals (RSI, HV)
        close = df['Close'].astype(float)
        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=13, min_periods=14).mean()
        avg_loss = loss.ewm(com=13, min_periods=14).mean()
        rs = avg_gain / avg_loss.replace(0, float('nan'))
        df['rsi'] = 100 - 100 / (1 + rs)
        # HV (20d)
        log_ret = np.log(close / close.shift(1))
        df['hv_20'] = log_ret.rolling(window=20).std() * np.sqrt(252)
        
        df = df.dropna(subset=['rsi', 'hv_20'])
        
        # 3. Simulation Loop
        capital = initial_capital
        position = 0 # Shares held
        in_put = False
        in_call = False
        current_option = None
        trades = []
        equity_curve = []
        
        for i, row in df.iterrows():
            date = row['timestamp']
            spot = row['Close']
            rsi = row['rsi']
            hv = row['hv_20']
            
            # Update equity
            current_equity = capital + (position * spot)
            if current_option:
                # Value current option
                T_remain = (current_option['expiry_date'] - date).days / 365.0
                opt_val = self.synth.black_scholes(spot, current_option['strike'], T_remain, 0.04, current_option['iv'], 0, current_option['type'].lower())
                # If we are sellers, option value is a liability
                current_equity -= opt_val * 100 * 1 
                
            equity_curve.append({
                "date": str(date.date()),
                "equity": round(current_equity, 2),
                "underlying_price": round(spot, 2)
            })

            # Check expiry
            if current_option and date >= current_option['expiry_date']:
                # Settlement
                strike = current_option['strike']
                if current_option['type'] == 'PUT':
                    if spot < strike: # Assigned
                        assigned_shares = 100
                        cost = assigned_shares * strike
                        position += assigned_shares
                        capital -= cost
                        trades.append({"date": str(date.date()), "type": "ASSIGNED", "price": strike, "shares": 100})
                    else: # Expired worthless
                        trades.append({"date": str(date.date()), "type": "PUT_EXPIRED", "price": strike})
                elif current_option['type'] == 'CALL':
                    if spot > strike: # Called away
                        proceeds = 100 * strike
                        capital += proceeds
                        position -= 100
                        trades.append({"date": str(date.date()), "type": "CALLED_AWAY", "price": strike, "shares": 100})
                    else: # Expired worthless
                        trades.append({"date": str(date.date()), "type": "CALL_EXPIRED", "price": strike})
                
                current_option = None

            # Open new positions
            if not current_option:
                if position == 0:
                    # Sell Put
                    chain = self.synth.generate_chain(date.date(), spot, rsi, hv, ticker=ticker)
                    # Find option closest to target delta
                    puts = [o for o in chain if o['type'] == 'PUT' and o['expiry_dte'] == 30]
                    if puts:
                        best_put = min(puts, key=lambda x: abs(x['delta'] - put_delta))
                        premium = best_put['bid']
                        capital += premium * 100
                        current_option = {
                            "type": "PUT",
                            "strike": best_put['strike'],
                            "expiry_date": date + timedelta(days=30),
                            "iv": best_put['iv'],
                            "premium": premium
                        }
                        trades.append({"date": str(date.date()), "type": "SELL_PUT", "strike": best_put['strike'], "premium": premium})
                elif position >= 100:
                    # Sell Call
                    chain = self.synth.generate_chain(date.date(), spot, rsi, hv, ticker=ticker)
                    calls = [o for o in chain if o['type'] == 'CALL' and o['expiry_dte'] == 30]
                    if calls:
                        best_call = min(calls, key=lambda x: abs(x['delta'] - call_delta))
                        premium = best_call['bid']
                        capital += premium * 100
                        current_option = {
                            "type": "CALL",
                            "strike": best_call['strike'],
                            "expiry_date": date + timedelta(days=30),
                            "iv": best_call['iv'],
                            "premium": premium
                        }
                        trades.append({"date": str(date.date()), "type": "SELL_CALL", "strike": best_call['strike'], "premium": premium})

        return {
            "strategy": "WHEELS",
            "ticker": ticker,
            "initial_capital": initial_capital,
            "final_capital": round(current_equity, 2),
            "trades": trades,
            "equity_curve": equity_curve
        }

    def run_leaps(
        self,
        ticker,
        start_date,
        end_date,
        initial_capital=100000,
        delta_target=0.8,
        dte_target=365,
        capital_utilization=0.30,
        roll_dte=60,
        fill_slippage=0.10,
        df=None
    ):
        # 1. Get daily stock data
        if df is None:
            table_name = f"{ticker.lower()}_1d"
            df = self.db.get_stock_data(table_name, limit=10000)
            if df.empty: return {"error": f"No data for {ticker}"}
            df = df.reset_index()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        else:
            df = df.reset_index()
            if 'Date' in df.columns: df = df.rename(columns={'Date': 'timestamp'})
            elif 'date' in df.columns: df = df.rename(columns={'date': 'timestamp'})
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)].sort_values('timestamp')
        if len(df) < 20: return {"error": f"Insufficient data (found {len(df)} rows)"}

        # 2. Tech indicators
        close = df['Close'].astype(float)
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=13, min_periods=14).mean()
        avg_loss = loss.ewm(com=13, min_periods=14).mean()
        rs = avg_gain / avg_loss.replace(0, float('nan'))
        df['rsi'] = 100 - 100 / (1 + rs)
        log_ret = np.log(close / close.shift(1))
        df['hv_20'] = log_ret.rolling(window=20).std() * np.sqrt(252)
        df = df.dropna(subset=['rsi', 'hv_20'])

        # 3. Simulation Loop
        capital = initial_capital
        current_option = None
        trades = []
        equity_curve = []
        pos_counter = 0

        capital_utilization = min(max(float(capital_utilization or 0.30), 0), 1)
        roll_dte = int(roll_dte or 60)
        fill_slippage = min(max(float(fill_slippage or 0), 0), 0.5)
        
        for i, row in df.iterrows():
            date = row['timestamp']
            spot = float(row['Close'])
            rsi = row['rsi']
            hv = row['hv_20']
            
            # Update equity
            current_equity = capital
            if current_option:
                T_remain = (current_option['expiry_date'] - date).days / 365.0
                opt_val = self.synth.black_scholes(spot, current_option['strike'], T_remain, 0.04, current_option['iv'], 0, 'call')
                current_equity += opt_val * 100 * current_option['qty']
            
            equity_curve.append({
                "date": str(date.date()),
                "equity": round(current_equity, 2),
                "underlying_price": round(spot, 2)
            })

            # Check expiry or roll (if DTE < 60)
            if current_option:
                dte_now = (current_option['expiry_date'] - date).days
                if dte_now < roll_dte or date >= current_option['expiry_date']:
                    # Sell current
                    T_remain = max(dte_now, 0) / 365.0
                    sell_price = self.synth.black_scholes(spot, current_option['strike'], T_remain, 0.04, current_option['iv'], 0, 'call')
                    exit_cash_flow = sell_price * 100 * current_option['qty']
                    capital += exit_cash_flow
                    net_pnl = exit_cash_flow + current_option['entry_cash_flow']
                    trades.append({
                        "date": str(date.date()),
                        "event": "CLOSE",
                        "type": "CLOSE_LEAPS",
                        "strategy": "LEAPS",
                        "underlying_price": round(spot, 2),
                        "price": round(spot, 2),
                        "pl": round(net_pnl, 2),
                        "cash_flow": round(exit_cash_flow, 2),
                        "entry_cash_flow": round(current_option['entry_cash_flow'], 2),
                        "shares": current_option['qty'] * 100,
                        "qty": current_option['qty'],
                        "pos_id": current_option['pos_id'],
                        "long_leg": current_option['long_leg'],
                        "short_leg": "",
                        "long_delta": current_option['delta'],
                        "short_delta": None,
                        "dte": current_option['dte'],
                        "spread_width": "-",
                        "max_loss": round(abs(current_option['entry_cash_flow']), 2),
                        "max_profit": None,
                        "cash_balance": round(capital, 2),
                        "locked_risk": 0,
                        "locked_collateral": 0,
                        "available_cash": round(capital, 2),
                        "memo": f"{current_option['pos_id']} close | Sell LEAPS @ {sell_price:.2f} | Net P/L ${net_pnl:,.2f}"
                    })
                    current_option = None

            # Open new LEAPS
            if not current_option:
                chain = self.synth.generate_chain(date.date(), spot, rsi, hv, dte_list=[dte_target], ticker=ticker)
                leaps = [o for o in chain if o['type'] == 'CALL' and o['expiry_dte'] == dte_target]
                if leaps:
                    best_leaps = min(leaps, key=lambda x: abs(x['delta'] - delta_target))
                    mid = (best_leaps['bid'] + best_leaps['ask']) / 2
                    premium = mid + ((best_leaps['ask'] - best_leaps['bid']) * fill_slippage)
                    cost_per_contract = premium * 100
                    risk_budget = max(current_equity * capital_utilization, 0)
                    qty = min(int(risk_budget / cost_per_contract), int(capital / cost_per_contract))
                    if qty >= 1:
                        total_cost = cost_per_contract * qty
                        capital -= total_cost
                        pos_id = f"P{pos_counter}"
                        pos_counter += 1
                        current_option = {
                            "pos_id": pos_id,
                            "type": "CALL",
                            "strike": best_leaps['strike'],
                            "expiry_date": date + timedelta(days=365),
                            "iv": best_leaps['iv'],
                            "premium": premium,
                            "qty": qty,
                            "delta": best_leaps['delta'],
                            "dte": dte_target,
                            "entry_cash_flow": -total_cost,
                            "long_leg": f"BUY {qty} CALL {best_leaps['strike']} @ {round(premium, 2)}"
                        }
                        trades.append({
                            "date": str(date.date()),
                            "event": "OPEN",
                            "type": "OPEN_LEAPS",
                            "strategy": "LEAPS",
                            "underlying_price": round(spot, 2),
                            "price": round(spot, 2),
                            "pl": 0,
                            "cash_flow": round(-total_cost, 2),
                            "shares": qty * 100,
                            "qty": qty,
                            "pos_id": pos_id,
                            "long_leg": current_option['long_leg'],
                            "short_leg": "",
                            "long_delta": best_leaps['delta'],
                            "short_delta": None,
                            "dte": dte_target,
                            "spread_width": "-",
                            "max_loss": round(total_cost, 2),
                            "max_profit": None,
                            "cash_balance": round(capital, 2),
                            "locked_risk": round(total_cost, 2),
                            "locked_collateral": 0,
                            "available_cash": round(capital, 2),
                            "memo": f"{pos_id} open | {current_option['long_leg']}"
                        })

        ending_option_value = 0
        if current_option and not df.empty:
            ending_date = df.iloc[-1]['timestamp']
            ending_spot = float(df.iloc[-1]['Close'])
            T_remain = max((current_option['expiry_date'] - ending_date).days / 365.0, 0.001)
            ending_price = self.synth.black_scholes(ending_spot, current_option['strike'], T_remain, 0.04, current_option['iv'], 0, 'call')
            ending_option_value = ending_price * 100 * current_option['qty']

        ending_equity = capital + ending_option_value
        if equity_curve:
            equity_curve[-1]["equity"] = round(ending_equity, 2)

        return {
            "strategy": "LEAPS",
            "ticker": ticker,
            "initial_capital": initial_capital,
            "final_capital": round(ending_equity, 2),
            "trades": trades,
            "equity_curve": equity_curve,
            "metrics": {
                "capital_utilization_pct": capital_utilization,
                "delta_target": delta_target,
                "dte_target": dte_target,
                "roll_dte": roll_dte,
                "fill_slippage": fill_slippage,
                "ending_cash": round(capital, 2),
                "ending_option_value": round(ending_option_value, 2),
                "ending_equity": round(ending_equity, 2),
                "ending_locked_risk": round(abs(current_option['entry_cash_flow']), 2) if current_option else 0,
                "ending_locked_collateral": 0,
                "ending_available_cash": round(capital, 2),
                "open_positions": 1 if current_option else 0
            }
        }

    def run_spreads(
        self,
        ticker,
        start_date,
        end_date,
        initial_capital=100000,
        strategy_type="BULL_CALL",
        dte_target=40,
        risk_pct=0.30,
        long_delta_target=None,
        short_delta_target=None,
        spread_width=20,
        delta_tolerance=0.15,
        fill_slippage=0.10,
        open_interval_days=None,
        max_open_positions=4,
        entry_rsi_min=None,
        entry_rsi_max=None,
        df=None
    ):
        # 1. Get daily stock data
        if df is None:
            table_name = f"{ticker.lower()}_1d"
            df = self.db.get_stock_data(table_name, limit=10000)
            if df.empty: return {"error": f"No data for {ticker}"}
            df = df.reset_index()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        else:
            # Handle yfinance format
            df = df.reset_index()
            if 'Date' in df.columns: df = df.rename(columns={'Date': 'timestamp'})
            elif 'date' in df.columns: df = df.rename(columns={'date': 'timestamp'})
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)].sort_values('timestamp')
        if len(df) < 20:
            return {"error": f"Insufficient data (found {len(df)} rows)"}

        # 2. Calculate technicals
        close = df['Close'].astype(float)
        delta = close.diff(); gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=13, min_periods=14).mean(); avg_loss = loss.ewm(com=13, min_periods=14).mean()
        rs = avg_gain / avg_loss.replace(0, float('nan')); df['rsi'] = 100 - 100 / (1 + rs)
        df['hv_20'] = np.log(close / close.shift(1)).rolling(window=20).std() * np.sqrt(252)
        df = df.dropna(subset=['rsi', 'hv_20'])

        if df.empty:
            return {"error": "Insufficient indicator data"}

        # 3. Simulation
        capital = initial_capital
        active_spreads = [] # List of dicts
        trades = []
        equity_curve = []
        last_opened_date = None

        dte_target = int(dte_target or 40)
        risk_pct = max(float(risk_pct or 0.30), 0)
        spread_width = float(spread_width or 0)
        delta_tolerance = max(float(delta_tolerance or 0.15), 0)
        fill_slippage = min(max(float(fill_slippage or 0), 0), 0.5)
        max_open_positions = max(int(max_open_positions or 4), 1)
        open_interval_days = int(open_interval_days or max(1, round(dte_target / max_open_positions)))

        # Strategy Params
        if strategy_type == "BULL_CALL":
            opt_type = "CALL"
            long_delta = float(long_delta_target if long_delta_target is not None else 0.60)
            short_delta = float(short_delta_target if short_delta_target is not None else 0.30)
            entry_rsi_min = 50 if entry_rsi_min is None else float(entry_rsi_min)
            spread_label = "Bull Call Debit Spread"
        elif strategy_type == "BEAR_PUT":
            opt_type = "PUT"
            long_delta = float(long_delta_target if long_delta_target is not None else -0.60)
            short_delta = float(short_delta_target if short_delta_target is not None else -0.30)
            entry_rsi_max = 50 if entry_rsi_max is None else float(entry_rsi_max)
            spread_label = "Bear Put Debit Spread"
        else: # BULL_PUT
            opt_type = "PUT"
            long_delta = float(long_delta_target if long_delta_target is not None else -0.10)
            short_delta = float(short_delta_target if short_delta_target is not None else -0.30)
            spread_label = "Bull Put Credit Spread"

        for i, row in df.iterrows():
            date = row['timestamp']
            spot = float(row['Close'])
            rsi = row['rsi']
            hv = row['hv_20']
            
            # 3.1 Update Daily Equity
            current_option_value = 0
            risk_at_work = 0
            locked_collateral = 0
            remaining_spreads = []
            for spread in active_spreads:
                if date >= spread['expiry_date']:
                    # Settlement
                    long_k, short_k = spread['long_k'], spread['short_k']
                    opt_type = spread['opt_type']
                    qty = spread['qty']
                    pos_id = spread['pos_id']
                    
                    if opt_type == "CALL":
                        long_payoff = max(spot - long_k, 0)
                        short_payoff = max(spot - short_k, 0)
                    else: # PUT
                        long_payoff = max(long_k - spot, 0)
                        short_payoff = max(short_k - spot, 0)
                    
                    settlement_cash_flow = (long_payoff - short_payoff) * 100 * qty
                    capital += settlement_cash_flow
                    
                    # Net P/L = entry cash flow + expiry settlement.
                    net_pnl = spread['entry_cash_flow'] + settlement_cash_flow
                    trades.append({
                        "date": str(date.date()), 
                        "event": "CLOSE",
                        "type": f"CLOSE_{strategy_type}",
                                "strategy": spread_label,
                                "underlying_price": round(spot, 2),
                                "price": round(spot, 2),
                                "pl": round(net_pnl, 2),
                                "cash_flow": round(settlement_cash_flow, 2),
                        "entry_cash_flow": round(spread['entry_cash_flow'], 2),
                        "shares": qty * 100,
                        "qty": qty,
                        "pos_id": pos_id,
                        "long_leg": spread['long_leg'],
                                "short_leg": spread['short_leg'],
                                "long_delta": spread.get('long_delta'),
                                "short_delta": spread.get('short_delta'),
                                "dte": spread.get('dte'),
                                "spread_width": spread.get('spread_width'),
                                "max_loss": round(spread['max_loss'], 2),
                                "max_profit": round(spread['max_profit'], 2),
                        "cash_balance": round(capital, 2),
                        "locked_risk": round(sum(s['max_loss'] for s in remaining_spreads), 2),
                        "locked_collateral": round(sum(s.get('collateral', 0) for s in remaining_spreads), 2),
                        "available_cash": round(capital - sum(s.get('collateral', 0) for s in remaining_spreads), 2),
                        "memo": f"{pos_id} close | Settlement ${settlement_cash_flow:,.2f} | Net P/L ${net_pnl:,.2f}"
                    })
                else:
                    # Black-Scholes Valuation
                    T_remain = max((spread['expiry_date'] - date).days / 365.0, 0.001)
                    long_val = self.synth.black_scholes(spot, spread['long_k'], T_remain, 0.04, spread['long_iv'], 0, spread['opt_type'].lower())
                    short_val = self.synth.black_scholes(spot, spread['short_k'], T_remain, 0.04, spread['short_iv'], 0, spread['opt_type'].lower())
                    val_per_share = long_val - short_val
                    current_option_value += val_per_share * 100 * spread['qty']
                    risk_at_work += spread['max_loss']
                    locked_collateral += spread.get('collateral', 0)
                    remaining_spreads.append(spread)
            
            active_spreads = remaining_spreads
            current_equity = capital + current_option_value
            available_cash = capital - locked_collateral
            equity_curve.append({
                "date": str(date.date()),
                "equity": round(current_equity, 2),
                "underlying_price": round(spot, 2),
                "cash": round(capital, 2),
                "option_value": round(current_option_value, 2),
                "locked_risk": round(risk_at_work, 2),
                "locked_collateral": round(locked_collateral, 2),
                "available_cash": round(available_cash, 2),
                "active_positions": len(active_spreads)
            })

            # 3.2 Open new Spread
            rsi_allows_entry = True
            if entry_rsi_min is not None and rsi < entry_rsi_min:
                rsi_allows_entry = False
            if entry_rsi_max is not None and rsi > entry_rsi_max:
                rsi_allows_entry = False

            can_open_by_date = last_opened_date is None or (date - last_opened_date).days >= open_interval_days
            can_open_by_slots = len(active_spreads) < max_open_positions
            if rsi_allows_entry and can_open_by_slots and can_open_by_date:
                chain = self.synth.generate_chain(date.date(), spot, rsi, hv, dte_list=[dte_target], ticker=ticker)
                options = [o for o in chain if o['type'] == opt_type and o['expiry_dte'] == dte_target]
                if len(options) >= 2:
                    if strategy_type == "BULL_PUT":
                        short_leg = min(options, key=lambda x: abs(x['delta'] - short_delta))
                        if spread_width > 0:
                            target_long_strike = short_leg['strike'] - spread_width
                            long_candidates = [o for o in options if o['strike'] < short_leg['strike']]
                            long_leg = min(long_candidates, key=lambda x: abs(x['strike'] - target_long_strike)) if long_candidates else None
                        else:
                            long_leg = min(options, key=lambda x: abs(x['delta'] - long_delta))
                    else:
                        long_leg = min(options, key=lambda x: abs(x['delta'] - long_delta))
                        if spread_width > 0:
                            target_short_strike = long_leg['strike'] + spread_width if strategy_type == "BULL_CALL" else long_leg['strike'] - spread_width
                            if strategy_type == "BULL_CALL":
                                short_candidates = [o for o in options if o['strike'] > long_leg['strike']]
                            else:
                                short_candidates = [o for o in options if o['strike'] < long_leg['strike']]
                            short_leg = min(short_candidates, key=lambda x: abs(x['strike'] - target_short_strike)) if short_candidates else None
                        else:
                            short_leg = min(options, key=lambda x: abs(x['delta'] - short_delta))

                    if not long_leg or not short_leg:
                        continue
                    if abs(long_leg['delta'] - long_delta) > delta_tolerance:
                        continue
                    
                    valid_structure = (
                        (strategy_type == "BULL_CALL" and long_leg['strike'] < short_leg['strike']) or
                        (strategy_type == "BEAR_PUT" and long_leg['strike'] > short_leg['strike']) or
                        (strategy_type == "BULL_PUT" and long_leg['strike'] < short_leg['strike'])
                    )

                    if valid_structure:
                        width = abs(long_leg['strike'] - short_leg['strike'])
                        long_mid = (long_leg['bid'] + long_leg['ask']) / 2
                        short_mid = (short_leg['bid'] + short_leg['ask']) / 2
                        long_fill = long_mid + ((long_leg['ask'] - long_leg['bid']) * fill_slippage)
                        short_fill = short_mid - ((short_leg['ask'] - short_leg['bid']) * fill_slippage)
                        long_debit = long_fill * 100
                        short_credit = short_fill * 100
                        entry_cash_flow_per_spread = short_credit - long_debit

                        if strategy_type in ("BULL_CALL", "BEAR_PUT"):
                            # Debit spreads pay cash up front; max loss is the debit.
                            if entry_cash_flow_per_spread >= 0:
                                continue
                            max_loss_per_spread = abs(entry_cash_flow_per_spread)
                            max_profit_per_spread = (width * 100) - max_loss_per_spread
                        else:
                            # Credit spreads receive premium but must reserve max loss.
                            if entry_cash_flow_per_spread <= 0:
                                continue
                            max_profit_per_spread = entry_cash_flow_per_spread
                            max_loss_per_spread = (width * 100) - entry_cash_flow_per_spread

                        if max_loss_per_spread <= 0 or max_profit_per_spread <= 0:
                            continue

                        max_portfolio_risk = max(current_equity * risk_pct, 0)
                        risk_budget = max(max_portfolio_risk - risk_at_work, 0)
                        available_risk_capital = max(available_cash, 0)
                        qty_by_risk_budget = int(risk_budget / max_loss_per_spread)
                        qty_by_available_cash = int(available_risk_capital / max_loss_per_spread)
                        qty = min(qty_by_risk_budget, qty_by_available_cash)

                        if qty < 1:
                            continue

                        total_entry_cash_flow = entry_cash_flow_per_spread * qty
                        total_max_loss = max_loss_per_spread * qty
                        total_max_profit = max_profit_per_spread * qty
                        collateral = total_max_loss if strategy_type == "BULL_PUT" else 0

                        if strategy_type in ("BULL_CALL", "BEAR_PUT") and capital < abs(total_entry_cash_flow):
                            continue

                        if available_cash >= max(total_max_loss, collateral):
                            capital += total_entry_cash_flow
                            pos_id = f"P{len(trades)}"
                            new_risk_at_work = risk_at_work + total_max_loss
                            new_locked_collateral = locked_collateral + collateral
                            new_available_cash = capital - new_locked_collateral

                            new_spread = {
                                "pos_id": pos_id,
                                "long_k": long_leg['strike'],
                                "short_k": short_leg['strike'],
                                "long_iv": long_leg['iv'],
                                "short_iv": short_leg['iv'],
                                "opt_type": opt_type,
                                "long_leg": f"BUY {qty} {opt_type} {long_leg['strike']} @ {round(long_fill, 2)}",
                                "short_leg": f"SELL {qty} {opt_type} {short_leg['strike']} @ {round(short_fill, 2)}",
                                "fill_slippage": fill_slippage,
                                "long_delta": long_leg['delta'],
                                "short_delta": short_leg['delta'],
                                "dte": dte_target,
                                "spread_width": width,
                                "qty": qty,
                                "entry_cash_flow": total_entry_cash_flow,
                                "max_loss": total_max_loss,
                                "max_profit": total_max_profit,
                                "collateral": collateral,
                                "expiry_date": date + timedelta(days=dte_target)
                            }
                            active_spreads.append(new_spread)
                            last_opened_date = date
                            
                            trades.append({
                                "date": str(date.date()), 
                                "event": "OPEN",
                                "type": f"OPEN_{strategy_type}",
                                "strategy": spread_label,
                                "underlying_price": round(spot, 2),
                                "price": round(spot, 2),
                                "pl": 0,
                                "cash_flow": round(total_entry_cash_flow, 2),
                                "shares": qty * 100,
                                "qty": qty,
                                "pos_id": pos_id,
                                "long_leg": new_spread['long_leg'],
                                "short_leg": new_spread['short_leg'],
                                "long_delta": long_leg['delta'],
                                "short_delta": short_leg['delta'],
                                "dte": dte_target,
                                "spread_width": width,
                                "max_loss": round(total_max_loss, 2),
                                "max_profit": round(total_max_profit, 2),
                                "cash_balance": round(capital, 2),
                                "locked_risk": round(new_risk_at_work, 2),
                                "locked_collateral": round(new_locked_collateral, 2),
                                "available_cash": round(new_available_cash, 2),
                                "memo": f"{pos_id} open | {new_spread['long_leg']} / {new_spread['short_leg']}"
                            })

        ending_option_value = 0
        if not df.empty:
            ending_date = df.iloc[-1]['timestamp']
            ending_spot = float(df.iloc[-1]['Close'])
            for spread in active_spreads:
                T_remain = max((spread['expiry_date'] - ending_date).days / 365.0, 0.001)
                if spread['opt_type'] == "CALL":
                    long_payoff = max(ending_spot - spread['long_k'], 0)
                    short_payoff = max(ending_spot - spread['short_k'], 0)
                else:
                    long_payoff = max(spread['long_k'] - ending_spot, 0)
                    short_payoff = max(spread['short_k'] - ending_spot, 0)

                if ending_date >= spread['expiry_date']:
                    val_per_share = long_payoff - short_payoff
                else:
                    long_val = self.synth.black_scholes(ending_spot, spread['long_k'], T_remain, 0.04, spread['long_iv'], 0, spread['opt_type'].lower())
                    short_val = self.synth.black_scholes(ending_spot, spread['short_k'], T_remain, 0.04, spread['short_iv'], 0, spread['opt_type'].lower())
                    val_per_share = long_val - short_val
                ending_option_value += val_per_share * 100 * spread['qty']

        ending_equity = capital + ending_option_value
        if equity_curve:
            equity_curve[-1].update({
                "equity": round(ending_equity, 2),
                "cash": round(capital, 2),
                "option_value": round(ending_option_value, 2),
                "locked_risk": round(sum(s['max_loss'] for s in active_spreads), 2),
                "locked_collateral": round(sum(s.get('collateral', 0) for s in active_spreads), 2),
                "available_cash": round(capital - sum(s.get('collateral', 0) for s in active_spreads), 2),
                "active_positions": len(active_spreads)
            })

        return {
            "strategy": strategy_type,
            "ticker": ticker,
            "initial_capital": initial_capital,
            "final_capital": round(ending_equity, 2),
            "trades": trades,
            "equity_curve": equity_curve,
            "metrics": {
                "risk_pct": risk_pct,
                "capital_utilization_pct": risk_pct,
                "dte_target": dte_target,
                "long_delta_target": long_delta,
                "short_delta_target": short_delta,
                "spread_width": spread_width,
                "delta_tolerance": delta_tolerance,
                "fill_slippage": fill_slippage,
                "open_interval_days": open_interval_days,
                "max_open_positions": max_open_positions,
                "open_positions": len(active_spreads),
                "ending_cash": round(capital, 2),
                "ending_option_value": round(ending_option_value, 2),
                "ending_equity": round(ending_equity, 2),
                "ending_locked_risk": round(sum(s['max_loss'] for s in active_spreads), 2),
                "ending_locked_collateral": round(sum(s.get('collateral', 0) for s in active_spreads), 2),
                "ending_available_cash": round(capital - sum(s.get('collateral', 0) for s in active_spreads), 2)
            }
        }
