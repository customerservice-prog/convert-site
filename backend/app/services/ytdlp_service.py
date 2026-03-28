"""
yt-dlp integration (Python API only — no shell string concatenation).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

import yt_dlp

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[dict[str, Any]], None]


def extract_metadata(url: str) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "socket_timeout": 30,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise ValueError("No metadata returned")
    return info


def formats_for_response(info: dict[str, Any], limit: int = 48) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in info.get("formats") or []:
        fid = f.get("format_id")
        if not fid:
            continue
        height = f.get("height")
        out.append(
            {
                "format_id": fid,
                "resolution": f.get("resolution") or f.get("format_note"),
                "height": height,
                "ext": f.get("ext"),
                "vcodec": f.get("vcodec"),
                "acodec": f.get("acodec"),
                "filesize": f.get("filesize") or f.get("filesize_approx"),
            }
        )
    out.sort(key=lambda x: (x.get("height") or 0), reverse=True)
    return out[:limit]


def download_to_dir(
    url: str,
    format_id: str,
    output_dir: str | Path,
    *,
    output_type: str = "video",
    progress_hook: ProgressCallback | None = None,
) -> None:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(out_dir / "output.%(ext)s")

    opts: dict[str, Any] = {
        "outtmpl": out_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 60,
        "progress_hooks": [progress_hook] if progress_hook else [],
    }

    if output_type == "audio":
        opts["format"] = format_id if format_id else "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "0",
            }
        ]
    else:
        opts["format"] = format_id or "bestvideo+bestaudio/best"
        opts["merge_output_format"] = "mp4"

    logger.info(
        "yt-dlp download start url_prefix=%s format=%s type=%s",
        url[:80],
        opts.get("format"),
        output_type,
    )
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
