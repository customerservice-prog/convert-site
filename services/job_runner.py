"""
Background download pipeline: yt-dlp + verification + DB updates.
"""
from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config
from db import SessionLocal, write_lock
from models import Job
from services import errors, storage_service, ytdlp_service
from services.job_repository import mark_job_completed, mark_job_failed, touch_job_started, update_job_fields

logger = logging.getLogger(__name__)


def _write_meta_json(task_dir: Path) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    meta = {"started_at": datetime.now(timezone.utc).isoformat()}
    (task_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _find_output_file(task_dir: Path, output_type: str) -> Path | None:
    if not task_dir.is_dir():
        return None
    if output_type == "audio":
        for name in ("output.m4a", "output.mp3", "output.opus", "output.webm"):
            p = task_dir / name
            if p.is_file() and p.stat().st_size > 0:
                return p
        for p in sorted(task_dir.glob("*.m4a"), key=lambda x: x.stat().st_mtime, reverse=True):
            if p.stat().st_size > 0:
                return p
    for name in ("output.mp4", "output.mkv", "output.webm"):
        p = task_dir / name
        if p.is_file() and p.stat().st_size > 0:
            return p
    for p in sorted(task_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.stat().st_size > 0:
            return p
    return None


def run_download_job(job_id: str) -> None:
    with write_lock:
        db = SessionLocal()
        try:
            row = db.get(Job, job_id)
            if not row:
                logger.error("job_missing id=%s", job_id)
                return
            url = row.source_url
            format_id = row.format_id
            output_type = row.output_type or "video"
        finally:
            db.close()

    task_dir = storage_service.job_dir(job_id)
    try:
        task_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        logger.exception("job_dir_create_failed id=%s", job_id)
        mark_job_failed(
            job_id,
            user_code="download_failed",
            user_msg=errors.user_message("download_failed"),
            internal=str(exc),
        )
        return

    _write_meta_json(task_dir)
    touch_job_started(job_id)

    def progress_hook(d: dict[str, Any]) -> None:
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes") or 0
            pct = int((downloaded / total) * 85) if total else 10
            pct = max(5, min(85, pct))
            update_job_fields(
                job_id,
                status="downloading",
                progress=pct,
                stage_message=d.get("_percent_str") or "Downloading…",
            )
        elif d.get("status") == "finished":
            update_job_fields(
                job_id,
                status="processing",
                progress=90,
                stage_message="Muxing / encoding…",
            )

    try:
        ytdlp_service.download_to_dir(
            url,
            format_id,
            task_dir,
            output_type=output_type,
            progress_hook=progress_hook,
        )
    except Exception as exc:
        logger.exception("ytdlp_failed id=%s", job_id)
        shutil.rmtree(task_dir, ignore_errors=True)
        mark_job_failed(
            job_id,
            user_code="download_failed",
            user_msg=errors.user_message("download_failed"),
            internal=str(exc),
        )
        return

    out = _find_output_file(task_dir, output_type)
    if not out or not out.is_file():
        shutil.rmtree(task_dir, ignore_errors=True)
        mark_job_failed(
            job_id,
            user_code="processing_failed",
            user_msg=errors.user_message("processing_failed"),
            internal="Output file not found or empty after download",
        )
        return

    size = out.stat().st_size
    if size <= 0:
        shutil.rmtree(task_dir, ignore_errors=True)
        mark_job_failed(
            job_id,
            user_code="processing_failed",
            user_msg=errors.user_message("processing_failed"),
            internal="Output file size is zero",
        )
        return

    if size > config.MAX_FILE_BYTES:
        shutil.rmtree(task_dir, ignore_errors=True)
        mark_job_failed(
            job_id,
            user_code="download_failed",
            user_msg="File exceeded the maximum allowed size.",
            internal=f"size={size}",
        )
        return

    rel = f"{job_id}/{out.name}"
    title = None
    with write_lock:
        db = SessionLocal()
        try:
            r = db.get(Job, job_id)
            if r:
                title = r.title
        finally:
            db.close()

    disp_name = storage_service.content_disposition_filename(
        storage_service.sanitize_filename_stem(title),
        out.suffix.lstrip(".") or ("m4a" if output_type == "audio" else "mp4"),
    )

    mark_job_completed(
        job_id,
        relative_path=rel,
        filename=disp_name,
        file_size=size,
        title=title,
    )
    logger.info("job_complete id=%s bytes=%s", job_id, size)
