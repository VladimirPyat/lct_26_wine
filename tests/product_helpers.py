"""Общие хелперы тестов PROD-API: настройки в tmp_path, фикстуры SearchResult."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from core.config import (
    AnalogSettings,
    ConfidenceSettings,
    ProductSettings,
    StorageSettings,
    UploadSettings,
    load_ocr_rerank_settings,
)
from core.product.catalog_service import CatalogProductService
from core.product.schemas import (
    AnalogsResult,
    Candidate,
    OcrHints,
    SearchResult,
    WineCard,
)
from core.text.fuzzy import FuzzyReranker
from db.session import create_db_engine, create_session_factory

COLOR_SYNONYMS: dict[str, list[str]] = {
    "Красное": ["красное", "красн", "red"],
    "Белое": ["белое", "бел", "white"],
    "Розовое": ["розовое", "rose"],
}


def make_settings(
    tmp_path: Path,
    *,
    high_min: float = 0.8,
    medium_min: float = 0.65,
    not_found_min: float = 0.5,
    max_mb: float = 1.0,
) -> ProductSettings:
    """Настройки продукта с путями внутри ``tmp_path`` (не prod YAML)."""
    return ProductSettings(
        confidence=ConfidenceSettings(
            high_min=high_min, medium_min=medium_min, not_found_min=not_found_min
        ),
        analogs=AnalogSettings(limit=5, color_synonyms=COLOR_SYNONYMS),
        storage=StorageSettings(
            queries_dir=str(tmp_path / "search_queries"), retention_days=10
        ),
        feedback_log=str(tmp_path / "search_feedback.jsonl"),
        upload=UploadSettings(
            max_mb=max_mb, content_types=["image/jpeg", "image/png", "image/webp"]
        ),
    )


def fake_card(slug: str = "test-wine", manufacturer: str = "Тест") -> WineCard:
    return WineCard(
        slug=slug,
        title=f"Вино {slug}",
        manufacturer=manufacturer,
        color="Красное",
        shade="Рубиновый",
        region="Крым",
        grape_variety="Мерло",
        sweetness="Сухое",
        description="",
        public_rating=4.0,
        product_url=None,
        image_url=f"/static/wines/{slug}.webp",
        alcohol_pct=None,
        serving_temperature=None,
    )


def make_result(
    *,
    status: str = "found",
    winner: WineCard | None = None,
    candidates: list[Candidate] | None = None,
    hints: OcrHints | None = None,
    search_id: str | None = None,
) -> SearchResult:
    """``SearchResult`` для хранилища (аналоги с подсказками для low / not_found)."""
    level = {"found": "high", "low": "low", "not_found": "low"}[status]
    analogs = None
    if status != "found":
        analogs = AnalogsResult(
            source="ocr_filters",
            filters={},
            hints=hints or OcrHints(),
            wines=[],
            total=0,
        )
    return SearchResult(
        search_id=search_id or uuid.uuid4().hex,
        created_at=datetime.now(UTC),
        status=status,  # type: ignore[arg-type]
        confidence_level=level,  # type: ignore[arg-type]
        score_1=0.9 if status == "found" else 0.55,
        margin=0.1,
        winner=winner if status != "not_found" else None,
        candidates=candidates or [],
        analogs=analogs,
        rerank_triggered=False,
        latency_ms=1.0,
    )


def build_reranker() -> FuzzyReranker:
    """FuzzyReranker из ``ocr_rerank.yaml`` (как в рантайме)."""
    settings = load_ocr_rerank_settings()
    return FuzzyReranker(
        settings.field_weights,
        settings.fuzzy,
        min_line_chars=settings.ocr.min_line_chars,
        drop_spaced_letters=settings.ocr.drop_spaced_letters,
    )


def build_db_service(tmp_path: Path) -> CatalogProductService:
    """CatalogProductService на реальной БД без моделей; БД недоступна → skip."""
    engine = create_db_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM wines LIMIT 1"))
    except Exception as err:  # noqa: BLE001 - any DB failure is an env skip
        engine.dispose()
        pytest.skip(f"Postgres unavailable: {type(err).__name__}")
    runtime = SimpleNamespace(
        repo_root=tmp_path,
        session_factory=create_session_factory(engine),
        reranker=build_reranker(),
        engine=engine,
    )
    return CatalogProductService(runtime, make_settings(tmp_path))  # type: ignore[arg-type]


def store_result(queries_dir: Path, result: SearchResult) -> Path:
    """Записать ``{id}.json`` так же, как сервис."""
    queries_dir.mkdir(parents=True, exist_ok=True)
    path = queries_dir / f"{result.search_id}.json"
    path.write_text(result.model_dump_json(), encoding="utf-8")
    return path
