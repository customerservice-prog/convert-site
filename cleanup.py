"""
Remove expired download folders and sync job rows in SQLite.
Run frequently via cron / Task Scheduler:  python cleanup.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import config
from db import SessionLocal, init_db
from models import Job
from sqlalchemy import select

import services.storage_service as storage

DOWNLOAD_DIR = storage.downloads_base()
TTL_SECONDS = int(os.environ.get("DOWNLOAD_TTL_SECONDS", str(config.FILE_EXPIRY_MINUTES * 60)))
QUEUED_TTL_SECONDS = int(os.environ.get("QUEUED_JOB_TTL_SECONDS", str(config.QUEUED_JOB_TTL_MINUTES * 60)))


def _parse_started_at(task_dir: Path) -> float | None:
    meta_path = task_dir / "meta.json"
    if meta_path.is_file():
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            raw = data.get("started_at")
            if raw:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.timestamp()
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    try:
        return task_dir.stat().st_mtime
    except OSError:
        return None


def main() -> int:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_db()

    now = time.time()
    now_dt = datetime.now(timezone.utc)
    removed_dirs = 0

    if DOWNLOAD_DIR.is_dir():
        for entry in DOWNLOAD_DIR.iterdir():
            if not entry.is_dir():
                continue
            started = _parse_started_at(entry)
            if started is None:
                continue
            if now - started < TTL_SECONDS:
                continue
            shutil.rmtree(entry, ignore_errors=True)
            removed_dirs += 1
            print(f"Removed folder {entry.name}")

    db = SessionLocal()
    try:
        stmt = select(Job)
        jobs = list(db.scalars(stmt).all())
        updated = 0
        for job in jobs:
            if job.status == "completed" and job.expires_at and job.expires_at <= now_dt:
                job.status = "expired"
                job.user_error_code = "file_expired"
                job.failure_reason_user = "This file has expired."
                updated += 1
                continue
            if job.status == "queued" and job.submitted_at:
                age = (now_dt - job.submitted_at).total_seconds()
                if age > QUEUED_TTL_SECONDS:
                    job.status = "failed"
                    job.user_error_code = "server_busy"
                    job.failure_reason_user = "Job expired while waiting in queue."
                    updated += 1
            if job.output_path_relative:
                p = DOWNLOAD_DIR / job.output_path_relative
                if job.status == "completed" and not p.is_file():
                    job.status = "expired"
                    job.user_error_code = "file_expired"
                    job.failure_reason_user = "File was removed."
                    updated += 1
        if updated:
            db.commit()
        print(f"Updated {updated} job row(s). Removed {removed_dirs} folder(s).")
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
