"""Shared dependencies and helpers for API routes."""
from __future__ import annotations

import logging

from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.app import config
from backend.app.services import errors

logger = logging.getLogger("api")

limiter = Limiter(key_func=get_remote_address)


def error_payload(code: str, message: str | None = None) -> dict:
    return {"code": code, "message": message or errors.user_message(code)}


def client_ip(request: Request) -> str:
    if config.TRUST_PROXY:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()[:64]
    if request.client:
        return (request.client.host or "unknown")[:64]
    return "unknown"


def require_admin(request: Request) -> None:
    if not config.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin API disabled")
    key = request.headers.get("x-admin-key")
    if key != config.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
