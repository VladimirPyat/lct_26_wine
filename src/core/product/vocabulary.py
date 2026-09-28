"""Справочники фильтров: нормализация, дедупликация и сортировка значений каталога."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from core.text.normalize import compact_alnum, normalize_text

_GRAPE_SPLIT = re.compile(r"[,;/+]")
# Placeholder «нет данных» — splitting on «/» would yield fake grapes «н», «д».
_GRAPE_MISSING = frozenset({"н/д", "нд", "n/a", "-"})
_MIN_KEY_CHARS = 2


def value_key(value: str) -> str:
    """Ключ дедупликации: регистр, ё/е, пробелы и пунктуация не важны."""
    return compact_alnum(value)


def sort_key(value: str) -> tuple[str, str]:
    """Сортировка без учёта регистра и ё/е (русские значения)."""
    return normalize_text(value), value


def split_grapes(grape_variety: str) -> list[str]:
    """Разбить ``grape_variety`` на сорта по ``,;/+``; «н/д» → пустой список."""
    text = grape_variety.strip()
    if normalize_text(text) in _GRAPE_MISSING:
        return []
    parts = (" ".join(part.split()) for part in _GRAPE_SPLIT.split(text))
    return [part for part in parts if len(value_key(part)) >= _MIN_KEY_CHARS]


def _display(value: str) -> str:
    return value[:1].upper() + value[1:] if value[:1].islower() else value


@dataclass(frozen=True)
class Vocabulary:
    """Нормализованный справочник: отображаемые значения + исходные варианты из БД."""

    values: tuple[str, ...]
    variants: dict[str, tuple[str, ...]]
    display: dict[str, str]

    def resolve(self, value: str) -> tuple[str, ...]:
        """Все исходные написания значения (для фильтра в БД); пусто, если нет."""
        return self.variants.get(value_key(value), ())

    def canonical(self, value: str) -> str | None:
        """Отображаемое значение справочника для произвольного написания."""
        return self.display.get(value_key(value))


def build_vocabulary(raw_values: Iterable[str]) -> Vocabulary:
    """Сгруппировать значения по ``value_key``; показать самое частое написание."""
    counts: Counter[str] = Counter()
    for raw in raw_values:
        value = " ".join(raw.split())
        if len(value_key(value)) >= _MIN_KEY_CHARS:
            counts[value] += 1
    groups: dict[str, list[str]] = {}
    for value, _count in counts.most_common():
        groups.setdefault(value_key(value), []).append(value)
    display = {key: _display(group[0]) for key, group in groups.items()}
    return Vocabulary(
        values=tuple(sorted(display.values(), key=sort_key)),
        variants={key: tuple(group) for key, group in groups.items()},
        display=display,
    )
