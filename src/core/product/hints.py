"""OCR-подсказки для аналогов: цвет, сорта, производитель (без БД и OCR-движка)."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from core.product.schemas import OcrHints
from core.product.vocabulary import value_key
from core.text.color import WORD_SPLIT as _WORD_SPLIT
from core.text.color import extract_color
from core.text.color import fold as _fold
from core.text.color import ocr_words as _ocr_words
from core.text.color import synonym_hits as _synonym_hits
from core.text.fuzzy import FuzzyReranker
from core.text.normalize import compact_alnum, normalize_text, tokenize

__all__ = [
    "build_grape_families",
    "extract_color",
    "extract_grapes",
    "extract_hints",
    "extract_manufacturer",
]

_GRAPE_TOKEN_MIN_LEN = 3
_FAMILY_SPLIT = re.compile(r"[\s\-]+")
# Same floor as fuzzy token matching (ocr_rerank.yaml hybrid.fuzzy.token_min_len).
_FAMILY_HEAD_MIN_LEN = 4


def _alias_matches(
    lines: Sequence[str],
    grapes: Sequence[str],
    grape_aliases: Mapping[str, Sequence[str]],
) -> list[str]:
    """Сорта справочника, чей латинский алиас целиком (все слова) есть в OCR.

    Алиас указывает только на свой ключ; порядок слов не важен.
    """
    words = set(_ocr_words(lines))
    in_dictionary = set(grapes)
    matched: list[str] = []
    for grape, aliases in grape_aliases.items():
        if grape not in in_dictionary:
            continue
        for alias in aliases:
            tokens = [t for t in _WORD_SPLIT.split(_fold(alias)) if t]
            if tokens and all(token in words for token in tokens):
                matched.append(grape)
                break
    return matched


def build_grape_families(
    grapes: Sequence[str],
    counts: Mapping[str, int],
    color_synonyms: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, list[str]]:
    """Семейства сортов по первому слову: «Каберне» → [«Каберне Совиньон», …].

    Только для многословных сортов, чьё первое слово (≥ 4 букв, как у fuzzy)
    само не является сортом справочника и не является цветом (``color_synonyms``:
    «Красные сорта винограда» не должно ловиться по «КРАСНОЕ»). Члены — по
    убыванию числа вин (``counts``), при равенстве — порядок справочника.
    """
    keys = {value_key(g) for g in grapes}
    colors = [
        _fold(s) for synonyms in (color_synonyms or {}).values() for s in synonyms
    ]
    order = {grape: index for index, grape in enumerate(grapes)}
    families: dict[str, list[str]] = {}
    for grape in grapes:
        words = _FAMILY_SPLIT.split(grape.strip())
        head = words[0]
        if len(words) < 2 or len(head) < _FAMILY_HEAD_MIN_LEN:
            continue
        if value_key(head) in keys:
            continue
        if any(_synonym_hits(_fold(head), color) for color in colors if color):
            continue
        families.setdefault(head.capitalize(), []).append(grape)
    for members in families.values():
        members.sort(key=lambda g: (-counts.get(g, 0), order[g]))
    return families


def extract_grapes(
    lines: Sequence[str],
    grapes: Sequence[str],
    reranker: FuzzyReranker,
    grape_aliases: Mapping[str, Sequence[str]] | None = None,
    grape_families: Mapping[str, Sequence[str]] | None = None,
) -> list[str]:
    """Сорта справочника, все токены которых есть в OCR (как ``label_evidence``).

    Дополнительно — латинские алиасы ``analogs.grape_aliases`` (фраза целиком).
    Более конкретные названия (больше токенов) идут первыми: «Мускат Белый»
    раньше «Мускат». Внутри одинаковой длины — порядок справочника.

    Если целиком не нашёлся ни один сорт, но на этикетке есть первое слово
    семейства (``grape_families``, тот же fuzzy) — возвращаются все сорта
    семейства: «КАБЕРНЕ» без второго слова → Каберне Совиньон, Каберне Фран.
    """
    if not lines or not grapes:
        return []
    by_norm = {normalize_text(g): g for g in grapes if "," not in g}
    evidence = reranker.label_evidence(
        lines, title="", manufacturer="", grape_variety=", ".join(by_norm.values())
    )
    matched = [by_norm[name] for name in evidence.grapes if name in by_norm]
    if grape_aliases:
        matched.extend(_alias_matches(lines, grapes, grape_aliases))
    if not matched and grape_families:
        return _family_matches(lines, reranker, grape_families)
    order = {grape: index for index, grape in enumerate(grapes)}
    return sorted(
        dict.fromkeys(matched),
        key=lambda g: (-len(tokenize(g, min_len=_GRAPE_TOKEN_MIN_LEN)), order[g]),
    )


def _family_matches(
    lines: Sequence[str],
    reranker: FuzzyReranker,
    grape_families: Mapping[str, Sequence[str]],
) -> list[str]:
    heads = {normalize_text(head): head for head in grape_families}
    evidence = reranker.label_evidence(
        lines, title="", manufacturer="", grape_variety=", ".join(heads.values())
    )
    matched: list[str] = []
    for name in evidence.grapes:
        if name in heads:
            matched.extend(grape_families[heads[name]])
    return list(dict.fromkeys(matched))


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
    grape_aliases: Mapping[str, Sequence[str]] | None = None,
    grape_families: Mapping[str, Sequence[str]] | None = None,
) -> OcrHints:
    """Собрать ``OcrHints`` из строк OCR."""
    return OcrHints(
        color=extract_color(lines, color_synonyms),
        grapes=extract_grapes(lines, grapes, reranker, grape_aliases, grape_families),
        manufacturer=extract_manufacturer(lines, manufacturers, reranker),
        ocr_ran=ocr_ran,
    )
