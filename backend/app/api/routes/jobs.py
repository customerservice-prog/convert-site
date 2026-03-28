from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app import config
from backend.app.api.deps import client_ip, error_payload, limiter
from backend.app.db import get_db
from backend.app.models import Job
from backend.app.repositories import job_repository
from backend.app.schemas.api import JobCreateRequest
from backend.app.services import errors, metadata_response, validation, ytdlp_service
from backend.app.services.job_runner import run_download_job
from backend.app.services import storage_service

logger = logging.getLogger(__name__)
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


def _human_status(job: Job) -> str:
    m = {
        "queued": "Queued",
        "downloading": "Downloading",
        "processing": "Processing",
        "completed": "Ready",
        "failed": "Failed",
        "expired": "Expired",
    }
    return m.get(job.status, job.status.title())


@router.post("/jobs")
@limiter.limit(config.RATE_LIMIT_JOBS)
def api_create_job(
    request: Request,
    body: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    url = body.url.strip()
    preset_early = metadata_response.resolve_preset(body.preset_key)
    if not preset_early and body.output_type not in ("video", "audio"):
        raise HTTPException(status_code=400, detail=error_payload("invalid_url", "Invalid output type."))

    ok, code = validation.validate_video_url(url)
    if not ok:
        raise HTTPException(status_code=400, detail=error_payload(code or "invalid_url"))

    if not storage_service.has_min_free_disk():
        logger.warning("job_rejected_disk_low ip=%s", client_ip(request))
        raise HTTPException(status_code=503, detail=error_payload("disk_full"))

    if job_repository.count_active_jobs(db) >= config.MAX_CONCURRENT_JOBS_GLOBAL:
        raise HTTPException(status_code=429, detail=error_payload("too_many_jobs"))

    ip = client_ip(request)
    if job_repository.count_active_jobs_for_ip(db, ip) >= config.MAX_CONCURRENT_JOBS_PER_IP:
        raise HTTPException(status_code=429, detail=error_payload("too_many_jobs"))

    try:
        info = ytdlp_service.extract_metadata(url)
    except Exception as exc:
        logger.info("job_metadata_preflight_failed %s", exc)
        raise HTTPException(status_code=400, detail=error_payload("metadata_failed")) from exc

    duration = info.get("duration")
    if duration is not None and duration > config.MAX_DURATION_SECONDS:
        raise HTTPException(status_code=400, detail=error_payload("duration_exceeded"))

    preset = preset_early
    if preset:
        fmt, out_type = preset
        output_type = out_type
    else:
        output_type = body.output_type
        fmt = body.format_id.strip() if body.format_id else ""
        if output_type == "audio":
            if not fmt or fmt.startswith("bestvideo"):
                fmt = "bestaudio/best"
        else:
            fmt = fmt or "bestvideo+bestaudio/best"

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    thumb = info.get("thumbnail")
    job = Job(
        id=job_id,
        source_url=url,
        client_ip=ip,
        output_type=output_type,
        format_id=fmt,
        status="queued",
        progress=0,
        stage_message="Waiting in queue…",
        title=info.get("title"),
        thumbnail_url=thumb if isinstance(thumb, str) else None,
    )
    job.submitted_at = now
    db.add(job)
    db.commit()
    logger.info("job_created id=%s ip=%s type=%s", job_id, ip, output_type)

    background_tasks.add_task(run_download_job, job_id)
    return {
        "job_id": job_id,
        "status": "queued",
        "poll_url": f"/api/jobs/{job_id}",
    }


@router.get("/jobs/{job_id}")
def api_job_status(job_id: str, db: Session = Depends(get_db)):
    if not validation.is_safe_job_id(job_id):
        raise HTTPException(status_code=400, detail=error_payload("job_not_found"))

    job = job_repository.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=error_payload("job_not_found"))

    job = _ensure_file_state(db, job)

    out: dict = {
        "job_id": job.id,
        "status": job.status,
        "status_label": _human_status(job),
        "progress": int(job.progress or 0),
        "title": job.title,
        "output_type": job.output_type,
        "thumbnail_url": job.thumbnail_url,
    }
    if job.stage_message:
        out["stage"] = job.stage_message
    if job.failure_reason_user or job.user_error_code:
        out["error"] = job.failure_reason_user or errors.user_message(job.user_error_code or "download_failed")
        if job.user_error_code:
            out["code"] = job.user_error_code
    if job.expires_at and job.status == "completed":
        out["expires_at"] = job.expires_at.isoformat()
    if job.status == "completed":
        out["download_url"] = f"/api/files/{job_id}"
        out["filename"] = job.output_filename
        out["file_size"] = job.file_size
    return out
