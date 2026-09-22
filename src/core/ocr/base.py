"""Абстрактный контракт OCR-движка."""

from abc import ABC, abstractmethod


class IOCREngine(ABC):
    """Распознавание текста на изображении этикетки."""

    @abstractmethod
    def recognize(self, image_path: str) -> list[str]:
        """Вернуть распознанные строки текста из изображения ``image_path``."""
