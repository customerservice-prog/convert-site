"""URL and input validation."""
from __future__ import annotations

import re
from urllib.parse import urlparse

import config


def _normalize_host(netloc: str) -> str:
    host = netloc.split("@")[-1].split(":")[0].lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _host_allowed(host: str) -> bool:
    for allowed in config.SUPPORTED_URL_HOSTS:
        a = allowed.lower().strip()
        if not a:
            continue
        if host == a:
            return True
        if host.endswith("." + a):
            return True
    return False


def validate_video_url(url: str) -> tuple[bool, str | None]:
    """
    Returns (ok, error_code).
    error_code keys match services.errors.USER_MESSAGES.
    """
    raw = (url or "").strip()
    if len(raw) < 10 or len(raw) > 2048:
        return False, "invalid_url"

    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        return False, "invalid_url"
    if not parsed.netloc:
        return False, "invalid_url"

    host = _normalize_host(parsed.netloc)
    if not _host_allowed(host):
        return False, "unsupported_source"

    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", raw):
        return False, "invalid_url"

    return True, None


def is_safe_job_id(job_id: str) -> bool:
    if not job_id or len(job_id) > 64:
        return False
    return bool(re.fullmatch(r"[0-9a-fA-F-]{36}", job_id))
