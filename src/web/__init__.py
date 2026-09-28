"""Веб-интерфейс (Jinja2, серверный рендер) поверх ``ProductService``."""

from web.router import router
from web.templating import STATIC_DIR

__all__ = ["STATIC_DIR", "router"]
