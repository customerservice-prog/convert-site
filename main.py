"""
Launch-ready video download API: FastAPI + SQLite jobs + background tasks.
Endpoints: POST /api/info, POST /api/jobs, GET /api/jobs/{id}, GET /api/files/{id}
"""
from __future__ import annotations

import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

import config
from db import get_db, init_db
from models import Job
from services import errors, validation
from services import job_repository
from services import storage_service
from services import ytdlp_service
from services.job_runner import run_download_job

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("app")


def _client_ip(request: Request) -> str:
    if config.TRUST_PROXY:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()[:64]
    if request.client:
        return (request.client.host or "unknown")[:64]
    return "unknown"


limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info("app_start env=%s download_dir=%s", config.APP_ENV, config.DOWNLOAD_DIR)
    yield
    logger.info("app_stop")


app = FastAPI(title="Video Downloader API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_payload(code: str, message: str | None = None) -> dict:
    return {"code": code, "message": message or errors.user_message(code)}


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):  # noqa: ARG001
    logger.exception("unhandled_error path=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": _error_payload("server_busy")},
    )


class InfoRequest(BaseModel):
    url: str = Field(..., min_length=1)


class JobCreateRequest(BaseModel):
    url: str = Field(..., min_length=1)
    format_id: str = Field(default="bestvideo+bestaudio/best")
    output_type: str = Field(default="video")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    from sqlalchemy import text

    db_ok = False
    disk_free = 0
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.warning("health_db_check_failed %s", exc)
    try:
        disk_free = storage_service.free_disk_bytes()
    except OSError as exc:
        logger.warning("health_disk_check_failed %s", exc)
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


@app.get("/")
def serve_index():
    from pathlib import Path

    index_path = Path(__file__).resolve().parent / "index.html"
    if not index_path.is_file():
        return JSONResponse({"detail": "index.html not found"}, status_code=404)
    return FileResponse(index_path, media_type="text/html")


@app.get("/legal/{page}")
def serve_legal(page: str):
    from pathlib import Path

    if page not in ("terms", "privacy"):
        raise HTTPException(status_code=404, detail="Not found")
    p = Path(__file__).resolve().parent / "legal" / f"{page}.html"
    if not p.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(p, media_type="text/html")


@app.post("/api/info")
@limiter.limit(config.RATE_LIMIT_INFO)
def api_info(request: Request, body: InfoRequest, db: Session = Depends(get_db)):  # noqa: ARG001
    ok, code = validation.validate_video_url(body.url)
    if not ok:
        raise HTTPException(status_code=400, detail=_error_payload(code or "invalid_url"))

    try:
        info = ytdlp_service.extract_metadata(body.url.strip())
    except Exception as exc:
        logger.info("metadata_failed domain=%s err=%s", body.url[:60], exc)
        raise HTTPException(
            status_code=400,
            detail=_error_payload("metadata_failed", errors.user_message("metadata_failed")),
        ) from exc

    return {
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "formats": ytdlp_service.formats_for_response(info),
    }


@app.post("/api/jobs")
@limiter.limit(config.RATE_LIMIT_JOBS)
def api_create_job(
    request: Request,
    body: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    url = body.url.strip()
    if body.output_type not in ("video", "audio"):
        raise HTTPException(status_code=400, detail=_error_payload("invalid_url", "Invalid output type."))

    ok, code = validation.validate_video_url(url)
    if not ok:
        raise HTTPException(status_code=400, detail=_error_payload(code or "invalid_url"))

    if not storage_service.has_min_free_disk():
        logger.warning("job_rejected_disk_low ip=%s", _client_ip(request))
        raise HTTPException(status_code=503, detail=_error_payload("disk_full"))

    if job_repository.count_active_jobs(db) >= config.MAX_CONCURRENT_JOBS_GLOBAL:
        raise HTTPException(status_code=429, detail=_error_payload("too_many_jobs"))

    ip = _client_ip(request)
    if job_repository.count_active_jobs_for_ip(db, ip) >= config.MAX_CONCURRENT_JOBS_PER_IP:
        raise HTTPException(status_code=429, detail=_error_payload("too_many_jobs"))

    try:
        info = ytdlp_service.extract_metadata(url)
    except Exception as exc:
        logger.info("job_metadata_preflight_failed %s", exc)
        raise HTTPException(
            status_code=400,
            detail=_error_payload("metadata_failed"),
        ) from exc

    duration = info.get("duration")
    if duration is not None and duration > config.MAX_DURATION_SECONDS:
        raise HTTPException(status_code=400, detail=_error_payload("duration_exceeded"))

    fmt = body.format_id.strip() if body.format_id else ""
    if body.output_type == "audio":
        if not fmt or fmt.startswith("bestvideo"):
            fmt = "bestaudio/best"
    else:
        fmt = fmt or "bestvideo+bestaudio/best"

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    job = Job(
        id=job_id,
        source_url=url,
        client_ip=ip,
        output_type=body.output_type,
        format_id=fmt,
        status="queued",
        progress=0,
        stage_message="Queued…",
        title=info.get("title"),
    )
    job.submitted_at = now
    db.add(job)
    db.commit()
    logger.info("job_created id=%s ip=%s type=%s", job_id, ip, body.output_type)

    background_tasks.add_task(run_download_job, job_id)
    return {"job_id": job_id}


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


@app.get("/api/jobs/{job_id}")
def api_job_status(job_id: str, db: Session = Depends(get_db)):
    if not validation.is_safe_job_id(job_id):
        raise HTTPException(status_code=400, detail=_error_payload("job_not_found"))

    job = job_repository.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=_error_payload("job_not_found"))

    job = _ensure_file_state(db, job)

    out: dict = {
        "status": job.status,
        "progress": int(job.progress or 0),
    }
    if job.stage_message:
        out["stage"] = job.stage_message
    if job.failure_reason_user or job.user_error_code:
        out["error"] = job.failure_reason_user or errors.user_message(job.user_error_code or "download_failed")
        if job.user_error_code:
            out["code"] = job.user_error_code
    if job.expires_at and job.status == "completed":
        out["expires_at"] = job.expires_at.isoformat()
    return out


@app.get("/api/files/{job_id}")
def api_download_file(job_id: str, db: Session = Depends(get_db)):
    if not validation.is_safe_job_id(job_id):
        raise HTTPException(status_code=400, detail=_error_payload("job_not_found"))

    job = job_repository.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=_error_payload("job_not_found"))

    job = _ensure_file_state(db, job)

    if job.status == "expired":
        raise HTTPException(status_code=410, detail=_error_payload("file_expired"))

    if job.status != "completed":
        raise HTTPException(status_code=409, detail=_error_payload("server_busy", "File not ready yet."))

    if not job.output_path_relative:
        raise HTTPException(status_code=404, detail=_error_payload("file_missing"))

    path = storage_service.downloads_base() / job.output_path_relative
    if not path.is_file() or path.stat().st_size <= 0:
        raise HTTPException(status_code=404, detail=_error_payload("file_missing"))

    fname = job.output_filename or path.name
    media = storage_service.media_type_for_ext(path.suffix)
    return FileResponse(
        path,
        filename=fname,
        media_type=media,
    )


def _require_admin(request: Request) -> None:
    if not config.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin API disabled")
    key = request.headers.get("x-admin-key")
    if key != config.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/api/admin/jobs")
def api_admin_jobs(request: Request, db: Session = Depends(get_db), limit: int = 50):
    _require_admin(request)
    limit = max(1, min(limit, 200))
    rows = job_repository.list_recent_jobs(db, limit)
    out = []
    for j in rows:
        from urllib.parse import urlparse

        dom = None
        try:
            dom = urlparse(j.source_url).netloc
        except Exception:
            dom = "unknown"
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), reload=False)
