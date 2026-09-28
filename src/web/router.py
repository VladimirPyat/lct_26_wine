"""Страницы веб-интерфейса (Jinja2) поверх ``request.app.state.product_service``."""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.routing import APIRoute
from starlette.datastructures import UploadFile

from core.config import ProductSettings, UploadSettings
from core.product import (
    AnalogsResult,
    Dictionaries,
    FeedbackIn,
    ProductService,
    SearchNotFoundError,
    UploadRejectedError,
    Verdict,
    WineCard,
)
from web.templating import WEB_DIR, templates
from web.views import (
    CATALOG_PAGE_SIZE,
    build_catalog_view,
    build_result_view,
    filters_from_query,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = WEB_DIR.parents[1]
_TMP_UPLOADS = _REPO_ROOT / "data" / "tmp" / "uploads"
_SEARCH_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_MAX_SLUG_LEN = 300
_MAX_PAGE = 10_000
_VERDICTS = ("match", "mismatch")
_EXT_BY_TYPE: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
_TYPE_NAMES: dict[str, str] = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WebP",
}


class _WebRoute(APIRoute):
    """Маршрут UI: необработанные ошибки → страница ``error.html`` без трассировки."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def guarded(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError:
                return _error(request, 400, "Некорректный запрос.")
            except Exception:
                logger.exception(
                    "web UI error on %s %s", request.method, request.url.path
                )
                return _error(
                    request, 500, "Что-то пошло не так. Попробуйте ещё раз чуть позже."
                )

        return guarded


router = APIRouter(route_class=_WebRoute, include_in_schema=False)


def _service(request: Request) -> ProductService:
    return cast(ProductService, request.app.state.product_service)


def _settings(request: Request) -> ProductSettings:
    return cast(ProductSettings, request.app.state.product_settings)


def _render(
    request: Request,
    name: str,
    context: dict[str, Any],
    *,
    nav: str = "",
    status_code: int = 200,
) -> Response:
    return templates.TemplateResponse(
        request, name, {"nav": nav, **context}, status_code=status_code
    )


def _error(request: Request, status_code: int, message: str) -> Response:
    title = "Страница не найдена" if status_code == 404 else "Ошибка"
    return _render(
        request,
        "pages/error.html",
        {"status_code": status_code, "title": title, "message": message},
        status_code=status_code,
    )


def _not_found(request: Request, message: str = "Такой страницы нет.") -> Response:
    return _error(request, 404, message)


def _valid_search_id(search_id: str) -> bool:
    return _SEARCH_ID_RE.fullmatch(search_id) is not None


def _sniff_image_type(head: bytes) -> str | None:
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def _scan_context(upload: UploadSettings, error: str | None = None) -> dict[str, Any]:
    names = [_TYPE_NAMES.get(t, t) for t in upload.content_types]
    return {
        "error": error,
        "accept": ",".join(upload.content_types),
        "max_mb": f"{upload.max_mb:g}",
        "max_bytes": int(upload.max_mb * 1024 * 1024),
        "type_names": ", ".join(names),
    }


def _scan_error(request: Request, status_code: int, message: str) -> Response:
    upload = _settings(request).upload
    return _render(
        request,
        "pages/scan.html",
        _scan_context(upload, message),
        nav="scan",
        status_code=status_code,
    )


@router.get("/")
async def scan_page(request: Request) -> Response:
    """Сканер: камера (JS) + загрузка файла (работает без JS)."""
    upload = _settings(request).upload
    return _render(request, "pages/scan.html", _scan_context(upload), nav="scan")


@router.post("/search")
async def search(request: Request) -> Response:
    """Проверить загрузку, распознать вино и перенаправить на результат (PRG)."""
    upload = _settings(request).upload
    max_bytes = int(upload.max_mb * 1024 * 1024)
    form = await request.form(max_files=1, max_fields=5)
    try:
        image = form.get("image")
        if not isinstance(image, UploadFile):
            return _scan_error(request, 400, "Выберите фото бутылки.")
        data = await image.read(max_bytes + 1)
        original_name = Path(image.filename or "").name or None
        declared = (image.content_type or "").split(";")[0].strip().lower()
    finally:
        await form.close()

    if not data:
        return _scan_error(request, 400, "Файл пустой. Выберите фото бутылки.")
    if len(data) > max_bytes:
        return _scan_error(
            request,
            413,
            f"Файл слишком большой. Максимальный размер — {upload.max_mb:g} МБ.",
        )
    allowed = [t.lower() for t in upload.content_types]
    sniffed = _sniff_image_type(data[:16])
    if sniffed is None or sniffed not in allowed:
        if sniffed is None and declared in allowed:
            return _scan_error(
                request,
                400,
                "Не удалось прочитать изображение. Попробуйте другое фото.",
            )
        names = ", ".join(_TYPE_NAMES.get(t, t) for t in upload.content_types)
        return _scan_error(
            request, 415, f"Неподдерживаемый формат. Подойдут файлы: {names}."
        )

    _TMP_UPLOADS.mkdir(parents=True, exist_ok=True)
    tmp_path = _TMP_UPLOADS / f"{uuid.uuid4().hex}{_EXT_BY_TYPE[sniffed]}"
    try:
        await run_in_threadpool(tmp_path.write_bytes, data)
        result = await run_in_threadpool(
            _service(request).search, tmp_path, original_name=original_name
        )
    except UploadRejectedError:
        return _scan_error(
            request, 400, "Не удалось прочитать изображение. Попробуйте другое фото."
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    return RedirectResponse(f"/result/{result.search_id}", status_code=303)


@router.get("/result/{search_id}")
async def result_page(request: Request, search_id: str) -> Response:
    """Результат поиска по статусу; ``?analogs=1`` — аналоги для found."""
    if not _valid_search_id(search_id):
        return _not_found(request, "Результат поиска не найден.")
    service = _service(request)
    result = await run_in_threadpool(service.get_search, search_id)
    if result is None:
        return _not_found(request, "Результат поиска не найден или устарел.")

    params = request.query_params
    extra_analogs: AnalogsResult | None = None
    if params.get("analogs") == "1" and result.analogs is None:
        limit = _settings(request).analogs.limit
        try:
            extra_analogs = await run_in_threadpool(
                service.analogs_for, search_id, limit=limit
            )
        except SearchNotFoundError:
            return _not_found(request, "Результат поиска не найден или устарел.")
    verdict = params.get("verdict")
    dictionaries = await run_in_threadpool(service.dictionaries)
    view = build_result_view(
        result,
        extra_analogs=extra_analogs,
        feedback_sent=params.get("fb") == "1",
        feedback_verdict=verdict if verdict in _VERDICTS else None,
        dictionaries=dictionaries,
    )
    return _render(request, "pages/result.html", {"view": view}, nav="scan")


@router.get("/result/{search_id}/photo")
async def result_photo(request: Request, search_id: str) -> Response:
    """Исходное фото запроса (только по точному id)."""
    if not _valid_search_id(search_id):
        return _not_found(request, "Фото не найдено.")
    path = await run_in_threadpool(_service(request).query_photo_path, search_id)
    if path is None or not path.is_file():
        return _not_found(request, "Фото не найдено.")
    return FileResponse(
        path,
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/result/{search_id}/feedback")
async def result_feedback(request: Request, search_id: str) -> Response:
    """Отзыв «Это то вино?» → PRG на результат с состоянием «спасибо»."""
    if not _valid_search_id(search_id):
        return _not_found(request, "Результат поиска не найден.")
    form = await request.form(max_files=0, max_fields=5)
    verdict = str(form.get("verdict") or "")
    slug = str(form.get("slug") or "").strip()[:_MAX_SLUG_LEN] or None
    if verdict not in _VERDICTS:
        return _error(
            request, 400, "Не удалось сохранить ответ: выберите «Да» или «Нет»."
        )
    service = _service(request)
    result = await run_in_threadpool(service.get_search, search_id)
    if result is None:
        return _not_found(request, "Результат поиска не найден или устарел.")
    if slug is None and result.winner is not None:
        slug = result.winner.slug
    feedback = FeedbackIn(
        search_id=search_id, slug=slug, verdict=cast(Verdict, verdict)
    )
    try:
        await run_in_threadpool(service.record_feedback, feedback)
    except SearchNotFoundError:
        return _not_found(request, "Результат поиска не найден или устарел.")
    return RedirectResponse(
        f"/result/{search_id}?fb=1&verdict={verdict}#feedback", status_code=303
    )


@router.get("/wine/{slug}")
async def wine_page(request: Request, slug: str) -> Response:
    """Карточка вина по slug."""
    if len(slug) > _MAX_SLUG_LEN:
        return _not_found(request, "Вино не найдено.")
    service = _service(request)
    wine = await run_in_threadpool(service.get_wine, slug)
    if wine is None:
        return _not_found(request, "Вино не найдено в каталоге.")
    return _render(request, "pages/wine.html", {"wine": wine}, nav="catalog")


def _parse_page(raw: str | None) -> int:
    try:
        page = int(raw or "1")
    except ValueError:
        return 1
    return min(max(page, 1), _MAX_PAGE)


@router.get("/catalog")
async def catalog_page(request: Request) -> Response:
    """Каталог с фильтрами из справочников и пагинацией."""
    params = request.query_params
    filters = filters_from_query(params, params.getlist("exclude_slugs"))
    page = _parse_page(params.get("page"))
    service = _service(request)

    def load() -> tuple[Dictionaries, list[WineCard], int, int]:
        dictionaries = service.dictionaries()
        current = page
        wines, total = service.find_wines(
            filters, limit=CATALOG_PAGE_SIZE, offset=(current - 1) * CATALOG_PAGE_SIZE
        )
        if not wines and total > 0:
            current = (total - 1) // CATALOG_PAGE_SIZE + 1
            wines, total = service.find_wines(
                filters,
                limit=CATALOG_PAGE_SIZE,
                offset=(current - 1) * CATALOG_PAGE_SIZE,
            )
        return dictionaries, wines, total, current

    dictionaries, wines, total, page = await run_in_threadpool(load)
    view = build_catalog_view(
        filters, dictionaries=dictionaries, wines=wines, total=total, page=page
    )
    return _render(request, "pages/catalog.html", {"view": view}, nav="catalog")


@router.get("/me")
async def me_page(request: Request) -> Response:
    """Оболочка «Моих вин»; данные заполняет ``store.js`` из localStorage."""
    return _render(request, "pages/me.html", {}, nav="me")
