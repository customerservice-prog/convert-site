# Convert Site — launch-oriented video downloader

FastAPI backend, React + Tailwind UI (CDN), **yt-dlp** + **FFmpeg**, **SQLite** job persistence, **slowapi** rate limits, disk guards, structured errors, admin listing, Docker, and cleanup automation.

## v1 product scope (frozen)

| Area | Launch decision |
|------|------------------|
| Sources | **YouTube** (and short URLs on `youtu.be`) — host allowlist in config |
| Output | **Video** (muxed MP4) and **audio** (M4A via FFmpeg extract) |
| Quality | **Best** preset plus per-format IDs from metadata |
| Accounts | **None** — anonymous use with **IP rate limits** and **concurrency caps** |
| Storage | **Temporary** only — `FILE_EXPIRY_MINUTES` + `cleanup.py` |
| Queue | **FastAPI `BackgroundTasks`** (Option A). Upgrade to Celery + Redis if traffic grows. |
| Max duration / size | `MAX_DURATION_SECONDS` (default 4h), `MAX_FILE_BYTES` (default 3 GiB) |

## API

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/health` | DB ping + disk free; `503` if degraded |
| `POST` | `/api/info` | `{ "url" }` → metadata + formats |
| `POST` | `/api/jobs` | `{ "url", "format_id", "output_type": "video"\|"audio" }` → `{ "job_id" }` |
| `GET` | `/api/jobs/{id}` | `status`: `queued` · `downloading` · `processing` · `completed` · `failed` · `expired` |
| `GET` | `/api/files/{id}` | Streams file; **`410`** if expired |
| `GET` | `/api/admin/jobs` | Requires header `X-Admin-Key: <ADMIN_API_KEY>` |
| `GET` | `/legal/terms`, `/legal/privacy` | Static legal pages |

Errors often return `{"detail": {"code": "...", "message": "..."}}`.

## Run locally

**Requirements:** Python 3.10+, **FFmpeg** on `PATH`, free disk above `MIN_FREE_DISK_BYTES`.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/`. Data lives in `./data/jobs.db` and `./downloads/` by default.

**Cleanup** (schedule every 5–15 minutes):

```bash
python cleanup.py
```

## Configuration

Copy `.env.example` to `.env` and adjust. Important variables:

- `CORS_ALLOWED_ORIGINS` — use explicit origins in production (not `*`).
- `ADMIN_API_KEY` — set to enable `/api/admin/jobs`.
- `TRUST_PROXY=1` — only behind a **trusted** reverse proxy so `X-Forwarded-For` is accurate for limits.
- `RATE_LIMIT_INFO`, `RATE_LIMIT_JOBS` — slowapi strings, e.g. `30/minute`, `8/hour`.
- `MAX_CONCURRENT_JOBS_GLOBAL`, `MAX_CONCURRENT_JOBS_PER_IP`
- `SUPPORTED_URL_HOSTS` — comma-separated hostnames

## Docker

```bash
docker compose up --build
```

Persisted volume: `/data` (SQLite + downloads). Install a reverse proxy (Caddy, nginx, Traefik) for HTTPS and set `CORS_ALLOWED_ORIGINS` + `TRUST_PROXY` appropriately.

## Tests

```bash
python -m pytest tests -q
```

## Launch checklist (abbreviated)

- [ ] `APP_ENV=production`, strong `SECRET_KEY`, `ADMIN_API_KEY` set
- [ ] `CORS_ALLOWED_ORIGINS` narrowed; HTTPS terminated at proxy
- [ ] FFmpeg present in runtime image/host
- [ ] `cleanup.py` on a schedule; disk alerts configured
- [ ] `/health` monitored (uptime + 503 rate)
- [ ] Smoke test: info → job → download → wait for expiry path
- [ ] Legal pages reachable; support contact documented for your deployment

## Legal

Only download content you have the right to use. You are responsible for compliance with YouTube and applicable law. This repository is a technical template; operators must provide their own Terms, Privacy, and abuse policies.

## Upgrades (post-launch)

- **Celery + Redis** for worker isolation and horizontal scale  
- **Postgres** instead of SQLite for multi-instance APIs  
- **Object storage** (S3) for large or multi-node file delivery  
- **CAPTCHA** or auth if abuse continues despite rate limits  
