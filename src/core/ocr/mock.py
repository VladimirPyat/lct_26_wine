"""No-op OCR, когда ``ocr_backend`` равен ``mock``."""

from core.ocr.base import IOCREngine


class MockOCREngine(IOCREngine):
    """Не возвращает текст; не бросает на отсутствующем или нечитаемом файле."""

    def recognize(self, image_path: str) -> list[str]:
        """Вернуть пустой список строк. ``image_path`` игнорируется."""
        return []
