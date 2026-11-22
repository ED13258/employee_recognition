from pathlib import Path
from typing import Any, Dict, Optional
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR   = BASE_DIR / "webClient" / "www" / "static"
TEMPLATE_DIR = BASE_DIR / "webClient" / "www" / "template"
INDEX_HTML   = BASE_DIR / "webClient" / "www" / "index.html"

class Settings:
    POSTGRES_URI = os.environ.get(
        "POSTGRES_URI",
        "postgresql+asyncpg://recognition:Damn13258@localhost:5432/recognition_db"
    )
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))