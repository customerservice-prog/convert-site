from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import require_admin
from backend.app.db import get_db
from backend.app.repositories import job_repository
from backend.app.services import storage_service

router = APIRouter()


@router.get("/admin/jobs")
def api_admin_jobs(request: Request, db: Session = Depends(get_db), limit: int = 50):
    require_admin(request)
    limit = max(1, min(limit, 200))
    rows = job_repository.list_recent_jobs(db, limit)
    out = []
    for j in rows:
        dom = "unknown"
        try:
            dom = urlparse(j.source_url).netloc
        except Exception:
            pass
        out.append(
            {
                "id": j.id,
                "status": j.status,
                "progress": j.progress,
                "submitted_at": j.submitted_at.isoformat() if j.submitted_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "expires_at": j.expires_at.isoformat() if j.expires_at else None,
                "source_domain": dom,
                "output_type": j.output_type,
                "file_size": j.file_size,
                "user_error_code": j.user_error_code,
                "failure_reason_user": j.failure_reason_user,
            }
        )
    return {"jobs": out, "disk_free_bytes": storage_service.free_disk_bytes()}
