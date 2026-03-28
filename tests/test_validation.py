"""URL validation and job id safety."""
from __future__ import annotations

from services.storage_service import content_disposition_filename, sanitize_filename_stem
from services.validation import is_safe_job_id, validate_video_url


def test_youtube_watch_ok():
    ok, err = validate_video_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert ok and err is None


def test_youtu_be_ok():
    ok, err = validate_video_url("https://youtu.be/dQw4w9WgXcQ")
    assert ok


def test_unsupported_host():
    ok, code = validate_video_url("https://example.com/video")
    assert not ok and code == "unsupported_source"


def test_invalid_scheme():
    ok, code = validate_video_url("ftp://youtube.com/foo")
    assert not ok and code == "invalid_url"


def test_safe_job_id():
    assert is_safe_job_id("550e8400-e29b-41d4-a716-446655440000")
    assert not is_safe_job_id("../etc/passwd")
    assert not is_safe_job_id("not-a-uuid")


def test_sanitize_filename():
    assert ".." not in sanitize_filename_stem('evil<>:"/\\|?*')
    assert content_disposition_filename("My Video", "mp4").endswith(".mp4")
