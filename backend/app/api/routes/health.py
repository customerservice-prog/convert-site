from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app import config
from backend.app.db import get_db
from backend.app.services import storage_service

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    from sqlalchemy import text

    db_ok = False
    disk_free = 0
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    try:
        disk_free = storage_service.free_disk_bytes()
    except OSError:
        pass
    healthy = db_ok and disk_free >= config.MIN_FREE_DISK_BYTES
    body = {
        "status": "ok" if healthy else "degraded",
        "checks": {
            "database": "ok" if db_ok else "error",
            "disk_free_bytes": disk_free,
            "min_free_bytes": config.MIN_FREE_DISK_BYTES,
        },
    }
    return JSONResponse(content=body, status_code=200 if healthy else 503)


@router.get("/live")
def live():
    return {"status": "live"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    from sqlalchemy import text

    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return JSONResponse(content={"status": "not_ready"}, status_code=503)
