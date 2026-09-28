"""PROD-API A — OCR-подсказки для аналогов (без БД и моделей)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.config import AnalogSettings, load_ocr_rerank_settings, load_product_settings
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


# --- grape_aliases (fix1) ------------------------------------------------

ALIAS_GRAPES = [
    "Каберне Совиньон",
    "Гевюрцтраминер",
    "Пино Гри",
    "Пино Нуар",
    "Санджовезе",
]
GRAPE_ALIASES: dict[str, list[str]] = {
    "Санджовезе": ["sangiovese"],
    "Пино Нуар": ["pinot noir", "pinot nero"],
    "Гевюрцтраминер": ["gewurztraminer"],
}


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (["SANGIOVESE"], ["Санджовезе"]),
        (["PINOT NOIR"], ["Пино Нуар"]),
        (["Pinot Nero"], ["Пино Нуар"]),
        (["NERO PINOT"], ["Пино Нуар"]),  # word order is free
        (["PINOT"], []),
        (["ПИНО"], []),
        (["PINOT GRIS"], ["Пино Гри"]),
        (["CABERNET SAUVIGNON"], ["Каберне Совиньон"]),
        (["GEWÜRZTRAMINER"], ["Гевюрцтраминер"]),
        (["ROSSO DI TOSCANA 2019"], []),
    ],
)
def test_grape_aliases_latin(
    reranker: FuzzyReranker, lines: list[str], expected: list[str]
) -> None:
    """[TEST-ID] PA-A5-fix1 латинские алиасы: фраза целиком, алиас → только свой ключ.
    """
    assert extract_grapes(lines, ALIAS_GRAPES, reranker, GRAPE_ALIASES) == expected


def test_grape_alias_pinot_gris_not_noir(reranker: FuzzyReranker) -> None:
    """[TEST-ID] PA-A5b-fix1 «PINOT GRIS» → «Пино Гри», не «Пино Нуар»."""
    got = extract_grapes(["PINOT GRIS"], ALIAS_GRAPES, reranker, GRAPE_ALIASES)
    assert "Пино Гри" in got
    assert "Пино Нуар" not in got


def test_grape_alias_key_outside_dictionary_ignored(reranker: FuzzyReranker) -> None:
    """[TEST-ID] PA-A5c-fix1 ключ алиаса вне справочника не выводится."""
    got = extract_grapes(
        ["SANGIOVESE"], ["Мерло"], reranker, {"Санджовезе": ["sangiovese"]}
    )
    assert got == []


@pytest.mark.parametrize(
    "lines",
    [
        ["CABERNET SAUVIGNON"],
        ["ПИНО"],
        ["МУСКАТ БЕЛЫЙ"],
        ["Каберне Совиньон / Мерло"],
        ["SANGIOVESE"],
        ["PINOT NOIR"],
        [],
    ],
)
@pytest.mark.parametrize("empty", [None, {}])
def test_grape_aliases_absent_backward_compatible(
    reranker: FuzzyReranker, lines: list[str], empty: dict | None
) -> None:
    """[TEST-ID] PA-A5d-fix1 без grape_aliases (None / {}) — как до fix1."""
    assert extract_grapes(lines, GRAPES, reranker, empty) == extract_grapes(
        lines, GRAPES, reranker
    )


def test_extract_hints_with_aliases(reranker: FuzzyReranker) -> None:
    """[TEST-ID] PA-A5e-fix1 extract_hints передаёт grape_aliases в extract_grapes."""
    hints = extract_hints(
        ["SANGIOVESE", "ROSSO"],
        reranker=reranker,
        color_synonyms=COLOR_SYNONYMS,
        grapes=ALIAS_GRAPES,
        manufacturers=MANUFACTURERS,
        ocr_ran=True,
        grape_aliases=GRAPE_ALIASES,
    )
    assert hints.grapes == ["Санджовезе"]
    assert hints.color == "Красное"
    without = extract_hints(
        ["SANGIOVESE", "ROSSO"],
        reranker=reranker,
        color_synonyms=COLOR_SYNONYMS,
        grapes=ALIAS_GRAPES,
        manufacturers=MANUFACTURERS,
        ocr_ran=True,
    )
    assert without.grapes == []


def test_repo_product_yaml_grape_aliases_load() -> None:
    """[TEST-ID] PA-A5f-fix1 product.yaml грузится, grape_aliases непусты и валидны."""
    settings = load_product_settings()
    aliases = settings.analogs.grape_aliases
    assert aliases
    assert aliases["Санджовезе"] == ["sangiovese"]
    assert set(aliases["Пино Нуар"]) == {"pinot noir", "pinot nero"}
    assert all(key.strip() and values for key, values in aliases.items())
    assert all(a.strip() for values in aliases.values() for a in values)


@pytest.mark.parametrize(
    "bad", [{"": ["x"]}, {"Мерло": ["merlot", " "]}]
)
def test_grape_aliases_validation(bad: dict[str, list[str]]) -> None:
    """[TEST-ID] PA-A5g-fix1 пустой ключ / пустой алиас → ValidationError."""
    with pytest.raises(ValidationError):
        AnalogSettings(limit=5, grape_aliases=bad)
