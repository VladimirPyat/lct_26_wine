"""Просмотр веб-интерфейса без бэкенда: UI-роутер поверх ``StubProductService``.

Без моделей (YOLO/DINO/OCR), без БД и без lifespan — только шаблоны, статика
и фикстурные вина заглушки. Статус результата задаётся именем загружаемого файла:
``*_low.jpg`` → низкая уверенность, ``*_notfound.jpg`` → «не найдено»,
любое другое имя → найдено.

Запуск (из корня репозитория)::

    uv run python scripts/dev_ui_stub.py

Затем открыть http://127.0.0.1:8082/ (порт можно сменить: ``--port 8090``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from core.config import load_product_settings  # noqa: E402
from core.product import StubProductService  # noqa: E402
from web import STATIC_DIR as WEB_STATIC  # noqa: E402
from web import router as web_router  # noqa: E402

STATIC_WINES = REPO_ROOT / "static" / "wines"


def build_app() -> FastAPI:
    """Минимальное приложение: UI + статика, сервис-заглушка."""
    app = FastAPI(title="Vine UI (stub)")
    if STATIC_WINES.is_dir():
        app.mount(
            "/static/wines",
            StaticFiles(directory=str(STATIC_WINES)),
            name="static_wines",
        )
    app.mount("/ui-static", StaticFiles(directory=str(WEB_STATIC)), name="ui_static")
    app.include_router(web_router)
    app.state.product_service = StubProductService()
    app.state.product_settings = load_product_settings()
    return app


def main() -> None:
    """Разобрать аргументы и запустить uvicorn."""
    parser = argparse.ArgumentParser(description="UI preview on StubProductService")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8082)
    args = parser.parse_args()
    uvicorn.run(build_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
