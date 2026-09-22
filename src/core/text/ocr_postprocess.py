"""Нормализация шумных OCR-строк перед fuzzy-матчингом и confidence."""

from __future__ import annotations

import re
from collections.abc import Sequence

_PUNCT_OR_DIGIT_ONLY = re.compile(r"^[\W\d_]+$", re.UNICODE)
_SINGLE_LETTER_TOKEN = re.compile(r"^[A-Za-zА-Яа-яЁё]$")


def postprocess_ocr_lines(
    lines: Sequence[str],
    *,
    min_line_chars: int,
    drop_spaced_letters: bool,
) -> list[str]:
    """Схлопнуть spaced letters, отбросить шум, дедуп без учёта регистра.

    Args:
        lines: Сырые OCR-строки (по одной на элемент).
        min_line_chars: Отбросить строки короче этого после normalize/collapse.
        drop_spaced_letters: True — склеивать серии однобуквенных токенов
            (например ``"Б Ю Р Н Ь Б"`` → ``"бюрньб"``).
    """
    cleaned: list[str] = []
    seen_lower: set[str] = set()
    for raw in lines:
        line = _normalize_line(raw, drop_spaced_letters=drop_spaced_letters)
        if not line:
            continue
        if len(line) < min_line_chars:
            continue
        if _PUNCT_OR_DIGIT_ONLY.match(line.replace(" ", "")):
            continue
        key = line.casefold()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        cleaned.append(line)
    return cleaned


def _normalize_line(text: str, *, drop_spaced_letters: bool) -> str:
    collapsed = " ".join(text.split())
    if not collapsed:
        return ""
    if drop_spaced_letters:
        collapsed = _collapse_spaced_single_letters(collapsed)
    return collapsed.casefold().replace("ё", "е")


def _collapse_spaced_single_letters(text: str) -> str:
    """Join consecutive single Cyrillic/Latin letters separated by spaces."""
    tokens = text.split(" ")
    if not tokens:
        return text
    out: list[str] = []
    run: list[str] = []

    def flush_run() -> None:
        nonlocal run
        if not run:
            return
        if len(run) >= 2:
            out.append("".join(run).casefold())
        else:
            out.append(run[0])
        run = []

    for token in tokens:
        if _SINGLE_LETTER_TOKEN.fullmatch(token):
            run.append(token)
            continue
        flush_run()
        out.append(token)
    flush_run()
    return " ".join(out)
