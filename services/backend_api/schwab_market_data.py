import base64
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qs, unquote, urlencode, urlparse

import pandas as pd
import requests


SCHWAB_AUTH_URL = "https://api.schwabapi.com/v1/oauth/authorize"
SCHWAB_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
SCHWAB_MARKETDATA_BASE_URL = "https://api.schwabapi.com/marketdata/v1"


class SchwabAuthError(RuntimeError):
    pass


class SchwabMarketDataProvider:
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        scope: Optional[str] = None,
        token_path: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("SCHWAB_CLIENT_ID", "").strip()
        self.client_secret = client_secret or os.getenv("SCHWAB_CLIENT_SECRET", "").strip()
        self.redirect_uri = redirect_uri or os.getenv(
            "SCHWAB_REDIRECT_URI",
            "https://developer.schwab.com/oauth2-redirect.html",
        ).strip()
        self.scope = scope or os.getenv("SCHWAB_SCOPE", "readonly").strip()
        self.token_store = os.getenv("SCHWAB_TOKEN_STORE", "file").strip().lower()
        self.token_key = os.getenv("SCHWAB_TOKEN_KEY", "schwab_market_data").strip()
        self._token_engine = None

        raw_token_path = token_path or os.getenv("SCHWAB_TOKEN_PATH", ".schwab_tokens.json")
        self.token_path = Path(raw_token_path)
        if not self.token_path.is_absolute():
            self.token_path = Path(__file__).resolve().parents[2] / self.token_path

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def get_authorization_url(self) -> str:
        self._require_config()
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "scope": self.scope,
            "redirect_uri": self.redirect_uri,
        }
        return f"{SCHWAB_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> Dict[str, Any]:
        self._require_config()
        clean_code = self._normalize_authorization_code(code)
        payload = {
            "grant_type": "authorization_code",
            "code": clean_code,
            "redirect_uri": self.redirect_uri,
        }
        token = self._token_request(payload)
        self._save_token(token, include_refresh_expiry=True)
        return self._redact_token(token)

    def refresh_access_token(self) -> Dict[str, Any]:
        self._require_config()
        stored = self._load_token()
        refresh_token = stored.get("refresh_token")
        if not refresh_token:
            raise SchwabAuthError("No Schwab refresh_token found. Complete OAuth authorization first.")

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        token = self._token_request(payload)
        if "refresh_token" not in token:
            token["refresh_token"] = refresh_token
        self._save_token(token)
        return self._redact_token(token)

    def status(self) -> Dict[str, Any]:
        configured = self.is_configured()
        token = self._load_token()
        now = int(time.time())
        expires_at = int(token.get("expires_at") or 0)
        refresh_expires_at = int(token.get("refresh_token_expires_at") or 0)
        return {
            "provider": "schwab",
            "configured": configured,
            "token_store": self.token_store,
            "token_file": str(self.token_path),
            "has_access_token": bool(token.get("access_token")),
            "has_refresh_token": bool(token.get("refresh_token")),
            "access_token_valid": bool(token.get("access_token") and expires_at > now + 60),
            "access_token_expires_at": expires_at or None,
            "refresh_token_expires_at": refresh_expires_at or None,
            "authorization_url": self.get_authorization_url() if configured else None,
        }

    def get_quotes(self, symbols: Iterable[str], fields: str = "quote,reference,regular") -> Dict[str, Any]:
        clean_symbols = [s.strip().upper() for s in symbols if s and s.strip()]
        if not clean_symbols:
            raise ValueError("At least one symbol is required")
        return self._marketdata_get(
            "/quotes",
            {
                "symbols": ",".join(clean_symbols),
                "fields": fields,
            },
        )

    def get_quote(self, symbol: str, fields: str = "quote,reference,regular") -> Dict[str, Any]:
        return self.get_quotes([symbol], fields=fields)

    def get_price_history(
        self,
        symbol: str,
        period_type: str = "day",
        period: int = 10,
        frequency_type: str = "minute",
        frequency: int = 5,
        need_extended_hours_data: bool = False,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        params = {
            "symbol": symbol.strip().upper(),
            "frequencyType": frequency_type,
            "frequency": frequency,
            "needExtendedHoursData": str(need_extended_hours_data).lower(),
        }
        if start_datetime is not None:
            start_dt = pd.to_datetime(start_datetime).to_pydatetime().replace(tzinfo=timezone.utc)
            params["startDate"] = int(start_dt.timestamp() * 1000)
            if end_datetime is not None:
                end_dt = pd.to_datetime(end_datetime).to_pydatetime().replace(tzinfo=timezone.utc)
                params["endDate"] = int(end_dt.timestamp() * 1000)
        else:
            params["periodType"] = period_type
            params["period"] = period
        return self._marketdata_get("/pricehistory", params)

    def get_option_chain(self, symbol: str, **params: Any) -> Dict[str, Any]:
        query = {"symbol": symbol.strip().upper()}
        query.update({k: v for k, v in params.items() if v is not None})
        return self._marketdata_get("/chains", query)

    def get_normalized_option_chain(self, symbol: str, **params: Any) -> Dict[str, Any]:
        raw = self.get_option_chain(symbol, **params)
        options = []
        for map_name, option_type in (("callExpDateMap", "CALL"), ("putExpDateMap", "PUT")):
            for exp_key, strikes in (raw.get(map_name) or {}).items():
                expiry, dte = self._parse_expiry_key(exp_key)
                for contracts in (strikes or {}).values():
                    for contract in contracts or []:
                        bid = self._safe_float(contract.get("bid"))
                        ask = self._safe_float(contract.get("ask"))
                        mark = self._safe_float(contract.get("mark"))
                        mid = round((bid + ask) / 2, 2) if bid is not None and ask is not None and ask > 0 else mark
                        last_price = self._safe_float(contract.get("last"))
                        iv = self._safe_float(contract.get("volatility"))
                        options.append(
                            {
                                "symbol": contract.get("symbol"),
                                "description": contract.get("description"),
                                "underlying": raw.get("symbol") or symbol.upper(),
                                "type": contract.get("putCall") or option_type,
                                "strike": self._safe_float(contract.get("strikePrice")),
                                "expiry": expiry,
                                "expiry_dte": self._safe_int(contract.get("daysToExpiration"), dte),
                                "bid": bid,
                                "ask": ask,
                                "mid": mid,
                                "mark": mark,
                                "last_price": last_price,
                                "volume": self._safe_int(contract.get("totalVolume"), 0),
                                "open_interest": self._safe_int(contract.get("openInterest"), 0),
                                "delta": self._safe_float(contract.get("delta")),
                                "gamma": self._safe_float(contract.get("gamma")),
                                "theta": self._safe_float(contract.get("theta")),
                                "vega": self._safe_float(contract.get("vega")),
                                "iv": round(iv / 100, 6) if iv is not None and iv > 2 else iv,
                                "in_the_money": bool(contract.get("inTheMoney")),
                                "quote_time": self._epoch_ms_to_iso(contract.get("quoteTimeInLong")),
                                "trade_time": self._epoch_ms_to_iso(contract.get("tradeTimeInLong")),
                            }
                        )
        options.sort(key=lambda o: (o.get("expiry") or "", abs((o.get("strike") or 0) - (raw.get("underlyingPrice") or 0)), o.get("type") or ""))
        return {
            "ticker": symbol.upper(),
            "provider": "schwab",
            "status": raw.get("status"),
            "underlying_price": raw.get("underlyingPrice"),
            "volatility": raw.get("volatility"),
            "options": options,
            "raw_counts": {
                "calls": sum(len(contracts or []) for strikes in (raw.get("callExpDateMap") or {}).values() for contracts in (strikes or {}).values()),
                "puts": sum(len(contracts or []) for strikes in (raw.get("putExpDateMap") or {}).values() for contracts in (strikes or {}).values()),
            },
        }

    def get_price_history_frame(
        self,
        symbol: str,
        period_type: str = "day",
        period: int = 10,
        frequency_type: str = "minute",
        frequency: int = 5,
        need_extended_hours_data: bool = False,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
    ) -> pd.DataFrame:
        payload = self.get_price_history(
            symbol,
            period_type=period_type,
            period=period,
            frequency_type=frequency_type,
            frequency=frequency,
            need_extended_hours_data=need_extended_hours_data,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )
        candles = payload.get("candles") or []
        if not candles:
            return pd.DataFrame()
        frame = pd.DataFrame(candles)
        frame["timestamp"] = pd.to_datetime(frame["datetime"], unit="ms", utc=True).dt.tz_convert(None)
        frame = frame.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            }
        )
        frame = frame.set_index("timestamp")
        return frame[["Open", "High", "Low", "Close", "Volume"]].sort_index()

    def _marketdata_get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        token = self._get_valid_access_token()
        response = requests.get(
            f"{SCHWAB_MARKETDATA_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params=params,
            timeout=30,
        )
        if response.status_code == 401:
            self.refresh_access_token()
            token = self._load_token().get("access_token")
            if not token:
                raise SchwabAuthError("Unable to refresh Schwab access token")
            response = requests.get(
                f"{SCHWAB_MARKETDATA_BASE_URL}{path}",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                params=params,
                timeout=30,
            )
        if not response.ok:
            raise RuntimeError(f"Schwab API {response.status_code}: {response.text[:1000]}")
        return response.json()

    def _get_valid_access_token(self) -> str:
        token = self._load_token()
        now = int(time.time())
        if token.get("access_token") and int(token.get("expires_at") or 0) > now + 60:
            return token["access_token"]
        self.refresh_access_token()
        token = self._load_token()
        if not token.get("access_token"):
            raise SchwabAuthError("No Schwab access_token found after refresh")
        return token["access_token"]

    def _token_request(self, payload: Dict[str, str]) -> Dict[str, Any]:
        auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8")).decode("ascii")
        response = requests.post(
            SCHWAB_TOKEN_URL,
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data=payload,
            timeout=30,
        )
        if not response.ok:
            raise SchwabAuthError(f"Schwab token request failed {response.status_code}: {response.text[:1000]}")
        return response.json()

    def _save_token(self, token: Dict[str, Any], include_refresh_expiry: bool = False) -> None:
        now = int(time.time())
        current = self._load_token()
        merged = {**current, **token}
        if "expires_in" in token:
            merged["expires_at"] = now + int(token["expires_in"])
        if include_refresh_expiry and token.get("refresh_token"):
            merged["refresh_token_expires_at"] = now + 7 * 24 * 60 * 60
        if self.token_store == "database":
            self._save_token_to_database(merged)
            return
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(json.dumps(merged, indent=2, sort_keys=True), encoding="utf-8")
        try:
            self.token_path.chmod(0o600)
        except OSError:
            pass

    def _load_token(self) -> Dict[str, Any]:
        if self.token_store == "database":
            return self._load_token_from_database()
        if not self.token_path.exists():
            return {}
        try:
            return json.loads(self.token_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _get_token_engine(self):
        if self._token_engine is not None:
            return self._token_engine
        from sqlalchemy import create_engine

        db_url = os.getenv("DATABASE_URL", "").strip()
        if not db_url:
            raise SchwabAuthError("Schwab token database store requires DATABASE_URL")
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        self._token_engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=1800)
        return self._token_engine

    def _ensure_token_table(self, conn) -> None:
        from sqlalchemy import text

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_runtime_secrets (
                key VARCHAR(100) PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

    def _save_token_to_database(self, token: Dict[str, Any]) -> None:
        from sqlalchemy import text

        engine = self._get_token_engine()
        payload = json.dumps(token, separators=(",", ":"), sort_keys=True)
        with engine.begin() as conn:
            self._ensure_token_table(conn)
            conn.execute(text("DELETE FROM app_runtime_secrets WHERE key = :key"), {"key": self.token_key})
            conn.execute(
                text("""
                    INSERT INTO app_runtime_secrets (key, value_json, updated_at)
                    VALUES (:key, :value_json, CURRENT_TIMESTAMP)
                """),
                {"key": self.token_key, "value_json": payload},
            )

    def _load_token_from_database(self) -> Dict[str, Any]:
        from sqlalchemy import text

        try:
            engine = self._get_token_engine()
            with engine.begin() as conn:
                self._ensure_token_table(conn)
                row = conn.execute(
                    text("SELECT value_json FROM app_runtime_secrets WHERE key = :key"),
                    {"key": self.token_key},
                ).fetchone()
            if not row:
                return {}
            return json.loads(row[0])
        except SchwabAuthError:
            raise
        except Exception:
            return {}

    def _require_config(self) -> None:
        if not self.is_configured():
            raise SchwabAuthError("Schwab OAuth client configuration is missing")

    @staticmethod
    def _redact_token(token: Dict[str, Any]) -> Dict[str, Any]:
        redacted = dict(token)
        for key in ("access_token", "refresh_token", "id_token"):
            if redacted.get(key):
                value = str(redacted[key])
                redacted[key] = f"{value[:6]}...{value[-4:]}" if len(value) > 12 else "***"
        return redacted

    @staticmethod
    def _normalize_authorization_code(value: str) -> str:
        raw = value.strip()
        if not raw:
            raise SchwabAuthError("Authorization code is required")

        if raw.startswith("http://") or raw.startswith("https://"):
            parsed = urlparse(raw)
            code_values = parse_qs(parsed.query).get("code")
            if not code_values:
                raise SchwabAuthError("Redirect URL does not contain a code query parameter")
            return code_values[0].strip()

        if raw.startswith("code="):
            return unquote(raw.split("=", 1)[1].split("&", 1)[0]).strip()

        return unquote(raw)

    @staticmethod
    def _parse_expiry_key(value: str) -> tuple[str, Optional[int]]:
        expiry, _, dte = str(value).partition(":")
        try:
            return expiry, int(dte) if dte else None
        except ValueError:
            return expiry, None

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: Any, fallback: Optional[int] = None) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _epoch_ms_to_iso(value: Any) -> Optional[str]:
        try:
            return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            return None


_provider = None


def get_schwab_provider() -> SchwabMarketDataProvider:
    global _provider
    if _provider is None:
        _provider = SchwabMarketDataProvider()
    return _provider
