"""ORM models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_type: Mapped[str] = mapped_column(String(16), nullable=False, default="video")
    format_id: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    output_path_relative: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_reason_user: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_detail_internal: Mapped[str | None] = mapped_column(Text, nullable=True)
