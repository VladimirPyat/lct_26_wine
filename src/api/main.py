"""FastAPI application entrypoint (eval predict + static catalog images)."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.routers.eval import router as eval_router
from api.routers.product import router as product_router
from api.runtime import EvalRuntime, build_eval_runtime
from core.config import load_product_settings
from core.product.catalog_service import CatalogProductService
from web import STATIC_DIR as _WEB_STATIC
from web import router as web_router

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def _configure_logging() -> None:
    """Вывести логи приложения в stderr (uvicorn настраивает только свои логгеры).

    Уровень — ``VINE_LOG_LEVEL`` (по умолчанию ``INFO``). Если у root уже есть
    обработчики (pytest, внешний хост), ничего не меняем.
    """
    root = logging.getLogger()
    if root.handlers:
        return
    level_name = os.environ.get("VINE_LOG_LEVEL", "INFO").upper()
    level = logging.getLevelName(level_name)
    if not isinstance(level, int):
        msg = f"VINE_LOG_LEVEL must be a logging level name, got {level_name!r}"
        raise ValueError(msg)
    logging.basicConfig(level=level, format=_LOG_FORMAT)


_configure_logging()
logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STATIC_WINES = _REPO_ROOT / "static" / "wines"
_TMP_UPLOADS = _REPO_ROOT / "data" / "tmp" / "uploads"


def _warm_up_ocr(runtime: EvalRuntime) -> None:
    """Построить PHOCR до приёма запросов.

    При первом запуске PHOCR скачивает веса (~270 МБ); если делать это на первом
    rerank-запросе, клиент с таймаутом 60 с (скрипт заказчика) получит ошибку.
    Сбой прогрева не фатален: движок снова попробует построиться лениво.
    """
    if runtime.ocr_effective != "phocr" or not runtime.ocr_rerank.policy.enable_rerank:
        return
    logger.info("warming up PHOCR (first run downloads weights)…")
    try:
        runtime.get_ocr()
    except Exception:
        logger.exception("PHOCR warm-up failed; OCR will be retried on first rerank")
        return
    logger.info("PHOCR ready")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load YOLO/DINO/DB once and warm up PHOCR before serving."""
    _TMP_UPLOADS.mkdir(parents=True, exist_ok=True)
    logger.info("building eval runtime (YOLO + DINO + DB)…")
    app.state.eval_runtime = build_eval_runtime(_REPO_ROOT)
    logger.info(
        "eval runtime ready (ocr.engine=%s enable_rerank=%s top_k=%s)",
        app.state.eval_runtime.ocr_rerank.ocr.engine,
        app.state.eval_runtime.ocr_rerank.policy.enable_rerank,
        app.state.eval_runtime.ocr_rerank.policy.top_k,
    )
    _warm_up_ocr(app.state.eval_runtime)
    app.state.product_settings = load_product_settings()
    app.state.product_service = CatalogProductService(
        app.state.eval_runtime, app.state.product_settings
    )
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
app.include_router(product_router)
app.include_router(web_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
