"""Продуктовый JSON API ``/api/v1/*`` (контракт ``product_api.md`` §5)."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from api.eval_pipeline import EmptyCatalogError
from core.config import ProductSettings
from core.product import (
    AnalogsResult,
    CatalogFilters,
    Dictionaries,
    FeedbackIn,
    ProductService,
    SearchNotFoundError,
    SearchResult,
    UploadRejectedError,
    WineCard,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["product"])

_CHUNK_BYTES = 1024 * 1024
_BYTES_PER_MB = 1024 * 1024
_SUFFIX_BY_TYPE = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
_SEARCH_NOT_FOUND = "search not found"
_MAX_LIMIT = 50


class WinesPage(BaseModel):
    """Страница каталога: вина и общее число совпадений."""

    items: list[WineCard]
    total: int


def _service(request: Request) -> ProductService:
    service: ProductService | None = getattr(request.app.state, "product_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="product service not initialized")
    return service


def _settings(request: Request) -> ProductSettings:
    settings: ProductSettings | None = getattr(
        request.app.state, "product_settings", None
    )
    if settings is None:
        raise HTTPException(status_code=503, detail="product settings not initialized")
    return settings


def _upload_dir(request: Request) -> Path:
    runtime = getattr(request.app.state, "eval_runtime", None)
    root = getattr(runtime, "repo_root", None)
    if not isinstance(root, Path):
        root = Path(__file__).resolve().parents[3]
    path = root / "data" / "tmp" / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _base_content_type(value: str | None) -> str:
    return (value or "").split(";", 1)[0].strip().lower()


def _check_decodable(path: Path) -> None:
    try:
        with Image.open(path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as err:
        raise HTTPException(status_code=400, detail="image cannot be decoded") from err
    except Image.DecompressionBombError as err:
        raise HTTPException(status_code=413, detail="image is too large") from err


async def _save_upload(
    image: UploadFile, settings: ProductSettings, dest: Path
) -> Path:
    """Проверить тип, потоково сохранить с контролем размера; вернуть путь."""
    content_type = _base_content_type(image.content_type)
    allowed = {t.lower() for t in settings.upload.content_types}
    if content_type not in allowed:
        raise HTTPException(
            status_code=415, detail=f"unsupported content type: {content_type or '-'}"
        )
    max_bytes = int(settings.upload.max_mb * _BYTES_PER_MB)
    suffix = _SUFFIX_BY_TYPE.get(content_type, ".img")
    size = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=str(dest)) as out:
        tmp_path = Path(out.name)
        try:
            while chunk := await image.read(_CHUNK_BYTES):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"image exceeds {settings.upload.max_mb:g} MB",
                    )
                out.write(chunk)
        except BaseException:
            out.close()
            tmp_path.unlink(missing_ok=True)
            raise
    if size == 0:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="empty image upload")
    return tmp_path


@router.post("/search", response_model=SearchResult)
async def search(
    request: Request,
    image: Annotated[UploadFile, File(description="Фото бутылки / этикетки")],
) -> SearchResult:
    """Multipart ``image`` → ``SearchResult``."""
    service = _service(request)
    settings = _settings(request)
    tmp_path = await _save_upload(image, settings, _upload_dir(request))
    try:
        await run_in_threadpool(_check_decodable, tmp_path)
        return await run_in_threadpool(
            service.search, tmp_path, original_name=image.filename
        )
    except UploadRejectedError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except EmptyCatalogError as err:
        logger.error("product search: empty catalog: %s", err)
        raise HTTPException(status_code=503, detail="catalog is empty") from err
    except HTTPException:
        raise
    except Exception as err:
        logger.exception("product search failed")
        raise HTTPException(status_code=500, detail="search failed") from err
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/search/{search_id}", response_model=SearchResult)
async def get_search(request: Request, search_id: str) -> SearchResult:
    """Сохранённый результат поиска."""
    result = await run_in_threadpool(_service(request).get_search, search_id)
    if result is None:
        raise HTTPException(status_code=404, detail=_SEARCH_NOT_FOUND)
    return result


@router.get("/search/{search_id}/analogs", response_model=AnalogsResult)
async def get_analogs(
    request: Request,
    search_id: str,
    limit: Annotated[int, Query(ge=1, le=_MAX_LIMIT)] = 5,
) -> AnalogsResult:
    """Аналоги для поиска (``winner_filters`` / ``ocr_filters`` / ``vector``)."""
    try:
        return await run_in_threadpool(
            _service(request).analogs_for, search_id, limit=limit
        )
    except SearchNotFoundError as err:
        raise HTTPException(status_code=404, detail=_SEARCH_NOT_FOUND) from err


@router.get("/wines/{slug}", response_model=WineCard)
async def get_wine(request: Request, slug: str) -> WineCard:
    """Карточка вина по slug."""
    wine = await run_in_threadpool(_service(request).get_wine, slug)
    if wine is None:
        raise HTTPException(status_code=404, detail="wine not found")
    return wine


@router.get("/wines", response_model=WinesPage)
async def find_wines(
    request: Request,
    color: str | None = None,
    grape: str | None = None,
    region: str | None = None,
    sweetness: str | None = None,
    dish: str | None = None,
    exclude_manufacturer: str | None = None,
    limit: Annotated[int, Query(ge=1, le=_MAX_LIMIT)] = 5,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WinesPage:
    """Каталог по фильтрам, рейтинг по убыванию."""
    filters = CatalogFilters(
        color=color or None,
        grape=grape or None,
        region=region or None,
        sweetness=sweetness or None,
        dish=dish or None,
        exclude_manufacturer=exclude_manufacturer or None,
    )
    items, total = await run_in_threadpool(
        _service(request).find_wines, filters, limit=limit, offset=offset
    )
    return WinesPage(items=items, total=total)


@router.get("/dictionaries", response_model=Dictionaries)
async def get_dictionaries(request: Request) -> Dictionaries:
    """Справочники фильтров (строятся при старте)."""
    return await run_in_threadpool(_service(request).dictionaries)


@router.post("/feedback", status_code=204, response_class=Response)
async def post_feedback(request: Request, feedback: FeedbackIn) -> Response:
    """Отзыв «то вино / не то» → JSONL; неизвестный поиск → 404."""
    try:
        await run_in_threadpool(_service(request).record_feedback, feedback)
    except SearchNotFoundError as err:
        raise HTTPException(status_code=404, detail=_SEARCH_NOT_FOUND) from err
    return Response(status_code=204)
