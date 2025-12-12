
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CANONICAL_DIR = DATA_DIR / "canonical"
DB_PATH = BASE_DIR / "database" / "research.db"

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Local LLM
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL") or "http://localhost:1234/v1"

# Ingestion Settings
PREFER_NATIVE_TEXT = True
