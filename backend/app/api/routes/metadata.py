from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app import config
from backend.app.api.deps import error_payload, limiter
from backend.app.db import get_db
from backend.app.schemas.api import InfoRequest
from backend.app.services import errors, validation, ytdlp_service
from backend.app.services.metadata_response import build_metadata_payload

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/info")
@limiter.limit(config.RATE_LIMIT_INFO)
def api_info(request: Request, body: InfoRequest, db: Session = Depends(get_db)):  # noqa: ARG001
    ok, code = validation.validate_video_url(body.url)
    if not ok:
        raise HTTPException(status_code=400, detail=error_payload(code or "invalid_url"))

    try:
        info = ytdlp_service.extract_metadata(body.url.strip())
    except Exception as exc:
        logger.info("metadata_failed err=%s", exc)
        raise HTTPException(
            status_code=400,
            detail=error_payload("metadata_failed", errors.user_message("metadata_failed")),
        ) from exc

    if not info.get("id") and not info.get("title"):
        raise HTTPException(status_code=400, detail=error_payload("metadata_failed"))

    return build_metadata_payload(body.url.strip(), info)
