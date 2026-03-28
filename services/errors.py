"""User-safe error codes and messages (no raw stack traces to clients)."""
from __future__ import annotations

USER_MESSAGES: dict[str, str] = {
    "invalid_url": "That link doesn’t look valid. Use a supported video URL.",
    "unsupported_source": "This source isn’t supported in v1. We currently focus on YouTube links.",
    "metadata_failed": "We couldn’t read that video. It may be private, region-locked, or unavailable.",
    "duration_exceeded": "This video is longer than the maximum allowed length for this service.",
    "rate_limited": "Too many requests. Please wait and try again.",
    "too_many_jobs": "The server is busy. Please try again in a few minutes.",
    "disk_full": "Server storage is low; new downloads are temporarily paused.",
    "format_unavailable": "That format isn’t available for this video.",
    "download_failed": "Download failed. Try another quality or try again later.",
    "processing_failed": "Processing failed after download.",
    "file_expired": "This file has expired. Start a new download.",
    "file_missing": "The file is no longer available.",
    "job_not_found": "No download was found for that id.",
    "server_busy": "The service is temporarily busy. Please retry shortly.",
}


def user_message(code: str, fallback: str | None = None) -> str:
    return USER_MESSAGES.get(code) or fallback or "Something went wrong. Please try again."
