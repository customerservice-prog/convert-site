"""Test isolation: temp SQLite + downloads before importing the app."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_tmp = tempfile.mkdtemp()
Path(_tmp, "data").mkdir(parents=True, exist_ok=True)
Path(_tmp, "dl").mkdir(parents=True, exist_ok=True)
_jobs_db = Path(_tmp, "data", "jobs.db")
os.environ["DATA_DIR"] = str(Path(_tmp, "data"))
os.environ["DOWNLOAD_DIR"] = str(Path(_tmp, "dl"))
os.environ["DATABASE_URL"] = "sqlite:///" + str(_jobs_db).replace("\\", "/")
os.environ.setdefault("RATE_LIMIT_INFO", "1000/second")
os.environ.setdefault("RATE_LIMIT_JOBS", "1000/second")

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.db import init_db  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c
