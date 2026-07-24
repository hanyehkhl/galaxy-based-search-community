import os
from pathlib import Path

from dotenv import load_dotenv

# بارگذاری فایل .env (در کنار config.py)
load_dotenv(Path(__file__).parent / ".env")


def _pick(*keys, default=""):
    """اولین env variable موجود از لیست را برمی‌گرداند، وگرنه default"""
    for k in keys:
        v = os.getenv(k)
        if v:
            return v
    return default


# پارامترهای الگوریتم GbSA
population_size = int(os.getenv("GBSA_POPULATION_SIZE", "20"))
iterations = int(os.getenv("GBSA_ITERATIONS", "50"))
dataset_path = os.getenv("GBSA_DATASET_PATH", "data/karate.gml")

# --- تنظیمات LLM ---
# اولویت: GBSA_LLM_* (OS env) ← GAPGPT_* (.env) ← پیش‌فرض
# اگر provider=ollama باشد، مقادیر GAPGPT از .env نادیده گرفته می‌شوند

llm_provider = os.getenv("GBSA_LLM_PROVIDER") or os.getenv("GAPGPT_PROVIDER") or ""

if llm_provider == "ollama":
    # فقط GBSA_LLM_* (OS env) + پیش‌فرض‌های Ollama لوکال
    llm_model = os.getenv("GBSA_LLM_MODEL") or "llama3.2"
    llm_api_key = os.getenv("GBSA_LLM_API_KEY") or "ollama"
    llm_base_url = os.getenv("GBSA_LLM_BASE_URL") or "http://localhost:11434/v1"
    llm_timeout = int(os.getenv("GBSA_LLM_REQUEST_TIMEOUT", "60"))
    llm_enabled = os.getenv("GBSA_LLM_ENABLED", "true").lower() in ("1", "true", "yes")
else:
    # GAPGPT (AvalAI / OpenAI-compatible): GBSA_LLM_* ← GAPGPT_* ← پیش‌فرض
    llm_model = _pick("GBSA_LLM_MODEL", "GAPGPT_MODEL", default="deepseek-v4-flash")
    llm_api_key = _pick("GBSA_LLM_API_KEY", "GAPGPT_API_KEY", default="")
    llm_base_url = _pick("GBSA_LLM_BASE_URL", "GAPGPT_BASE_URL", default="")
    llm_timeout = int(_pick("GBSA_LLM_REQUEST_TIMEOUT", "GAPGPT_REQUEST_TIMEOUT", default="60"))
    llm_enabled = _pick("GBSA_LLM_ENABLED", "GAPGPT_ENABLED", default="true").lower() in ("1", "true", "yes")
