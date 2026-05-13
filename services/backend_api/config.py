import os
import sys
import warnings
from pathlib import Path
from dotenv import load_dotenv

# Suppress the specific Google GenerativeAI deprecation warning to clean up logs
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

# 1. Project Root Setup (Must be first)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parent

for p in [str(PROJECT_ROOT), str(BACKEND_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p) # Insert at 0 to ensure priority

# 2. Internal Imports
from internal.db_client.database import StockDB
import options_synth
import schwab_market_data
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
import google.generativeai as genai

# 3. Load Env
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# 4. Auth Config
SECRET_KEY = os.getenv("SECRET_KEY", "brstock_super_secret_key_9988")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# 5. AI Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY and GEMINI_API_KEY.strip():
    genai.configure(api_key=GEMINI_API_KEY)

LOCAL_AI_URL = os.getenv("LOCAL_AI_URL", "http://192.168.0.162:8912/v1/chat/completions")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "minimax/minimax-m2.5:free")

# 6. DB & Engines
db = StockDB()
synth_engine = options_synth.OptionSynth()

def get_moomoo_provider():
    import options_moomoo
    return options_moomoo.get_moomoo_provider()

def get_schwab_provider():
    return schwab_market_data.get_schwab_provider()
