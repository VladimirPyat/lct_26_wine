"""FastAPI application entrypoint (eval predict + static catalog images)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.routers.eval import router as eval_router
from api.runtime import build_eval_runtime
from core.config import load_product_settings
from core.product import StubProductService
from web import STATIC_DIR as _WEB_STATIC
from web import router as web_router

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STATIC_WINES = _REPO_ROOT / "static" / "wines"
_TMP_UPLOADS = _REPO_ROOT / "data" / "tmp" / "uploads"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load YOLO/DINO/DB once; OCR stays lazy until first rerank."""
    _TMP_UPLOADS.mkdir(parents=True, exist_ok=True)
    logger.info("building eval runtime (YOLO + DINO + DB)…")
    app.state.eval_runtime = build_eval_runtime(_REPO_ROOT)
    logger.info(
        "eval runtime ready (ocr.engine=%s enable_rerank=%s top_k=%s)",
        app.state.eval_runtime.ocr_rerank.ocr.engine,
        app.state.eval_runtime.ocr_rerank.policy.enable_rerank,
        app.state.eval_runtime.ocr_rerank.policy.top_k,
    )
    app.state.product_settings = load_product_settings()
    # PRODUCT SERVICE: backend branch replaces this line with the real service.
    app.state.product_service = StubProductService()
    try:
        yield
    finally:
        runtime = getattr(app.state, "eval_runtime", None)
        if runtime is not None:
            runtime.engine.dispose()
            app.state.eval_runtime = None


app = FastAPI(
    title="Vine Scanner",
    version="0.2.0",
    description="Wine label scanner — Stage 2B eval predict",
    lifespan=lifespan,
)

_STATIC_WINES.mkdir(parents=True, exist_ok=True)
app.mount(
    "/static/wines",
    StaticFiles(directory=str(_STATIC_WINES)),
    name="static_wines",
)
app.mount("/ui-static", StaticFiles(directory=str(_WEB_STATIC)), name="ui_static")
app.include_router(eval_router)
app.include_router(web_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
