"""OCR-подсказки для аналогов: цвет, сорта, производитель (без БД и OCR-движка)."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence

from core.product.schemas import OcrHints
from core.text.fuzzy import FuzzyReranker
from core.text.normalize import compact_alnum, normalize_text, tokenize

_WORD_SPLIT = re.compile(r"[^\w]+", re.UNICODE)
_CYRILLIC = re.compile(r"[а-я]")
# Russian color words inflect (красное / красного / красный): a Cyrillic
# synonym also matches as a prefix when the ending adds at most this many letters.
_MAX_INFLECTION = 3
_GRAPE_TOKEN_MIN_LEN = 3


def _fold(text: str) -> str:
    """normalize_text + снятие диакритики (rosé → rose)."""
    decomposed = unicodedata.normalize("NFKD", normalize_text(text))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _ocr_words(lines: Sequence[str]) -> list[str]:
    words: list[str] = []
    for line in lines:
        words.extend(word for word in _WORD_SPLIT.split(_fold(line)) if word)
    return words


def _synonym_hits(word: str, synonym: str) -> bool:
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
    """Цвет каталога (``categories.name``) по словарю синонимов из ``product.yaml``.

    Побеждает цвет с наибольшим числом совпавших слов; при равенстве —
    первый в порядке YAML. Нет совпадений → ``None``.
    """
    words = _ocr_words(lines)
    best: str | None = None
    best_hits = 0
    for color, synonyms in color_synonyms.items():
        folded = [_fold(s) for s in synonyms if _fold(s)]
        hits = sum(1 for word in words if any(_synonym_hits(word, s) for s in folded))
        if hits > best_hits:
            best, best_hits = color, hits
    return best


def extract_grapes(
    lines: Sequence[str], grapes: Sequence[str], reranker: FuzzyReranker
) -> list[str]:
    """Сорта справочника, все токены которых есть в OCR (как ``label_evidence``).

    Более конкретные названия (больше токенов) идут первыми: «Мускат Белый»
    раньше «Мускат». Внутри одинаковой длины — порядок справочника.
    """
    if not lines or not grapes:
        return []
    by_norm = {normalize_text(g): g for g in grapes if "," not in g}
    evidence = reranker.label_evidence(
        lines, title="", manufacturer="", grape_variety=", ".join(by_norm.values())
    )
    matched = [by_norm[name] for name in evidence.grapes if name in by_norm]
    order = {grape: index for index, grape in enumerate(grapes)}
    return sorted(
        dict.fromkeys(matched),
        key=lambda g: (-len(tokenize(g, min_len=_GRAPE_TOKEN_MIN_LEN)), order[g]),
    )


def extract_manufacturer(
    lines: Sequence[str], manufacturers: Sequence[str], reranker: FuzzyReranker
) -> str | None:
    """Производитель каталога, подтверждённый OCR (compact / токен, ``label_evidence``).

    Несколько совпадений → больше доля слов названия, дословно найденных в OCR;
    при равенстве — самое длинное compact-название (наиболее конкретное).
    """
    if not lines:
        return None
    matched = [
        name
        for name in manufacturers
        if reranker.label_evidence(
            lines, title="", manufacturer=name, grape_variety=""
        ).manufacturer
    ]
    if not matched:
        return None
    ocr_compact = compact_alnum(" ".join(lines))

    def verbatim_share(name: str) -> float:
        tokens = [
            compact_alnum(t) for t in tokenize(name, min_len=_GRAPE_TOKEN_MIN_LEN)
        ]
        tokens = [t for t in tokens if t]
        if not tokens:
            return 0.0
        return sum(1 for t in tokens if t in ocr_compact) / len(tokens)

    return max(
        matched, key=lambda name: (verbatim_share(name), len(compact_alnum(name)))
    )


def extract_hints(
    lines: Sequence[str],
    *,
    reranker: FuzzyReranker,
    color_synonyms: Mapping[str, Sequence[str]],
    grapes: Sequence[str],
    manufacturers: Sequence[str],
    ocr_ran: bool,
) -> OcrHints:
    """Собрать ``OcrHints`` из строк OCR."""
    return OcrHints(
        color=extract_color(lines, color_synonyms),
        grapes=extract_grapes(lines, grapes, reranker),
        manufacturer=extract_manufacturer(lines, manufacturers, reranker),
        ocr_ran=ocr_ran,
    )
