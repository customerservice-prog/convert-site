"""Normalize yt-dlp metadata into frontend-friendly payloads."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from backend.app.services import ytdlp_service

# Presets: key -> (format_id, output_type, label, description, container hint)
PRESET_DEFINITIONS: list[dict[str, Any]] = [
    {
        "key": "best",
        "label": "Best quality MP4",
        "description": "Highest combined video and audio, merged to MP4",
        "format_id": "bestvideo+bestaudio/best",
        "output_type": "video",
        "container": "mp4",
    },
    {
        "key": "p1080",
        "label": "1080p HD",
        "description": "Up to 1080p video with best audio",
        "format_id": "bestvideo[height<=1080]+bestaudio/best",
        "output_type": "video",
        "container": "mp4",
    },
    {
        "key": "p720",
        "label": "720p",
        "description": "Up to 720p — smaller file, still HD",
        "format_id": "bestvideo[height<=720]+bestaudio/best",
        "output_type": "video",
        "container": "mp4",
    },
    {
        "key": "audio",
        "label": "Audio only (M4A)",
        "description": "Best audio track, extracted to M4A",
        "format_id": "bestaudio/best",
        "output_type": "audio",
        "container": "m4a",
    },
]

PRESET_BY_KEY: dict[str, tuple[str, str]] = {
    p["key"]: (p["format_id"], p["output_type"]) for p in PRESET_DEFINITIONS
}


def source_site_label(info: dict[str, Any], page_url: str) -> str:
    ext = (info.get("extractor") or info.get("ie_key") or "").lower()
    if "youtube" in ext:
        return "YouTube"
    net = urlparse(page_url).netloc
    return net.replace("www.", "") if net else "unknown"


def format_upload_date(raw: str | None) -> str | None:
    if not raw or len(str(raw)) != 8:
        return None
    s = str(raw)
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"


def build_metadata_payload(url: str, info: dict[str, Any]) -> dict[str, Any]:
    page_url = info.get("webpage_url") or url
    raw_formats = ytdlp_service.formats_for_response(info)
    return {
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "duration_label": _duration_label(info.get("duration")),
        "source_site": source_site_label(info, page_url),
        "uploader": info.get("uploader") or info.get("channel"),
        "upload_date": format_upload_date(info.get("upload_date")),
        "description": (info.get("description") or "")[:400] or None,
        "formats": raw_formats,
        "normalized_choices": list(PRESET_DEFINITIONS),
        "recommended_choice_key": "best",
        "default_format_id": "bestvideo+bestaudio/best",
    }


def _duration_label(seconds: Any) -> str | None:
    if seconds is None:
        return None
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return None
    m, sec = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def resolve_preset(preset_key: str | None) -> tuple[str, str] | None:
    if not preset_key:
        return None
    key = preset_key.strip().lower()
    return PRESET_BY_KEY.get(key)
