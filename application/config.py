import json
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_JSON = PROJECT_DIR / "linkedin_results.json"
CONFIG_JSON = PROJECT_DIR / "configuration" / "config.json"
CHROME_PROFILE_DIR = PROJECT_DIR / "chrome_profile"

# Charge automatiquement un fichier .env local s'il existe (non versionné sur Git)
load_dotenv(PROJECT_DIR / ".env")


def _load_local_config_dict() -> dict:
    if CONFIG_JSON.exists():
        try:
            data = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


_LOCAL_CFG = _load_local_config_dict()

MONGO_URI = (
    os.getenv("MONGO_URI")
    or _LOCAL_CFG.get("mongo_uri")
    or "mongodb://localhost:27017/leadfeeder-social-accounts"
)
DB_NAME = os.getenv("DB_NAME") or _LOCAL_CFG.get("db_name") or "leadfeeder-social-accounts"
COLLECTION = os.getenv("COLLECTION") or _LOCAL_CFG.get("collection") or "adding_social_accounts"
CHECKPOINT_COLLECTION = (
    os.getenv("CHECKPOINT_COLLECTION")
    or _LOCAL_CFG.get("checkpoint_collection")
    or "linkedin_enrichment_progress"
)
CHECKPOINT_ID = (
    os.getenv("CHECKPOINT_ID")
    or _LOCAL_CFG.get("checkpoint_id")
    or "missing_linkedin_companies"
)
MONGO_BATCH_SIZE = int(
    os.getenv("MONGO_BATCH_SIZE")
    or _LOCAL_CFG.get("mongo_batch_size")
    or 25  # Taille de lot sécurisée pour éviter les timeouts réseau
)

LI_HOME_URL = "https://www.linkedin.com"
LI_FEED_URL = "https://www.linkedin.com/feed/"
LI_SEARCH_URL = "https://www.linkedin.com/search/results/companies/?keywords={query}"
LI_LOGIN_URL = "https://www.linkedin.com/login"
GOOGLE_SEARCH = "https://www.google.com/search?q={query}"

BLACKLIST_SLUGS = {
    "setup", "new", "about", "security", "careers", "press", "legal",
    "terms", "privacy", "help", "pulse", "feed", "search", "jobs",
    "learning", "premium", "recruiter", "talent", "ads", "mycompany",
    "showcase", "events", "school", "products", "checkpoint", "authwall",
    "login", "signup"
}

WAIT_PAGE = 8
WAIT_BETWEEN = 2.5


def load_results() -> dict:
    if OUTPUT_JSON.exists():
        try:
            return json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_results(data: dict) -> None:
    OUTPUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config() -> dict:
    return _load_local_config_dict()


def save_config(cfg: dict) -> None:
    CONFIG_JSON.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_JSON.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")