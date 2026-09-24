"""FastAPI application entrypoint (Stage 0 stub + static catalog images)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STATIC_WINES = _REPO_ROOT / "static" / "wines"

app = FastAPI(
    title="Vine Scanner",
    version="0.1.0",
    description="Wine label scanner — Stage 0 scaffold",
)

# Catalog images written by import (`image_url` = /static/wines/{slug}.webp).
_STATIC_WINES.mkdir(parents=True, exist_ok=True)
app.mount(
    "/static/wines",
    StaticFiles(directory=str(_STATIC_WINES)),
    name="static_wines",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
