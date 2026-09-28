"""Окружение Jinja2 для веб-интерфейса: автоэкранирование и фильтры."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, StrictUndefined, Undefined

WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

GlassState = Literal["full", "empty"]

_RATING_MAX = 5
_CONFIDENCE_LABELS: dict[str, str] = {
    "high": "Высокая уверенность",
    "medium": "Средняя уверенность",
    "low": "Низкая уверенность — возможно, это не то вино",
}


def confidence_label(level: str) -> str:
    """Текстовая метка уровня уверенности (без процентов)."""
    return _CONFIDENCE_LABELS.get(level, "Уверенность не определена")


def rating_glasses(rating: float | None) -> list[GlassState]:
    """Пять «бокалов» для рейтинга 0..5; ``None`` → пустой список («нет оценок»)."""
    if rating is None:
        return []
    filled = max(0, min(_RATING_MAX, int(rating + 0.5)))
    full: list[GlassState] = ["full"] * filled
    empty: list[GlassState] = ["empty"] * (_RATING_MAX - filled)
    return full + empty


def rating_text(rating: float | None) -> str:
    """Рейтинг одной цифрой после запятой («4,3») или пустая строка."""
    if rating is None:
        return ""
    return f"{rating:.1f}".replace(".", ",")


def num(value: float | None) -> str:
    """Число без лишних нулей с десятичной запятой («13», «12,5»)."""
    if value is None:
        return ""
    return f"{value:g}".replace(".", ",")


def is_http_url(value: object) -> bool:
    """``True`` только для абсолютных ссылок ``http://`` / ``https://``."""
    if not isinstance(value, str):
        return False
    lowered = value.strip().lower()
    return lowered.startswith(("http://", "https://")) and len(lowered) > len(
        "https://"
    )


def _build_environment() -> Environment:
    strict = os.environ.get("VINE_WEB_STRICT") == "1"
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
        undefined=StrictUndefined if strict else Undefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["confidence_label"] = confidence_label
    env.filters["rating_glasses"] = rating_glasses
    env.filters["rating_text"] = rating_text
    env.filters["num"] = num
    env.filters["is_http_url"] = is_http_url
    env.tests["http_url"] = is_http_url
    return env


templates = Jinja2Templates(env=_build_environment())
