# Video Downloading Web Application (MVP)

Web UI and **FastAPI** backend to fetch video metadata and download merged files (primarily YouTube) using **yt-dlp** and **FFmpeg**. This MVP uses **FastAPI `BackgroundTasks`** (no Celery/Redis) and stores files under `./downloads/<job_id>/`. Run **`cleanup.py`** on a schedule to delete old jobs.

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/info` | Body: `{ "url" }` → title, thumbnail, duration, formats |
| `POST` | `/api/jobs` | Body: `{ "url", "format_id" }` → `{ "job_id" }` |
| `GET` | `/api/jobs/{id}` | `{ "status", "progress" }` — statuses: `queued`, `downloading`, `processing`, `completed`, `failed` |
| `GET` | `/api/files/{id}` | Download file when `completed` |

`GET /` serves `index.html`.

## Stack

- Python 3.10+, FastAPI, uvicorn  
- yt-dlp (downloads + metadata)  
- FFmpeg on `PATH` (mux to MP4)  
- Frontend: React (CDN) + Tailwind CSS (CDN), no build step  

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Install **FFmpeg** and ensure it is available on your `PATH`.

## Run

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open **http://127.0.0.1:8000/**.

For low traffic, background jobs run in the worker process after the response is sent (sync work runs in a thread pool). For horizontal scaling or heavy load, plan a **Phase 2** move to Celery + Redis.

## Cleanup

```bash
python cleanup.py
```

- `DOWNLOAD_DIR` — default `./downloads`  
- `DOWNLOAD_TTL_SECONDS` — default `3600` (60 minutes)  

## Environment

| Variable | Default |
|----------|---------|
| `DOWNLOAD_DIR` | `./downloads` |
| `CORS_ORIGINS` | `*` |
| `PORT` | `8000` (only when running `python main.py`) |

## Legal note

Download only content you are permitted to use. Respect site terms and copyright.

## Roadmap (from spec)

- **Phase 2:** Celery + Redis queue, richer UX  
- **Phase 3:** Streaming downloads, cloud storage, scale-out  
