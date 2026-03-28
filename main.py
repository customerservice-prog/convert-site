"""
FastAPI API + Celery workers for YouTube download (yt-dlp + FFmpeg).
Endpoints: POST /metadata, POST /download/start, GET /download/status/:id, GET /download/file/:id
"""
from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from celery import Celery, states
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import yt_dlp

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", "./downloads")).resolve()
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

celery_app = Celery("convert_site", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)

app = FastAPI(title="YouTube Downloader API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _safe_task_dir(task_id: str) -> Path:
    if not task_id or re.search(r"[./\\]", task_id):
        raise HTTPException(status_code=400, detail="Invalid task id")
    d = (DOWNLOAD_DIR / task_id).resolve()
    try:
        d.relative_to(DOWNLOAD_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task id") from None
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


@celery_app.task(bind=True, name="download_video")
def download_video_task(self, url: str, format_id: str | None) -> dict[str, Any]:
    task_id = self.request.id
    if not task_id:
        raise RuntimeError("Missing Celery task id")
    task_dir = (DOWNLOAD_DIR / task_id).resolve()
    task_dir.mkdir(parents=True, exist_ok=True)
    _write_meta(task_dir)

    fmt = format_id or "bestvideo+bestaudio/best"
    out_template = str(task_dir / "output.%(ext)s")

    def progress_hook(d: dict[str, Any]) -> None:
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes") or 0
            pct = (downloaded / total * 100.0) if total else None
            self.update_state(
                state="PROGRESS",
                meta={
                    "progress": round(pct, 2) if pct is not None else None,
                    "message": d.get("_percent_str", "Downloading…"),
                    "phase": "download",
                },
            )
        elif d["status"] == "finished" and d.get("filename"):
            self.update_state(
                state="PROGRESS",
                meta={"progress": 95.0, "message": "Merging with FFmpeg…", "phase": "merge"},
            )

    ydl_opts: dict[str, Any] = {
        "format": fmt,
        "merge_output_format": "mp4",
        "outtmpl": out_template,
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
    }

    self.update_state(
        state=states.STARTED,
        meta={"progress": 0.0, "message": "Starting…", "phase": "start"},
    )

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as exc:
        shutil.rmtree(task_dir, ignore_errors=True)
        self.update_state(state=states.FAILURE, meta={"error": str(exc)})
        raise

    out = _find_output_file(task_dir)
    if not out or not out.is_file():
        shutil.rmtree(task_dir, ignore_errors=True)
        raise RuntimeError("Download finished but output file was not found")

    return {"filename": out.name, "path": str(out)}


class MetadataRequest(BaseModel):
    url: str = Field(..., min_length=1)


class DownloadStartRequest(BaseModel):
    url: str = Field(..., min_length=1)
    format_id: str | None = None


@app.get("/")
def serve_index():
    index_path = Path(__file__).resolve().parent / "index.html"
    if not index_path.is_file():
        return JSONResponse({"detail": "index.html not found"}, status_code=404)
    return FileResponse(index_path, media_type="text/html")


@app.post("/metadata")
def metadata(body: MetadataRequest):
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

    formats_raw = info.get("formats") or []
    formats_out: list[dict[str, Any]] = []
    for f in formats_raw:
        fid = f.get("format_id")
        if not fid:
            continue
        formats_out.append(
            {
                "format_id": fid,
                "ext": f.get("ext"),
                "resolution": f.get("resolution") or f.get("format_note"),
                "vcodec": f.get("vcodec"),
                "acodec": f.get("acodec"),
                "filesize": f.get("filesize") or f.get("filesize_approx"),
                "format_note": f.get("format_note"),
            }
        )

    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader"),
        "webpage_url": info.get("webpage_url") or url,
        "formats": formats_out,
    }


@app.post("/download/start")
def download_start(body: DownloadStartRequest):
    url = body.url.strip()
    async_result = download_video_task.delay(url, body.format_id)
    return {"id": async_result.id}


@app.get("/download/status/{task_id}")
def download_status(task_id: str):
    _safe_task_dir(task_id)
    async_result = celery_app.AsyncResult(task_id)
    state = async_result.state
    meta = async_result.info if isinstance(async_result.info, dict) else {}

    if state == states.PENDING:
        return {
            "state": state,
            "progress": None,
            "message": "Queued…",
            "error": None,
            "filename": None,
        }
    if state == states.STARTED or state == "PROGRESS":
        return {
            "state": state,
            "progress": meta.get("progress"),
            "message": meta.get("message") or "Working…",
            "error": None,
            "filename": None,
            "phase": meta.get("phase"),
        }
    if state == states.SUCCESS:
        result = async_result.result
        filename = None
        if isinstance(result, dict):
            filename = result.get("filename")
        task_dir = _safe_task_dir(task_id)
        out = _find_output_file(task_dir)
        if out:
            filename = out.name
        return {
            "state": state,
            "progress": 100.0,
            "message": "Complete",
            "error": None,
            "filename": filename,
        }
    if state == states.FAILURE:
        err = "Task failed"
        info = async_result.info
        if isinstance(info, dict):
            err = str(info.get("error", err))
        elif info is not None:
            err = str(info)
        return JSONResponse(
            status_code=200,
            content={
                "state": state,
                "progress": None,
                "message": "Failed",
                "error": err,
                "filename": None,
            },
        )

    return {
        "state": state,
        "progress": meta.get("progress"),
        "message": meta.get("message"),
        "error": meta.get("error"),
        "filename": None,
    }


@app.get("/download/file/{task_id}")
def download_file(task_id: str):
    task_dir = _safe_task_dir(task_id)
    async_result = celery_app.AsyncResult(task_id)
    if async_result.state != states.SUCCESS:
        raise HTTPException(status_code=409, detail="Download not ready or failed")
    path = _find_output_file(task_dir)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path,
        filename=path.name,
        media_type="video/mp4",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), reload=False)
