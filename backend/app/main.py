"""
FastAPI application factory and route registration.
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.app import config
from backend.app.api.deps import error_payload, limiter
from backend.app.api.routes import admin, files, health, jobs, metadata, static_pages
from backend.app.db import init_db
from backend.app.services import errors

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info("app_start env=%s download_dir=%s", config.APP_ENV, config.DOWNLOAD_DIR)
    yield
    logger.info("app_stop")


app = FastAPI(title="Video Downloader API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):  # noqa: ARG001
    logger.exception("unhandled_error path=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": error_payload("server_busy")},
    )


app.include_router(health.router)
app.include_router(metadata.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(static_pages.router)

if config.FRONTEND_DIST.is_dir() and (config.FRONTEND_DIST / "index.html").is_file():
    static_pages.mount_frontend(app)
else:

    @app.get("/")
    def root_placeholder():
        return static_pages.root_placeholder()
