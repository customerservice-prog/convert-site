"""
Video download API (MVP): FastAPI + BackgroundTasks, yt-dlp + FFmpeg.
Routes: POST /api/info, POST /api/jobs, GET /api/jobs/{id}, GET /api/files/{id}
"""
from __future__ import annotations

import json
import os
import re
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yt_dlp
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", "./downloads")).resolve()
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

_jobs_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}

app = FastAPI(title="Video Downloader API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _job_update(job_id: str, **kwargs: Any) -> None:
    with _jobs_lock:
        if job_id not in _jobs:
            _jobs[job_id] = {}
        _jobs[job_id].update(kwargs)


def _job_get(job_id: str) -> dict[str, Any] | None:
    with _jobs_lock:
        j = _jobs.get(job_id)
        return dict(j) if j else None


def _safe_job_dir(job_id: str) -> Path:
    if not job_id or re.search(r"[./\\]", job_id):
        raise HTTPException(status_code=400, detail="Invalid job id")
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job id") from None
    d = (DOWNLOAD_DIR / job_id).resolve()
    try:
        d.relative_to(DOWNLOAD_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job id") from None
    return d


def _write_meta(task_dir: Path) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    meta = {"started_at": datetime.now(timezone.utc).isoformat()}
    (task_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _find_output_file(task_dir: Path) -> Path | None:
    if not task_dir.is_dir():
        return None
    for name in ("output.mp4", "output.mkv", "output.webm"):
        p = task_dir / name
        if p.is_file():
            return p
    for p in sorted(task_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
        return p
    return None


def _run_download_job(job_id: str, url: str, format_id: str) -> None:
    task_dir = (DOWNLOAD_DIR / job_id).resolve()
    task_dir.mkdir(parents=True, exist_ok=True)
    _write_meta(task_dir)

    fmt = format_id.strip() if format_id else "bestvideo+bestaudio/best"
    out_template = str(task_dir / "output.%(ext)s")

    def progress_hook(d: dict[str, Any]) -> None:
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes") or 0
            pct = int((downloaded / total) * 85) if total else 10
            pct = max(5, min(85, pct))
            _job_update(job_id, status="downloading", progress=pct)
        elif d["status"] == "finished":
            _job_update(job_id, status="processing", progress=90)

    ydl_opts: dict[str, Any] = {
        "format": fmt,
        "merge_output_format": "mp4",
        "outtmpl": out_template,
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
    }

    _job_update(job_id, status="downloading", progress=1)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as exc:
        shutil.rmtree(task_dir, ignore_errors=True)
        _job_update(job_id, status="failed", progress=0, error=str(exc))
        return

    out = _find_output_file(task_dir)
    if not out or not out.is_file():
        shutil.rmtree(task_dir, ignore_errors=True)
        _job_update(job_id, status="failed", progress=0, error="Output file not found after download")
        return

    _job_update(job_id, status="completed", progress=100, filename=out.name)


class InfoRequest(BaseModel):
    url: str = Field(..., min_length=1)


class JobCreateRequest(BaseModel):
    url: str = Field(..., min_length=1)
    format_id: str = Field(default="bestvideo+bestaudio")


@app.get("/")
def serve_index():
    index_path = Path(__file__).resolve().parent / "index.html"
    if not index_path.is_file():
        return JSONResponse({"detail": "index.html not found"}, status_code=404)
    return FileResponse(index_path, media_type="text/html")


@app.post("/api/info")
def api_info(body: InfoRequest):
    url = body.url.strip()
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not info:
        raise HTTPException(status_code=400, detail="No metadata returned")

    formats_out: list[dict[str, Any]] = []
    for f in info.get("formats") or []:
        fid = f.get("format_id")
        if not fid:
            continue
        formats_out.append(
            {
                "format_id": fid,
                "resolution": f.get("resolution") or f.get("format_note"),
                "ext": f.get("ext"),
                "filesize": f.get("filesize") or f.get("filesize_approx"),
            }
        )

    return {
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "formats": formats_out,
    }


@app.post("/api/jobs")
def api_create_job(body: JobCreateRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _job_update(
        job_id,
        status="queued",
        progress=0,
        url=body.url.strip(),
        format_id=body.format_id,
        error=None,
        filename=None,
    )
    background_tasks.add_task(
        _run_download_job,
        job_id,
        body.url.strip(),
        body.format_id,
    )
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def api_job_status(job_id: str):
    _safe_job_dir(job_id)
    job = _job_get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    out: dict[str, Any] = {
        "status": job.get("status", "queued"),
        "progress": int(job.get("progress") or 0),
    }
    if job.get("error"):
        out["error"] = job["error"]
    return out


@app.get("/api/files/{job_id}")
def api_download_file(job_id: str):
    task_dir = _safe_job_dir(job_id)
    job = _job_get(job_id)
    if not job or job.get("status") != "completed":
        raise HTTPException(status_code=409, detail="File not ready")
    path = _find_output_file(task_dir)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    name = job.get("filename") or path.name
    return FileResponse(path, filename=name, media_type="video/mp4")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), reload=False)
