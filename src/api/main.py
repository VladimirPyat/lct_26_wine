"""FastAPI application entrypoint (Stage 0 stub)."""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="Vine Scanner",
    version="0.1.0",
    description="Wine label scanner — Stage 0 scaffold",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
