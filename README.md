# YouTube Downloader (FastAPI + Celery)

Single-page UI (`index.html`) talks to a FastAPI backend that queues downloads with **Celery** and **Redis**, fetches media with **yt-dlp**, and merges streams with **FFmpeg**. Completed files live under `./downloads/<task_id>/` and are removed after **1 hour** when you run `cleanup.py` on a schedule.

## Flow

1. **POST /metadata** — video title, thumbnail, duration, and available formats (from yt-dlp).
2. **POST /download/start** — body: `{ "url", "format_id"? }`; returns `{ "id": "<celery task id>" }`.
3. **GET /download/status/:id** — poll until `state` is `SUCCESS` or `FAILURE`.
4. **GET /download/file/:id** — download the merged file when `SUCCESS`.

## Requirements

- Python 3.10+
- **Redis** (broker + result backend for Celery)
- **FFmpeg** on `PATH` (yt-dlp uses it to merge video + audio into MP4)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Start **Redis** (default `localhost:6379`).

## Run

**Terminal 1 — API (port 8000):**

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 — Celery worker:**

```bash
celery -A main.celery_app worker --loglevel=info --pool=solo
```

On Windows, `--pool=solo` avoids multiprocessing issues; on Linux you can omit it for better throughput.

**Frontend**

- Open `http://127.0.0.1:8000/` (FastAPI serves `index.html` from the project root), or  
- From this folder: `python -m http.server 5173` and open `http://127.0.0.1:5173/` — the page uses `http://localhost:8000` as the API when the page is **not** served from port 8000.

## Cleanup (1 hour TTL)

```bash
python cleanup.py
```

Schedule this hourly (Task Scheduler / cron). Override paths or TTL with env vars:

- `DOWNLOAD_DIR` — default `./downloads`
- `DOWNLOAD_TTL_SECONDS` — default `3600`

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker + result backend |
| `DOWNLOAD_DIR` | `./downloads` | Per-task download folders |
| `CORS_ORIGINS` | `*` | Comma-separated origins for FastAPI CORS |
| `PORT` | `8000` | Only used by `python main.py` |

## Legal note

Only download content you are allowed to use. Respect YouTube’s Terms of Service and copyright.
