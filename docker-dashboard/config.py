import os
from pathlib import Path

# Base Directory of the app
BASE_DIR = Path(__file__).resolve().parent

# Data directory for persistent storage (e.g. SQLite database, custom connectors)
# In Docker, this will point to /app/data, but locally it defaults to a 'data' directory in the project root
DATA_DIR_STR = os.getenv("DATA_DIR", str(BASE_DIR / "data"))
DATA_DIR = Path(DATA_DIR_STR)

# Ensure the data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database path
DB_PATH = DATA_DIR / "sleep_study.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Connectors Directories
# 1. Custom connectors directory in the persistent mount (e.g. /app/data/connectors)
CUSTOM_CONNECTORS_DIR = DATA_DIR / "connectors"
CUSTOM_CONNECTORS_DIR.mkdir(parents=True, exist_ok=True)

# 2. Native connectors directory inside the app (e.g. /app/connectors)
NATIVE_CONNECTORS_DIR = BASE_DIR / "connectors"
NATIVE_CONNECTORS_DIR.mkdir(parents=True, exist_ok=True)

# Application Port
PORT = int(os.getenv("PORT", 8000))
