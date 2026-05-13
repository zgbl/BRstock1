import os
import json
import time
import socket
import futu
from futu import OpenQuoteContext, RET_OK, RET_ERROR
from typing import List, Dict, Any

class MoomooOptionsProvider:
    def __init__(self, host='127.0.0.1', port=11111, telnet_port=22222):
        self.host = host
        self.port = port
        self.telnet_port = telnet_port
        self.quote_ctx = None
        self.pending_verification = False   # True = OpenD waiting for SMS code
        self._last_fail_time = 0            # Circuit breaker: timestamp of last failure
        self._failure_count = 0             # Track consecutive failures
        self._cooldown_seconds = 60         # Wait 60s after 3 failures

    def _get_context(self):
        """Lazy initialization with circuit breaker and retry limit."""
        if self.quote_ctx is not None:
            return self.quote_ctx

        now = time.time()
        # Circuit breaker: if we reached max retries, wait for cooldown
        if self._failure_count >= 3:
            elapsed = now - self._last_fail_time
            if elapsed < self._cooldown_seconds:
                remaining = int(self._cooldown_seconds - elapsed)
                print(f"🔒 [CIRCUIT BREAKER] Moomoo OpenD connection blocked. Try again in {remaining}s.")
                return None
            else:
                # Cooldown finished, reset counter to allow new attempts
                print("🔄 Cooldown finished. Resetting retry counter.")
                self._failure_count = 0

        print(f"🔌 [DEBUG] Attempting to connect to Moomoo OpenD at {self.host}:{self.port} (Try {self._failure_count + 1}/3)...")
        ctx = None
        try:
            # Still keep is_retry_connect=False to control retries here instead of library background
            ctx = OpenQuoteContext(host=self.host, port=self.port, is_retry_connect=False)
            ret, data = ctx.get_market_state()
            if ret == RET_OK:
                self.quote_ctx = ctx
                self.pending_verification = False
                self._failure_count = 0
                print(f"✅ [SUCCESS] Moomoo OpenD is now CONNECTED at {self.host}:{self.port}")
            else:
                print(f"⚠️ [NOTICE] Moomoo OpenD connection failed or needs verification: {data}")
                ctx.close()
                self._failure_count += 1
                self._last_fail_time = now
                self.pending_verification = True
                return None
        except Exception as e:
            print(f"❌ [ERROR] Failed to connect to Moomoo OpenD: {e}")
            if ctx:
                try: ctx.close()
                except: pass
            self._failure_count += 1
            self._last_fail_time = now
            self.pending_verification = True
            return None

        return self.quote_ctx

    def check_connection(self) -> dict:
        """Explicitly check and log the connection status"""
        if self.quote_ctx is None:
            status = "DISCONNECTED"
            if self.pending_verification:
                status = "WAITING_FOR_VERIFICATION"
            print(f"📡 [STATUS] Moomoo OpenD: {status}")
            return {"status": status, "connected": False}
        
        try:
            ret, data = self.quote_ctx.get_market_state()
            if ret == RET_OK:
                print(f"📡 [STATUS] Moomoo OpenD: CONNECTED (Market State: {data})")
                return {"status": "CONNECTED", "connected": True, "data": str(data)}
            else:
                print(f"📡 [STATUS] Moomoo OpenD: ERROR ({data})")
                return {"status": "ERROR", "connected": False, "error": str(data)}
        except Exception as e:
            print(f"📡 [STATUS] Moomoo OpenD: EXCEPTION ({e})")
            return {"status": "EXCEPTION", "connected": False, "error": str(e)}

    def reset_circuit_breaker(self):
        """Call this after successfully sending a verify code to allow reconnection."""
        print("🔓 Circuit breaker reset. Will retry OpenD connection on next request.")
        self.pending_verification = False
        self._failure_count = 0
        self._last_fail_time = 0
        self.quote_ctx = None

    def get_option_chain(self, code: str, expiration_dates: List[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch option chain for a given ticker.
        code: e.g. 'US.TSLA'
        """
        ctx = self._get_context()
        if not ctx:
            return []

        # 1. If no expiration dates provided, get the next few
        if not expiration_dates:
            ret, data = ctx.get_option_expiration(code)
            if ret == RET_OK:
                # Take first 3 dates as a sample if many
                expiration_dates = data['date'].tolist()[:5]
            else:
                print(f"Error fetching expirations for {code}: {data}")
                return []

        all_options = []
        for date in expiration_dates:
            ret, data = ctx.get_option_chain(code, start=date, end=date)
            if ret == RET_OK:
                # Convert dataframe to list of dicts
                for _, row in data.iterrows():
                    all_options.append({
                        "symbol": row['code'],
                        "strike": float(row['strike_price']),
                        "expiry": date,
                        "type": "CALL" if "C" in row['code'] else "PUT", # Simplistic check
                        "last_price": 0, # Needs separate quote call usually
                    })
            else:
                print(f"Error fetching chain for {code} on {date}: {data}")

        return all_options

    def get_market_snapshot(self, codes: List[str]):
        """Get real-time snapshot for a list of symbols (including options)"""
        ctx = self._get_context()
        if not ctx: return []
        
        ret, data = ctx.get_market_snapshot(codes)
        if ret == RET_OK:
            return data.to_dict(orient='records')
        return []

    def send_command(self, cmd: str) -> str:
        """Send a raw command to OpenD console via socket with extra logging"""
        try:
            print(f"📡 [DEBUG] Connecting to OpenD at {self.host}:{self.telnet_port}...")
            with socket.create_connection((self.host, self.telnet_port), timeout=10) as sock:
                print(f"📡 [DEBUG] Connected. Draining welcome message...")
                sock.settimeout(1.0)
                
                # Drain welcome message until we see '>>>' or timeout
                welcome_chunks = []
                try:
                    while True:
                        chunk = sock.recv(4096).decode('ascii', errors='ignore')
                        if not chunk: break
                        welcome_chunks.append(chunk)
                        if ">>>" in chunk: break
                except socket.timeout:
                    pass
                
                welcome_msg = "".join(welcome_chunks)
                if welcome_msg:
                    print(f"📥 [DEBUG] Welcome message received ({len(welcome_msg)} bytes)")
                
                print(f"📡 [DEBUG] Sending command: {cmd}")
                sock.settimeout(10.0) # 10s is plenty for a command response
                
                # Send command with \n only (Moomoo OpenD sometimes chokes on \r)
                full_cmd = cmd.strip() + "\n"
                sock.sendall(full_cmd.encode('ascii'))
                
                print(f"⏳ [DEBUG] Command sent: {repr(full_cmd)}. Waiting for response...")
                time.sleep(0.2) # Small sleep to let OpenD process
                
                # Try to read response chunks
                chunks = []
                try:
                    while True:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        decoded_chunk = chunk.decode('ascii', errors='ignore')
                        chunks.append(decoded_chunk)
                        print(f"📥 [DEBUG] Received chunk: {repr(decoded_chunk)}")
                        
                        # Stop if we see the prompt '>>>'
                        if ">>>" in decoded_chunk:
                            break
                        # For verification/login commands, if we have a newline, we likely have the result
                        if "\n" in decoded_chunk:
                            # Check if we have more than just the prompt or if this is the result line
                            if len("".join(chunks).strip()) > 0:
                                # Wait a tiny bit for the prompt to follow
                                sock.settimeout(0.3)
                except socket.timeout:
                    pass
                
                response = "".join(chunks).strip()
                # Remove the prompt if it's there
                if response.endswith(">>>"):
                    response = response[:-3].strip()
                
                if not response:
                    print("📩 [DEBUG] OpenD: Command sent, but no direct response text returned. (Check OpenD console logs)")
                    return "Command sent (Check OpenD console for result)"
                
                print(f"📩 OpenD Full Response: {response}")
                return response
                
        except Exception as e:
            print(f"❌ Socket Error: {e}")
            import traceback
            traceback.print_exc()
            return f"Error: {e}"

    def close(self):
        if self.quote_ctx:
            self.quote_ctx.close()
            self.quote_ctx = None

# Singleton instance for the app
_provider = None

def get_moomoo_provider():
    global _provider
    if _provider is None:
        # Get host/port from env or default
        host = os.getenv("MOOMOO_OPEND_HOST", "127.0.0.1")
        port = int(os.getenv("MOOMOO_OPEND_PORT", 11111))
        _provider = MoomooOptionsProvider(host=host, port=port)
    return _provider
