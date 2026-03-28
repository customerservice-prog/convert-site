"""
Delete download job folders older than TTL (default 60 minutes).
Schedule with Task Scheduler or cron:  python cleanup.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", "./downloads")).resolve()
TTL_SECONDS = int(os.environ.get("DOWNLOAD_TTL_SECONDS", str(60 * 60)))


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
    if not DOWNLOAD_DIR.is_dir():
        print(f"No download directory at {DOWNLOAD_DIR}", file=sys.stderr)
        return 0

    now = time.time()
    removed = 0
    for entry in DOWNLOAD_DIR.iterdir():
        if not entry.is_dir():
            continue
        started = _parse_started_at(entry)
        if started is None:
            continue
        if now - started < TTL_SECONDS:
            continue
        shutil.rmtree(entry, ignore_errors=True)
        removed += 1
        print(f"Removed {entry.name}")

    print(f"Cleanup done. Removed {removed} job folder(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
