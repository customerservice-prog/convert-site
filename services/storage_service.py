"""Disk space, paths, and safe download filenames."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import config


def downloads_base() -> Path:
    config.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return config.DOWNLOAD_DIR


def job_dir(job_id: str) -> Path:
    base = downloads_base().resolve()
    d = (base / job_id).resolve()
    if not str(d).startswith(str(base)) or d == base:
        raise ValueError("Invalid job path")
    return d


def free_disk_bytes(path: Path | None = None) -> int:
    p = path or downloads_base()
    p.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(p)
    return int(usage.free)


def has_min_free_disk() -> bool:
    return free_disk_bytes() >= config.MIN_FREE_DISK_BYTES


def sanitize_filename_stem(title: str | None, max_len: int = 120) -> str:
    if not title:
        return "download"
    s = title.strip()
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return "download"
    return s[:max_len]


def content_disposition_filename(stem: str, ext: str) -> str:
    ext = ext.lstrip(".") if ext else "mp4"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem) or "download"
    return f"{safe}.{ext}"


def media_type_for_ext(ext: str) -> str:
    e = ext.lower().lstrip(".")
    return {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mkv": "video/x-matroska",
        "m4a": "audio/mp4",
        "mp3": "audio/mpeg",
        "opus": "audio/opus",
        "ogg": "audio/ogg",
    }.get(e, "application/octet-stream")
