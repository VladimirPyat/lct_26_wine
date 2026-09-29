"""Реальный ``ProductService`` поверх каталога Postgres и общего пайплайна eval."""

from __future__ import annotations

import json
import logging
import shutil
import time
import uuid
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.eval_pipeline import SearchRun, log_search, recognize_crop, run_search
from api.runtime import EvalRuntime
from core.config import ConfidenceSettings, ProductSettings
from core.contracts import RankedHit
from core.ocr.base import OCRUnavailableError
from core.policy.decision import PolicyDecision
from core.product.hints import build_grape_families, extract_hints
from core.product.schemas import (
    AnalogSource,
    AnalogsResult,
    Candidate,
    CatalogFilters,
    ConfidenceLevel,
    Dictionaries,
    FeedbackIn,
    OcrHints,
    SearchResult,
    SearchStatus,
    WineCard,
)
from core.product.service import SearchNotFoundError, UploadRejectedError
from core.product.storage import (
    cleanup_expired,
    photo_path,
    result_path,
)
from core.product.vocabulary import (
    Vocabulary,
    build_vocabulary,
    split_grapes,
    value_key,
)
from db.models import Category, Region, SweetnessLevel, Wine
from db.repository import WineRepository
from db.session import session_scope

logger = logging.getLogger(__name__)

_EXT_BY_FORMAT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
_ENDPOINT = "product"
# Policy skipped rerank because OCR is off / failed: do not call OCR again.
_OCR_SKIPPED = frozenset({"ocr_unavailable", "ocr_failed"})


class _FilterKwargs(TypedDict):
    category_name: str | None
    region_name: str | None
    sweetness_name: str | None
    grape_names_any: list[str] | None
    dishes_any: list[str] | None
    exclude_manufacturer: str | None
    exclude_slugs: list[str] | None


def classify_confidence(
    score_1: float, thresholds: ConfidenceSettings
) -> tuple[SearchStatus, ConfidenceLevel]:
    """Статус и уровень уверенности по косинусу image top-1 (контракт §4.1)."""
    if score_1 < thresholds.not_found_min:
        return "not_found", "low"
    if score_1 >= thresholds.high_min:
        return "found", "high"
    if score_1 >= thresholds.medium_min:
        return "found", "medium"
    return "low", "low"


def image_extension(path: Path) -> str:
    """Расширение по реальному формату файла.

    Недекодируемое или неподдерживаемое фото → ``UploadRejectedError``.
    """
    try:
        with Image.open(path) as image:
            fmt = image.format or ""
            image.load()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as err:
        msg = f"cannot decode image: {err}"
        raise UploadRejectedError(msg) from err
    except Image.DecompressionBombError as err:
        msg = "image is too large to decode"
        raise UploadRejectedError(msg) from err
    ext = _EXT_BY_FORMAT.get(fmt)
    if ext is None:
        msg = f"unsupported image format: {fmt or 'unknown'}"
        raise UploadRejectedError(msg)
    return ext


def wine_card(wine: Wine) -> WineCard:
    """ORM ``Wine`` → ``WineCard``.

    Цвет — ``categories.name``, оттенок — ``wines.color``.
    """
    return WineCard(
        slug=wine.slug,
        title=wine.title,
        manufacturer=wine.manufacturer,
        color=wine.category.name,
        shade=wine.color,
        region=wine.region.name,
        grape_variety=wine.grape_variety,
        sweetness=wine.sweetness.name if wine.sweetness is not None else None,
        description=wine.description,
        public_rating=wine.public_rating,
        product_url=wine.product_url,
        image_url=wine.image_url,
        dishes=list(wine.dishes or []),
        alcohol_pct=float(wine.alcohol_pct) if wine.alcohol_pct is not None else None,
        serving_temperature=wine.serving_temperature,
    )


def _candidates(hits: Sequence[RankedHit]) -> list[Candidate]:
    return [
        Candidate(
            rank=rank,
            slug=hit["slug"],
            title=hit["title"],
            manufacturer=hit["manufacturer"],
            image_url=hit["image_path"],
            score=float(hit["score"]),
        )
        for rank, hit in enumerate(hits, start=1)
    ]


class CatalogProductService:
    """``ProductService`` на реальном каталоге.

    Справочники строятся один раз при создании (обновление = рестарт); там же
    чистится хранилище фото старше ``retention_days``. Каждый вызов открывает
    свою сессию БД через ``session_scope``.
    """

    def __init__(self, runtime: EvalRuntime, settings: ProductSettings) -> None:
        self._runtime = runtime
        self._settings = settings
        self._queries_dir = self._resolve(settings.storage.queries_dir)
        self._feedback_log = self._resolve(settings.feedback_log)
        self._queries_dir.mkdir(parents=True, exist_ok=True)
        removed = cleanup_expired(self._queries_dir, settings.storage.retention_days)
        if removed:
            logger.info("search storage retention: removed %d files", len(removed))
        with session_scope(runtime.session_factory) as session:
            self._build_dictionaries(session)

    # --- ProductService -------------------------------------------------

    def search(
        self, image_path: Path, *, original_name: str | None = None
    ) -> SearchResult:
        """Распознать вино: сохранить фото, пайплайн eval, уровень, аналоги, JSON."""
        started = time.perf_counter()
        ext = image_extension(image_path)
        search_id = uuid.uuid4().hex
        stored_photo = self._queries_dir / f"{search_id}{ext}"
        shutil.copyfile(image_path, stored_photo)
        thresholds = self._settings.confidence

        def log_fields(decision: PolicyDecision) -> dict[str, object]:
            status, level = classify_confidence(decision.score_1, thresholds)
            return {
                "search_id": search_id,
                "status": status,
                "confidence_level": level,
                "endpoint": _ENDPOINT,
                "original_name": original_name,
            }

        try:
            run = run_search(
                self._runtime, stored_photo, log_fields=log_fields, emit_log=False
            )
        except Exception:
            stored_photo.unlink(missing_ok=True)
            raise
        decision = run.decision
        status, level = classify_confidence(decision.score_1, thresholds)
        candidates = _candidates(decision.hits)
        hints, hint_lines = self._hints(run) if status != "found" else (None, None)

        winner: WineCard | None = None
        analogs: AnalogsResult | None = None
        try:
            with session_scope(self._runtime.session_factory) as session:
                repo = WineRepository(session)
                if status != "not_found":
                    wine = repo.get_by_slug(decision.slug)
                    if wine is None:
                        msg = f"winner slug missing from catalog: {decision.slug}"
                        raise RuntimeError(msg)
                    winner = wine_card(wine)
                if hints is not None:
                    analogs = self._hint_analogs(
                        repo,
                        hints,
                        winner_slug=winner.slug if winner is not None else None,
                        limit=self._settings.analogs.limit,
                    )
        finally:
            fields = dict(log_fields(decision))
            fields.update(self._analogs_log_fields(hints, hint_lines, analogs))
            log_search(self._runtime, run, fields)

        result = SearchResult(
            search_id=search_id,
            created_at=datetime.now(UTC),
            status=status,
            confidence_level=level,
            score_1=decision.score_1,
            margin=decision.margin,
            winner=winner,
            candidates=candidates,
            analogs=analogs,
            rerank_triggered=decision.rerank_triggered,
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )
        self._persist(result)
        return result

    def get_search(self, search_id: str) -> SearchResult | None:
        """Сохранённый результат по точному id или ``None``."""
        path = result_path(self._queries_dir, search_id)
        if path is None or not path.is_file():
            return None
        return SearchResult.model_validate_json(path.read_text(encoding="utf-8"))

    def query_photo_path(self, search_id: str) -> Path | None:
        """Фото запроса по точному id (uuid4 hex) или ``None``."""
        return photo_path(self._queries_dir, search_id)

    def analogs_for(self, search_id: str, *, limit: int = 5) -> AnalogsResult:
        """Аналоги (контракт §4.2): один фильтр — один сорт, без OCR-вызова.

        found — сорт победителя из БД, исключая его производителя; иначе —
        сорт из сохранённых OCR-подсказок поиска.
        """
        result = self.get_search(search_id)
        if result is None:
            msg = f"unknown search_id: {search_id!r}"
            raise SearchNotFoundError(msg)
        with session_scope(self._runtime.session_factory) as session:
            repo = WineRepository(session)
            if result.status == "found" and result.winner is not None:
                return self._winner_analogs(repo, result.winner, limit=limit)
            hints = result.analogs.hints if result.analogs is not None else OcrHints()
            return self._hint_analogs(
                repo,
                hints,
                winner_slug=result.winner.slug if result.winner is not None else None,
                limit=limit,
            )

    def get_wine(self, slug: str) -> WineCard | None:
        """Карточка вина по slug или ``None``."""
        with session_scope(self._runtime.session_factory) as session:
            wine = WineRepository(session).get_by_slug(slug)
            return wine_card(wine) if wine is not None else None

    def find_wines(
        self, filters: CatalogFilters, *, limit: int = 5, offset: int = 0
    ) -> tuple[list[WineCard], int]:
        """Вина по фильтрам: рейтинг по убыванию (NULL в конце), затем id; + total."""
        with session_scope(self._runtime.session_factory) as session:
            return self._find(WineRepository(session), filters, limit, offset)

    def dictionaries(self) -> Dictionaries:
        """Справочники, собранные при старте сервиса."""
        return self._dictionaries

    def record_feedback(self, feedback: FeedbackIn) -> None:
        """Дописать отзыв строкой JSONL; неизвестный поиск → ``SearchNotFoundError``."""
        result = self.get_search(feedback.search_id)
        if result is None:
            msg = f"unknown search_id: {feedback.search_id!r}"
            raise SearchNotFoundError(msg)
        winner_slug = result.winner.slug if result.winner is not None else None
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "search_id": feedback.search_id,
            "slug": feedback.slug if feedback.slug is not None else winner_slug,
            "verdict": feedback.verdict,
            "status": result.status,
            "confidence_level": result.confidence_level,
            "winner_slug": winner_slug,
        }
        line = json.dumps(record, ensure_ascii=False) + "\n"
        self._feedback_log.parent.mkdir(parents=True, exist_ok=True)
        with self._feedback_log.open("a", encoding="utf-8") as handle:
            handle.write(line)

    # --- internals ------------------------------------------------------

    def _resolve(self, path_value: str) -> Path:
        path = Path(path_value)
        return path if path.is_absolute() else self._runtime.repo_root / path

    def _build_dictionaries(self, session: Session) -> None:
        # Only lookup values that at least one wine uses (filters never return 0).
        colors = session.scalars(select(Category.name).join(Category.wines).distinct())
        regions = session.scalars(select(Region.name).join(Region.wines).distinct())
        sweetness = session.scalars(
            select(SweetnessLevel.name).join(SweetnessLevel.wines).distinct()
        )
        self._colors = build_vocabulary(colors)
        self._regions = build_vocabulary(regions)
        self._sweetness = build_vocabulary(sweetness)
        grape_rows = [
            grape
            for variety in session.scalars(select(Wine.grape_variety))
            for grape in split_grapes(variety)
        ]
        self._grapes = build_vocabulary(grape_rows)
        grape_counts = Counter(
            name for name in map(self._grapes.canonical, grape_rows) if name
        )
        self._grape_families = build_grape_families(
            self._grapes.values, grape_counts, self._settings.analogs.color_synonyms
        )
        self._grape_families_by_key = {
            value_key(head): members for head, members in self._grape_families.items()
        }
        self._dishes = build_vocabulary(
            str(dish)
            for dish in session.scalars(select(func.unnest(Wine.dishes)))
            if dish
        )
        self._manufacturers = sorted(
            {m for m in session.scalars(select(Wine.manufacturer).distinct()) if m}
        )
        self._grape_aliases: dict[str, list[str]] = {}
        for key, aliases in self._settings.analogs.grape_aliases.items():
            grape = self._grapes.canonical(key)
            if grape is None:
                logger.warning("analogs.grape_aliases: unknown grape %r ignored", key)
                continue
            self._grape_aliases.setdefault(grape, []).extend(aliases)
        self._dictionaries = Dictionaries(
            colors=list(self._colors.values),
            grapes=list(self._grapes.values),
            regions=list(self._regions.values),
            sweetness=list(self._sweetness.values),
            dishes=list(self._dishes.values),
        )
        logger.info(
            "product dictionaries: %d colors, %d grapes, %d regions, "
            "%d sweetness, %d dishes, %d manufacturers",
            len(self._colors.values),
            len(self._grapes.values),
            len(self._regions.values),
            len(self._sweetness.values),
            len(self._dishes.values),
            len(self._manufacturers),
        )

    def _hints(self, run: SearchRun) -> tuple[OcrHints, list[str] | None]:
        """OCR-подсказки неизвестного вина + строки OCR, по которым они собраны.

        Нет OCR / сбой → ``ocr_ran=False`` и строки ``None``.
        """
        decision = run.decision
        if decision.rerank_reason in _OCR_SKIPPED:
            logger.warning("analogs OCR skipped: %s", decision.rerank_reason)
            return OcrHints(ocr_ran=False), None
        lines: list[str] | None = list(decision.ocr_lines)
        if not decision.rerank_triggered:
            try:
                lines = recognize_crop(self._runtime, run.bundle.crop_path)
            except OCRUnavailableError as err:
                logger.warning("analogs OCR failed: %s", err)
                return OcrHints(ocr_ran=False), None
            except Exception:
                logger.exception("analogs OCR failed")
                return OcrHints(ocr_ran=False), None
        if lines is None:
            logger.warning("analogs OCR skipped: no OCR engine")
            return OcrHints(ocr_ran=False), None
        hints = extract_hints(
            lines,
            reranker=self._runtime.reranker,
            color_synonyms=self._settings.analogs.color_synonyms,
            grapes=self._grapes.values,
            manufacturers=self._manufacturers,
            ocr_ran=True,
            grape_aliases=self._grape_aliases,
            grape_families=self._grape_families,
        )
        return hints, lines

    def _analogs_log_fields(
        self,
        hints: OcrHints | None,
        lines: list[str] | None,
        analogs: AnalogsResult | None,
    ) -> dict[str, object]:
        """Поля decision log про аналоги неизвестного вина (OCR, подсказки, фильтр)."""
        cap = self._runtime.ocr_rerank.decision_log.ocr_lines_cap
        return {
            "analogs_ocr_lines": lines[:cap] if lines is not None else None,
            "analogs_hints": hints.model_dump() if hints is not None else None,
            "analogs_grape": analogs.filters.grape if analogs is not None else None,
            "analogs_total": analogs.total if analogs is not None else None,
        }

    def _hint_analogs(
        self,
        repo: WineRepository,
        hints: OcrHints,
        *,
        winner_slug: str | None,
        limit: int,
    ) -> AnalogsResult:
        """Неизвестное вино: фильтр — первый OCR-сорт или его семейство (без цвета)."""
        filters = CatalogFilters(
            grape=self._analogs_grape(hints.grapes),
            exclude_slugs=[winner_slug] if winner_slug is not None else [],
        )
        return self._grape_analogs(repo, "ocr_filters", filters, hints, limit)

    def _analogs_grape(self, grapes: Sequence[str]) -> str | None:
        """Сорт для фильтра аналогов: всё семейство («Каберне») → имя семейства."""
        if not grapes:
            return None
        if len(grapes) > 1:
            for head, members in self._grape_families.items():
                if list(grapes) == members:
                    return head
        return grapes[0]

    def _winner_analogs(
        self, repo: WineRepository, winner: WineCard, *, limit: int
    ) -> AnalogsResult:
        """Известное вино: первый сорт победителя, другие производители (без цвета)."""
        grapes = split_grapes(winner.grape_variety)
        grape = self._grapes.canonical(grapes[0]) if grapes else None
        filters = CatalogFilters(
            grape=grape,
            exclude_manufacturer=winner.manufacturer,
            exclude_slugs=[winner.slug],
        )
        hints = OcrHints(
            color=winner.color, grapes=[grape] if grape else [], ocr_ran=False
        )
        return self._grape_analogs(repo, "winner_filters", filters, hints, limit)

    def _grape_analogs(
        self,
        repo: WineRepository,
        source: AnalogSource,
        filters: CatalogFilters,
        hints: OcrHints,
        limit: int,
    ) -> AnalogsResult:
        """Один запрос по сорту; нет сорта → пусто без запроса в БД; без повторов."""
        wines: list[WineCard] = []
        total = 0
        if filters.grape is not None:
            wines, total = self._find(repo, filters, limit, 0)
        return AnalogsResult(
            source=source, filters=filters, hints=hints, wines=wines, total=total
        )

    def _find(
        self,
        repo: WineRepository,
        filters: CatalogFilters,
        limit: int,
        offset: int,
    ) -> tuple[list[WineCard], int]:
        kwargs = self._filter_kwargs(filters)
        total = repo.count_filters(**kwargs)
        if total == 0 or limit <= 0:
            return [], total
        wines: Sequence[Wine] = repo.search_filters(
            **kwargs, sort_by_rating="desc", limit=limit, offset=offset
        )
        return [wine_card(w) for w in wines], total

    def _filter_kwargs(self, filters: CatalogFilters) -> _FilterKwargs:
        def one(vocab: Vocabulary, value: str | None) -> str | None:
            if value is None:
                return None
            variants = vocab.resolve(value)
            return variants[0] if variants else value

        def many(vocab: Vocabulary, value: str | None) -> list[str] | None:
            if value is None:
                return None
            return list(vocab.resolve(value)) or [value]

        def grapes_any(value: str | None) -> list[str] | None:
            members = (
                self._grape_families_by_key.get(value_key(value))
                if value is not None and not self._grapes.resolve(value)
                else None
            )
            if members is None:
                return many(self._grapes, value)
            return [variant for m in members for variant in self._grapes.resolve(m)]

        return {
            "category_name": one(self._colors, filters.color),
            "region_name": one(self._regions, filters.region),
            "sweetness_name": one(self._sweetness, filters.sweetness),
            "grape_names_any": grapes_any(filters.grape),
            "dishes_any": many(self._dishes, filters.dish),
            "exclude_manufacturer": filters.exclude_manufacturer,
            "exclude_slugs": list(filters.exclude_slugs) or None,
        }

    def _persist(self, result: SearchResult) -> None:
        path = self._queries_dir / f"{result.search_id}.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(result.model_dump_json(), encoding="utf-8")
        tmp.replace(path)
