
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

# OpenRouter (additional provider)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Local LLM
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL")

# Verification models (3 diverse models for consensus)
VERIFICATION_MODELS = [
    "openai/gpt-oss-120b:free",
    "mistralai/devstral-2512:free",
    "xiaomi/mimo-v2-flash:free",
]

# Models per task (used by OpenRouter for non-verification tasks)
MODELS = {
    "verification": VERIFICATION_MODELS[0],  # Default single model
    "research": "xiaomi/mimo-v2-flash:free",
    "summarization": "xiaomi/mimo-v2-flash:free",
    "ocr": "nvidia/nemotron-nano-12b-v2-vl:free",
}

# Ingestion Settings
PREFER_NATIVE_TEXT = True
