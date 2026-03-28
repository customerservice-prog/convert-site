"""Application configuration from environment variables."""
from __future__ import annotations

import os
from pathlib import Path


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


# Repository root (convert-site/) — backend/app/config.py → parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGAL_DIR = PROJECT_ROOT / "legal"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

APP_ENV = os.environ.get("APP_ENV", "development")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data")).resolve()
DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{DATA_DIR / 'jobs.db'}"
DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", "./downloads")).resolve()

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")

_cors = os.environ.get("CORS_ALLOWED_ORIGINS", os.environ.get("CORS_ORIGINS", "*"))
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors.split(",") if o.strip()]

FILE_EXPIRY_MINUTES = _int("FILE_EXPIRY_MINUTES", 60)
QUEUED_JOB_TTL_MINUTES = _int("QUEUED_JOB_TTL_MINUTES", 30)

MAX_CONCURRENT_JOBS_GLOBAL = _int("MAX_CONCURRENT_JOBS_GLOBAL", 3)
MAX_CONCURRENT_JOBS_PER_IP = _int("MAX_CONCURRENT_JOBS_PER_IP", 2)
MAX_DURATION_SECONDS = _int("MAX_DURATION_SECONDS", 4 * 60 * 60)
MAX_FILE_BYTES = _int("MAX_FILE_BYTES", 3 * 1024 * 1024 * 1024)
MIN_FREE_DISK_BYTES = _int("MIN_FREE_DISK_BYTES", 512 * 1024 * 1024)

RATE_LIMIT_INFO = os.environ.get("RATE_LIMIT_INFO", "30/minute")
RATE_LIMIT_JOBS = os.environ.get("RATE_LIMIT_JOBS", "8/hour")

SUPPORTED_URL_HOSTS = [
    h.strip().lower()
    for h in os.environ.get(
        "SUPPORTED_URL_HOSTS",
        "youtube.com,www.youtube.com,youtu.be,m.youtube.com,music.youtube.com",
    ).split(",")
    if h.strip()
]

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
TRUST_PROXY = _bool("TRUST_PROXY", False)
