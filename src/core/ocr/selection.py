"""Выбор OCR-движка при старте: цепочка CUDA → PHOCR, иначе LLM, иначе без OCR."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from core.ocr.base import IOCREngine
from core.ocr.mock import MockOCREngine

EffectiveOcr = Literal["phocr", "llm", "mock", "none"]


@dataclass(frozen=True)
class OcrSelection:
    """Итог выбора: эффективный движок, причина для лога, готовый движок (если есть).

    Для ``phocr`` движок ``None`` — он строится лениво при первом rerank.
    """

    effective: EffectiveOcr
    reason: str
    engine: IOCREngine | None = None


def select_ocr_engine(
    configured: str,
    *,
    cuda_available: bool,
    llm_probe: Callable[[], IOCREngine],
) -> OcrSelection:
    """Чистая функция выбора движка по ``ocr_engine.md`` «Engine selection».

    ``llm_probe`` создаёт LLM-движок без сетевого вызова; любая ошибка
    инициализации (нет ключа, нет YAML задачи, ошибка клиента) → ``none``.
    Сообщение ошибки фабрики называет только имя переменной окружения.
    """
    name = configured.strip().lower()
    if name == "mock":
        return OcrSelection("mock", "configured_mock", MockOCREngine())
    if name == "phocr":
        if cuda_available:
            return OcrSelection("phocr", "cuda_available")
        return _probe_llm(llm_probe, ok_reason="no_cuda")
    if name == "llm":
        return _probe_llm(llm_probe, ok_reason="configured_llm")
    msg = f"Unknown ocr.engine {configured!r}; expected phocr | llm | mock"
    raise ValueError(msg)


def _probe_llm(
    llm_probe: Callable[[], IOCREngine], *, ok_reason: str
) -> OcrSelection:
    try:
        engine = llm_probe()
    except Exception as err:  # any init error → OCR disabled, never a crash
        return OcrSelection("none", f"llm_unavailable: {type(err).__name__}: {err}")
    return OcrSelection("llm", ok_reason, engine)
