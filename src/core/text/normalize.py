"""Общая нормализация OCR / каталожных строк для fuzzy и text-confidence."""

from __future__ import annotations

import re
from collections.abc import Iterable

# Cyrillic → Latin (cheap, no extra dependency). Multi-char mapped in a second pass.
_CYR_TO_LAT = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)

# Global stop list is off. Words like «красное» / «белое» / «сухое» / «reserve»
# distinguish sibling SKUs. Tokens shared by the whole shortlist are zeroed
# later by shortlist IDF, not by a fixed list.
GENERIC_STOPWORDS: frozenset[str] = frozenset()

# Bidirectional grape / brand token aliases (Latin ↔ Cyrillic OCR mix).
_TOKEN_ALIASES: dict[str, str] = {
    "cabernet": "каберне",
    "sauvignon": "совиньон",
    "sauvigni": "совиньон",
    "merlot": "мерло",
    "merlo": "мерло",
    "chardonnay": "шардоне",
    "riesling": "рислинг",
    "saperavi": "саперави",
    "pinot": "пино",
    "noir": "нуар",
    "blanc": "блан",
    "gris": "гри",
    "syrah": "сира",
    "shiraz": "шираз",
    "muscat": "мускат",
    "tempranillo": "темпранильо",
    "alma": "альма",
    "valley": "долина",
    "almavalley": "альмадолина",
    "inkerman": "инкерман",
    "gravi": "гравити",
    "gravity": "гравити",
    "chateau": "шато",
    "reserve": "резерв",
    "резерв": "reserve",
    "arena": "арена",
    "арена": "arena",
    "esse": "ессе",
    "unplugged": "unpluggbd",
}

_TOKEN_SPLIT = re.compile(r"[^\w]+", re.UNICODE)
_NON_ALNUM = re.compile(r"[^a-z0-9а-я]+", re.IGNORECASE)


def normalize_text(text: str) -> str:
    """Нижний регистр, ё→е, схлопывание пробелов."""
    lowered = text.lower().replace("ё", "е")
    return " ".join(lowered.split())


def transliterate_cyrillic(text: str) -> str:
    """Транслит кириллицы в латиницу после normalize."""
    return normalize_text(text).translate(_CYR_TO_LAT)


def compact_alnum(text: str) -> str:
    """Убрать пробелы и пунктуацию для склеенных OCR-токенов (например almavalley)."""
    return _NON_ALNUM.sub("", normalize_text(text))


def tokenize(text: str, *, min_len: int) -> list[str]:
    """Разрезать на буквенно-цифровые токены и отбросить короткие."""
    return [
        token
        for token in _TOKEN_SPLIT.split(normalize_text(text))
        if len(token) >= min_len and token not in GENERIC_STOPWORDS
    ]


def expand_token_aliases(token: str) -> set[str]:
    """Токен плюс транслит/compact-формы и известные алиасы."""
    base = normalize_text(token)
    out: set[str] = {base, transliterate_cyrillic(base), compact_alnum(base)}
    alias = _TOKEN_ALIASES.get(base)
    if alias is not None:
        out.add(alias)
        out.add(transliterate_cyrillic(alias))
        out.add(compact_alnum(alias))
    for key, value in _TOKEN_ALIASES.items():
        if base in {key, value}:
            out.add(key)
            out.add(value)
            out.add(transliterate_cyrillic(key))
            out.add(transliterate_cyrillic(value))
            out.add(compact_alnum(key))
            out.add(compact_alnum(value))
    return {item for item in out if item}


def text_variants(text: str) -> set[str]:
    """Нормализованные / транслитерированные / compact-варианты целой строки."""
    normalized = normalize_text(text)
    if not normalized:
        return set()
    return {
        normalized,
        transliterate_cyrillic(normalized),
        compact_alnum(normalized),
    }


def is_generic_field(field_norm: str, *, short_field_len: int) -> bool:
    """True, если поле каталога короткое / в основном generic wine-слова."""
    if not field_norm:
        return True
    tokens = field_norm.split()
    if len(field_norm) <= short_field_len and any(
        token in GENERIC_STOPWORDS for token in tokens
    ):
        return True
    return len(compact_alnum(field_norm)) <= short_field_len // 2


def primary_ocr_lines(lines: Iterable[str], *, max_lines: int) -> list[str]:
    """Предпочесть более длинные brand/title-строки; отбросить чистые стоп-слова."""
    normalized = [normalize_text(line) for line in lines]
    normalized = [line for line in normalized if line]
    content = [
        line
        for line in normalized
        if any(token not in GENERIC_STOPWORDS for token in tokenize(line, min_len=3))
    ]
    if not content:
        content = normalized
    content.sort(key=len, reverse=True)
    if max_lines < 1:
        return content
    return content[:max_lines]
