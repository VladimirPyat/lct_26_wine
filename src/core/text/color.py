"""Цвет вина по строкам OCR (словарь синонимов → ``categories.name``)."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence

from core.text.normalize import normalize_text

WORD_SPLIT = re.compile(r"[^\w]+", re.UNICODE)
_CYRILLIC = re.compile(r"[а-я]")
# Russian color words inflect (красное / красного / красный): a Cyrillic
# synonym also matches as a prefix when the ending adds at most this many letters.
_MAX_INFLECTION = 3


def fold(text: str) -> str:
    """normalize_text + снятие диакритики (rosé → rose)."""
    decomposed = unicodedata.normalize("NFKD", normalize_text(text))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def ocr_words(lines: Sequence[str]) -> list[str]:
    """Слова OCR после ``fold`` (без пустых)."""
    words: list[str] = []
    for line in lines:
        words.extend(word for word in WORD_SPLIT.split(fold(line)) if word)
    return words


def synonym_hits(word: str, synonym: str) -> bool:
    """Слово совпадает с синонимом (кириллица — ещё и с окончанием до 3 букв)."""
    if word == synonym:
        return True
    return (
        bool(_CYRILLIC.search(synonym))
        and word.startswith(synonym)
        and len(word) - len(synonym) <= _MAX_INFLECTION
    )


def extract_color(
    lines: Sequence[str], color_synonyms: Mapping[str, Sequence[str]]
) -> str | None:
    """Цвет каталога (``categories.name``) по словарю синонимов.

    Побеждает цвет с наибольшим числом совпавших слов; при равенстве —
    первый в порядке словаря. Нет совпадений → ``None``.
    """
    words = ocr_words(lines)
    best: str | None = None
    best_hits = 0
    for color, synonyms in color_synonyms.items():
        folded = [fold(s) for s in synonyms if fold(s)]
        hits = sum(1 for word in words if any(synonym_hits(word, s) for s in folded))
        if hits > best_hits:
            best, best_hits = color, hits
    return best
