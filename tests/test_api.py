"""API smoke tests (no real yt-dlp downloads)."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code in (200, 503)
    data = r.json()
    assert "status" in data
    assert "checks" in data


def test_live(client: TestClient):
    r = client.get("/live")
    assert r.status_code == 200
    assert r.json().get("status") == "live"


def test_ready(client: TestClient):
    r = client.get("/ready")
    assert r.status_code in (200, 503)


def test_info_invalid_url(client: TestClient):
    r = client.post("/api/info", json={"url": "https://example.com/not-youtube"})
    assert r.status_code == 400
    body = r.json()
    assert "detail" in body


def test_info_malformed(client: TestClient):
    r = client.post("/api/info", json={"url": "not-a-url"})
    assert r.status_code == 400


def test_job_status_invalid_id(client: TestClient):
    r = client.get("/api/jobs/not-a-uuid")
    assert r.status_code == 400


def test_job_status_missing(client: TestClient):
    r = client.get("/api/jobs/00000000-0000-4000-8000-000000000000")
    assert r.status_code == 404


def test_file_missing_job(client: TestClient):
    r = client.get("/api/files/00000000-0000-4000-8000-000000000000")
    assert r.status_code == 404
