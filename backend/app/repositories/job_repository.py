"""Database operations for jobs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app import config
from backend.app.db import SessionLocal, write_lock
from backend.app.models import Job

ACTIVE_STATUSES = ("queued", "downloading", "processing")


def count_active_jobs(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.status.in_(ACTIVE_STATUSES))
        )
        or 0
    )


def count_active_jobs_for_ip(db: Session, client_ip: str | None) -> int:
    if not client_ip:
        return 0
    return int(
        db.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.status.in_(ACTIVE_STATUSES), Job.client_ip == client_ip)
        )
        or 0
    )


def get_job(db: Session, job_id: str) -> Job | None:
    return db.get(Job, job_id)


def list_recent_jobs(db: Session, limit: int = 100) -> list[Job]:
    stmt = select(Job).order_by(Job.submitted_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def update_job_fields(job_id: str, **fields: Any) -> None:
    with write_lock:
        db = SessionLocal()
        try:
            row = db.get(Job, job_id)
            if not row:
                return
            for k, v in fields.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            db.commit()
        finally:
            db.close()


def touch_job_started(job_id: str) -> None:
    now = datetime.now(timezone.utc)
    update_job_fields(job_id, started_at=now, status="downloading", progress=1, stage_message="Downloading…")


def mark_job_failed(job_id: str, *, user_code: str, user_msg: str, internal: str) -> None:
    update_job_fields(
        job_id,
        status="failed",
        progress=0,
        user_error_code=user_code,
        failure_reason_user=user_msg,
        failure_detail_internal=internal[:8000] if internal else None,
        completed_at=datetime.now(timezone.utc),
        stage_message=None,
    )


def mark_job_completed(
    job_id: str,
    *,
    relative_path: str,
    filename: str,
    file_size: int,
    title: str | None,
) -> None:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=config.FILE_EXPIRY_MINUTES)
    update_job_fields(
        job_id,
        status="completed",
        progress=100,
        stage_message="Ready",
        output_path_relative=relative_path,
        output_filename=filename,
        file_size=file_size,
        title=title,
        completed_at=now,
        expires_at=expires,
    )
