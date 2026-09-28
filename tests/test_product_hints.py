"""PROD-API A — OCR-подсказки для аналогов (без БД и моделей)."""

from __future__ import annotations

import pytest

from core.config import load_ocr_rerank_settings
from core.product.hints import (
    extract_color,
    extract_grapes,
    extract_hints,
    extract_manufacturer,
)
from core.product.vocabulary import build_vocabulary, split_grapes
from core.text.fuzzy import FuzzyReranker

# Test-local synonym map (same shape as product.yaml analogs.color_synonyms).
COLOR_SYNONYMS: dict[str, list[str]] = {
    "Красное": ["красное", "красн", "red", "rosso", "tinto", "rouge"],
    "Белое": ["белое", "бел", "white", "bianco", "blanco", "blanc"],
    "Розовое": ["розовое", "розе", "rose", "rosé", "rosado", "rosato"],
    "Оранжевое": ["оранжевое", "orange", "arancione", "naranja"],
}

GRAPES = [
    "Каберне Совиньон",
    "Мерло",
    "Пино Гри",
    "Пино Нуар",
    "Совиньон Блан",
    "Мускат",
    "Мускат Белый",
]

MANUFACTURERS = [
    "Винодельня Фанагория",
    "Шато Тамань",
    "Усадьба Дивноморское",
]


@pytest.fixture(scope="module")
def reranker() -> FuzzyReranker:
    settings = load_ocr_rerank_settings()
    return FuzzyReranker(
        settings.field_weights,
        settings.fuzzy,
        min_line_chars=settings.ocr.min_line_chars,
        drop_spaced_letters=settings.ocr.drop_spaced_letters,
    )


# --- color ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (["КРАСНОЕ СУХОЕ"], "Красное"),
        (["ВИНО СУХОЕ КРАСНОГО ЦВЕТА"], "Красное"),
        (["ROSÉ"], "Розовое"),
        (["rose"], "Розовое"),
        (["BLANC DE BLANCS"], "Белое"),
        (["VINO ARANCIONE"], "Оранжевое"),
    ],
)
def test_color_synonyms(lines: list[str], expected: str) -> None:
    """[TEST-ID] PA-A1 синонимы цвета → categories.name."""
    assert extract_color(lines, COLOR_SYNONYMS) == expected


@pytest.mark.parametrize(
    "lines",
    [[], [""], ["VINO"], ["СУХОЕ 2019 0,75 L"], ["Фанагория"]],
)
def test_color_none_without_synonym(lines: list[str]) -> None:
    """[TEST-ID] PA-A1b нет синонима → None."""
    assert extract_color(lines, COLOR_SYNONYMS) is None


def test_color_empty_map_gives_none() -> None:
    """[TEST-ID] PA-A1c цвет без синонимов в карте не выводится."""
    assert extract_color(["КРАСНОЕ"], {}) is None


# --- grapes --------------------------------------------------------------


def test_grape_latin_alias(reranker: FuzzyReranker) -> None:
    """[TEST-ID] PA-A2 «CABERNET SAUVIGNON» → «Каберне Совиньон» (alias)."""
    assert extract_grapes(["CABERNET SAUVIGNON"], GRAPES, reranker) == [
        "Каберне Совиньон"
    ]


def test_grape_partial_name_not_matched(reranker: FuzzyReranker) -> None:
    """[TEST-ID] PA-A2b «ПИНО» alone не даёт «Пино Гри» / «Пино Нуар»."""
    got = extract_grapes(["ПИНО"], GRAPES, reranker)
    assert "Пино Гри" not in got
    assert "Пино Нуар" not in got
    assert got == []


def test_grape_more_specific_first(reranker: FuzzyReranker) -> None:
    """[TEST-ID] PA-A2c «МУСКАТ БЕЛЫЙ» → более конкретный сорт первым."""
    got = extract_grapes(["МУСКАТ БЕЛЫЙ"], GRAPES, reranker)
    assert got[0] == "Мускат Белый"
    assert set(got) <= {"Мускат Белый", "Мускат"}


def test_grape_blend_on_label(reranker: FuzzyReranker) -> None:
    """[TEST-ID] PA-A2d бленд на этикетке → оба сорта справочника."""
    got = extract_grapes(["Каберне Совиньон / Мерло"], GRAPES, reranker)
    assert set(got) == {"Каберне Совиньон", "Мерло"}


def test_grape_none(reranker: FuzzyReranker) -> None:
    """[TEST-ID] PA-A2e нет строк / справочника → []."""
    assert extract_grapes([], GRAPES, reranker) == []
    assert extract_grapes(["МЕРЛО"], [], reranker) == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Каберне Совиньон, Мерло", ["Каберне Совиньон", "Мерло"]),
        ("Каберне Фран; Саперави", ["Каберне Фран", "Саперави"]),
        ("Шардоне/Алиготе", ["Шардоне", "Алиготе"]),
        ("Мерло + Каберне Совиньон", ["Мерло", "Каберне Совиньон"]),
        ("  Рислинг  ", ["Рислинг"]),
        ("н/д", []),
        ("", []),
    ],
)
def test_split_grapes_blends(raw: str, expected: list[str]) -> None:
    """[TEST-ID] PA-A2f бленды в справочнике разбиваются по ,;/+ ; «н/д» → []."""
    assert split_grapes(raw) == expected


def test_grape_vocabulary_from_blends_dedup() -> None:
    """[TEST-ID] PA-A2g справочник сортов из блендов: без дублей и регистровых копий."""
    raw = ["Каберне Совиньон, Мерло", "мерло", "Мерло; Саперави", "н/д"]
    vocab = build_vocabulary(g for v in raw for g in split_grapes(v))
    assert list(vocab.values) == ["Каберне Совиньон", "Мерло", "Саперави"]
    assert set(vocab.resolve("МЕРЛО")) == {"Мерло", "мерло"}
    assert all("," not in v and v.strip() == v and v for v in vocab.values)


# --- manufacturer --------------------------------------------------------


def test_manufacturer_stopword_alone_is_none(reranker: FuzzyReranker) -> None:
    """[TEST-ID] PA-A3 «ВИНОДЕЛЬНЯ» / «ШАТО» alone → None (стоп-слова)."""
    assert extract_manufacturer(["ВИНОДЕЛЬНЯ"], MANUFACTURERS, reranker) is None
    assert extract_manufacturer(["ШАТО"], MANUFACTURERS, reranker) is None
    assert extract_manufacturer(["УСАДЬБА ВИНО"], MANUFACTURERS, reranker) is None


def test_manufacturer_compact_match(reranker: FuzzyReranker) -> None:
    """[TEST-ID] PA-A3b слитный OCR «ФАНАГОРИЯ» / «ШАТОТАМАНЬ» → производитель."""
    assert (
        extract_manufacturer(["ФАНАГОРИЯ"], MANUFACTURERS, reranker)
        == "Винодельня Фанагория"
    )
    assert (
        extract_manufacturer(["ШАТОТАМАНЬ"], MANUFACTURERS, reranker) == "Шато Тамань"
    )


def test_manufacturer_no_lines(reranker: FuzzyReranker) -> None:
    """[TEST-ID] PA-A3c нет строк → None."""
    assert extract_manufacturer([], MANUFACTURERS, reranker) is None


def test_extract_hints_combined(reranker: FuzzyReranker) -> None:
    """[TEST-ID] PA-A4 extract_hints собирает OcrHints."""
    hints = extract_hints(
        ["ФАНАГОРИЯ", "CABERNET SAUVIGNON", "КРАСНОЕ СУХОЕ"],
        reranker=reranker,
        color_synonyms=COLOR_SYNONYMS,
        grapes=GRAPES,
        manufacturers=MANUFACTURERS,
        ocr_ran=True,
    )
    assert hints.color == "Красное"
    assert hints.grapes == ["Каберне Совиньон"]
    assert hints.manufacturer == "Винодельня Фанагория"
    assert hints.ocr_ran is True
