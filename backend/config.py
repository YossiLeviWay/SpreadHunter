import os
from dotenv import load_dotenv

load_dotenv()

# Massive.com API credentials
MASSIVE_API_KEY = os.getenv("MASSIVE_API_KEY", "62VikDmIHlzWI2V7ddPQaUdMXT3YHpjJ")
MASSIVE_BASE_URL = os.getenv("MASSIVE_BASE_URL", "https://api.massive.com")

# DTE range for option screening
MIN_DTE = int(os.getenv("MIN_DTE", "20"))
MAX_DTE = int(os.getenv("MAX_DTE", "45"))

# Calculation parameters
RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.052"))  # ~5.2% as of 2024

# Cache TTL in seconds (5 minutes)
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))
