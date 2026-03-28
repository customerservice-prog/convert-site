# Convert Site — full product layout

Production-style layout: **Vite + React + TypeScript + Tailwind** frontend (`frontend/`), modular **FastAPI** backend (`backend/app/`), **SQLite** jobs, **yt-dlp** + **FFmpeg**, rate limits, Docker (multi-stage build), and automated tests (pytest + Vitest).

## Repository layout

```text
backend/app/          # API package (config, db, models, services, repositories, api/routes)
frontend/src/         # React UI (components, hooks, pages, services/api.ts)
main.py               # ASGI entry: re-exports backend.app.main:app
cleanup.py            # TTL cleanup + DB sync
legal/                # Terms & privacy HTML
tests/                # pytest (API + validation)
```

## Product scope (v1)

| Area | Decision |
|------|-----------|
| Sources | YouTube family URLs (`SUPPORTED_URL_HOSTS`) |
| Output | Video (MP4) and audio (M4A extract) |
| UX | Simple presets (Best / 1080p / 720p / Audio) + **Advanced** format list |
| Storage | Temporary; `cleanup.py` + expiry in DB |
| Queue | FastAPI `BackgroundTasks` |

## API (high level)

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/health` | DB + disk; `503` if degraded |
| `GET` | `/live` | Liveness |
| `GET` | `/ready` | Readiness (DB) |
| `POST` | `/api/info` | Normalized metadata: `normalized_choices`, `source_site`, `uploader`, `upload_date`, `duration_label`, capped `formats` for advanced UI |
| `POST` | `/api/jobs` | Body: `url`, `format_id`, `output_type`, optional `preset_key` (`best` / `p1080` / `p720` / `audio`) |
| `GET` | `/api/jobs/{id}` | `job_id`, `status_label`, `stage`, `download_url` when complete, `file_size`, `filename`, `thumbnail_url` |
| `GET` | `/api/files/{id}` | Stream file; `410` if expired |
| `GET` | `/api/admin/jobs` | `X-Admin-Key` |

## Local development

**Backend** (from repo root, `PYTHONPATH` must include `.` on some shells):

```powershell
$env:PYTHONPATH = "."
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend** (proxies `/api`, `/health`, `/legal` to port 8000):

```bash
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173** while the API runs on **8000**.

**Single port (production-style):** build the UI then serve only uvicorn:

```bash
cd frontend && npm run build && cd ..
$env:PYTHONPATH = "."
uvicorn main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000/** — static assets from `frontend/dist/`.

## Tests

```powershell
$env:PYTHONPATH = "."
python -m pytest tests -q
```

```bash
cd frontend && npm test
```

## Docker

```bash
docker compose up --build
```

The image builds the frontend and copies `frontend/dist` into the Python image. Set `PYTHONPATH=/app` (already in Dockerfile).

## Configuration

See `.env.example`. Use explicit `CORS_ALLOWED_ORIGINS` in production. Set `ADMIN_API_KEY` for admin routes. `TRUST_PROXY=1` only behind a trusted reverse proxy.

## Database note

If you upgrade from an older DB without `thumbnail_url`, the app attempts a best-effort `ALTER TABLE` on SQLite startup. If issues persist, delete `data/jobs.db` in dev.

## Legal

Only download content you are permitted to use. Operators must supply final Terms/Privacy and support channels.
