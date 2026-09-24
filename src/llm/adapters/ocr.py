"""OCR adapter: LLM task ``ocr_label`` as ``IOCREngine``."""

from __future__ import annotations

from pathlib import Path

from core.ocr.base import IOCREngine
from llm.engine import LLMEngine
from llm.factory import create_llm_engine


class LLMOCREngine(IOCREngine):
    """Распознавание этикетки через LLM-задачу (``create_llm_engine``).

    Caller passes only a task name; provider URL/model live in task YAML.
    """

    def __init__(
        self,
        task_name: str = "ocr_label",
        *,
        engine: LLMEngine | None = None,
    ) -> None:
        """Создать адаптер.

        Args:
            task_name: Имя YAML-задачи под ``src/llm/tasks/``.
            engine: Готовый ``LLMEngine`` (для тестов); иначе factory по ``task_name``.
        """
        if not task_name.strip():
            msg = "task_name must be a non-empty string"
            raise ValueError(msg)
        self._task_name = task_name
        self._engine = engine if engine is not None else create_llm_engine(task_name)

    def recognize(self, image_path: str) -> list[str]:
        """Вернуть непустые stripped-строки текста с этикетки."""
        source = Path(image_path)
        if not source.is_file():
            msg = f"Image not found for OCR: {image_path}"
            raise FileNotFoundError(msg)
        return self._engine.complete(image_path=str(source))
