from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.api.deps import error_payload
from backend.app.db import get_db
from backend.app.models import Job
from backend.app.repositories import job_repository
from backend.app.services import errors, storage_service, validation

router = APIRouter()


def _ensure_file_state(db: Session, job: Job) -> Job:
    if job.status != "completed" or not job.output_path_relative:
        return job
    path = storage_service.downloads_base() / job.output_path_relative
    if path.is_file():
        return job
    job.status = "expired"
    job.user_error_code = "file_expired"
    job.failure_reason_user = errors.user_message("file_expired")
    db.add(job)
    db.commit()
    return job


@router.get("/files/{job_id}")
def api_download_file(job_id: str, db: Session = Depends(get_db)):
    if not validation.is_safe_job_id(job_id):
        raise HTTPException(status_code=400, detail=error_payload("job_not_found"))

    job = job_repository.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=error_payload("job_not_found"))

    job = _ensure_file_state(db, job)

    if job.status == "expired":
        raise HTTPException(status_code=410, detail=error_payload("file_expired"))

    if job.status != "completed":
        raise HTTPException(status_code=409, detail=error_payload("server_busy", "File not ready yet."))

    if not job.output_path_relative:
        raise HTTPException(status_code=404, detail=error_payload("file_missing"))

    path = storage_service.downloads_base() / job.output_path_relative
    if not path.is_file() or path.stat().st_size <= 0:
        raise HTTPException(status_code=404, detail=error_payload("file_missing"))

    fname = job.output_filename or path.name
    media = storage_service.media_type_for_ext(path.suffix)
    return FileResponse(path, filename=fname, media_type=media)
