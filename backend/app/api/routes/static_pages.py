from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app import config

router = APIRouter()


@router.get("/legal/{page}")
def serve_legal(page: str):
    if page not in ("terms", "privacy"):
        raise HTTPException(status_code=404, detail="Not found")
    p = config.LEGAL_DIR / f"{page}.html"
    if not p.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(p, media_type="text/html")


def mount_frontend(app) -> None:
    dist = config.FRONTEND_DIST
    if not dist.is_dir() or not (dist / "index.html").is_file():
        return
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/")
    def spa_index():
        return FileResponse(dist / "index.html", media_type="text/html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        skip = (
            "api",
            "health",
            "live",
            "ready",
            "legal",
            "docs",
            "openapi.json",
            "redoc",
        )
        first = full_path.split("/")[0] if full_path else ""
        if first in skip or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(dist / "index.html", media_type="text/html")


def root_placeholder():
    """When no built frontend exists, / explains how to build."""
    return JSONResponse(
        {
            "message": "API is running. Build the frontend (npm run build in frontend/) or open /docs for OpenAPI.",
            "health": "/health",
        }
    )
