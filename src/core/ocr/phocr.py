"""PHOCR ONNX OCR (ленивый импорт; по умолчанию CPU, без torch)."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from pathlib import Path

import cv2
import numpy as np

from core.ocr.base import IOCREngine

logger = logging.getLogger(__name__)

_LANG_TO_LANGREC_ATTR: dict[str, str] = {
    "ch": "CH",
    "en": "EN",
    "ja": "JP",
    "jp": "JP",
    "ko": "KO",
    "ru": "RU",
    "th": "TH",
    "vi": "VI",
    "zh": "CH",
}

_PHOCR_INSTALL_HINT = "phocr is not installed; request: uv add phocr"


class PHOCREngine(IOCREngine):
    """Обёртка PHOCR.recognize как ``IOCREngine.recognize``."""

    def __init__(
        self,
        *,
        use_cuda: bool,
        lang: str,
        limit_side_len: int,
        ort_threads: int,
    ) -> None:
        """Лениво импортировать phocr и собрать движок.

        Модели грузятся здесь, не при import.

        ``lang`` и ``limit_side_len`` обязательны (прод передаёт ``ru``, YAML
        ``ocr.limit_side_len``). Числовых дефолтов нет.
        CUDA запрашивается только через параметры PHOCR — обёртка не импортирует torch.

        Args:
            use_cuda: True — просить CUDA у ONNX Runtime / PHOCR.
            lang: Код языка PHOCR LangRec (например ``ru``).
            limit_side_len: PHOCR ``Det.limit_side_len``.
            ort_threads: Лимит intra_op ONNX Runtime; ``0`` — дефолт PHOCR.
        """
        if not isinstance(limit_side_len, int) or limit_side_len <= 0:
            msg = f"limit_side_len must be a positive int, got {limit_side_len!r}"
            raise ValueError(msg)
        if not isinstance(ort_threads, int) or ort_threads < 0:
            msg = f"ort_threads must be >= 0 (0 = unlimited), got {ort_threads!r}"
            raise ValueError(msg)
        lang_code = _normalize_lang_code(lang)
        try:
            from phocr import PHOCR, LangRec
        except ImportError as err:
            raise ImportError(_PHOCR_INSTALL_HINT) from err

        lang_type = _langrec_member(LangRec, lang_code, lang)
        params: dict[str, object] = {
            "Rec.lang_type": lang_type,
            "Det.limit_side_len": limit_side_len,
        }
        if ort_threads > 0:
            params["EngineConfig.onnxruntime.intra_op_num_threads"] = ort_threads
            params["EngineConfig.onnxruntime.inter_op_num_threads"] = 1
        if use_cuda:
            _require_cuda_provider()
            # PHOCR demo wires CUDA through these keys; do not import torch.
            params["Rec.device"] = "cuda"
            params["EngineConfig.onnxruntime.use_cuda"] = True
            # Default kNextPowerOfTwo + EXHAUSTIVE conv search OOMs an 8GB GPU
            # when YOLO and PHOCR det share the same CUDA context.
            params["EngineConfig.onnxruntime.cuda_ep_cfg.arena_extend_strategy"] = (
                "kSameAsRequested"
            )
            params["EngineConfig.onnxruntime.cuda_ep_cfg.cudnn_conv_algo_search"] = (
                "DEFAULT"
            )
        self._engine = PHOCR(params=params)
        self._limit_side_len = limit_side_len
        self._use_cuda = use_cuda

    def recognize(self, image_path: str) -> list[str]:
        """Запустить PHOCR на ``image_path`` и вернуть непустые stripped-строки."""
        source = Path(image_path)
        if not source.is_file():
            msg = f"Image not found for OCR: {image_path}"
            raise FileNotFoundError(msg)
        payload: str | np.ndarray = str(source)
        if self._use_cuda:
            image_bgr = cv2.imread(str(source))
            if image_bgr is None:
                msg = f"Failed to read image for OCR: {image_path}"
                raise FileNotFoundError(msg)
            capped = _letterbox_cuda_det_input(image_bgr, self._limit_side_len)
            if capped is not image_bgr:
                src_h, src_w = image_bgr.shape[:2]
                out_h, out_w = capped.shape[:2]
                logger.info(
                    "PHOCR CUDA letterbox %sx%s -> %sx%s (limit_side_len=%s): %s",
                    src_w,
                    src_h,
                    out_w,
                    out_h,
                    self._limit_side_len,
                    source,
                )
                payload = capped
        result = self._engine(payload)
        return _lines_from_result(result)


def _letterbox_cuda_det_input(
    image_bgr: np.ndarray,
    limit_side_len: int,
) -> np.ndarray:
    """Keep PHOCR det off a tall min-side upsample that OOMs 8GB GPUs.

    PHOCR ``Det.limit_type=min`` scales the *short* side up to ``limit_side_len``.
    A 600×1600 crop becomes ~1150×3067. Letterbox so both sides are
    ``limit_side_len`` (YAML ``ocr.limit_side_len``) — one bounded CUDA tensor.
    CPU OCR is unchanged.
    """
    height, width = image_bgr.shape[:2]
    long_side = max(height, width)
    # Small shop crops stay on PHOCR min-side upsample (~1150×1700). Only tall
    # phone frames (long side already above the YAML limit) get letterboxed.
    if long_side <= limit_side_len:
        return image_bgr

    scale = limit_side_len / float(long_side)
    new_w = max(1, int(round(width * scale)))
    new_h = max(1, int(round(height * scale)))
    resized = cv2.resize(image_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    pad_h = max(0, limit_side_len - new_h)
    pad_w = max(0, limit_side_len - new_w)
    if pad_h == 0 and pad_w == 0:
        return resized
    top = pad_h // 2
    left = pad_w // 2
    return cv2.copyMakeBorder(
        resized,
        top,
        pad_h - top,
        left,
        pad_w - left,
        cv2.BORDER_CONSTANT,
        value=(114, 114, 114),
    )


def _require_cuda_provider() -> None:
    """Fail fast when CUDA is requested but ONNX Runtime cannot provide it."""
    try:
        import onnxruntime as ort
    except ImportError as err:
        msg = "CUDA requested but onnxruntime is not installed"
        raise ValueError(msg) from err
    if "CUDAExecutionProvider" not in ort.get_available_providers():
        msg = (
            "CUDA requested but ONNX Runtime CUDAExecutionProvider is "
            "not available; install phocr[cuda] or onnxruntime-gpu"
        )
        raise ValueError(msg)


def _normalize_lang_code(lang: str) -> str:
    code = lang.strip().lower()
    if not code:
        msg = "lang is required (e.g. 'ru'); no default is applied"
        raise ValueError(msg)
    if code not in _LANG_TO_LANGREC_ATTR:
        known = ", ".join(sorted(_LANG_TO_LANGREC_ATTR))
        msg = f"Unknown OCR language {lang!r}. Known codes: {known}"
        raise ValueError(msg)
    return code


def _langrec_member(lang_rec_cls: type, lang_code: str, original: str) -> object:
    attr_name = _LANG_TO_LANGREC_ATTR[lang_code]
    try:
        return getattr(lang_rec_cls, attr_name)
    except AttributeError as err:
        msg = (
            f"PHOCR LangRec has no member {attr_name} for lang {original!r}; "
            "cannot map this language"
        )
        raise ValueError(msg) from err


def _lines_from_result(result: object) -> list[str]:
    """Turn a PHOCR result into non-empty stripped lines (no markdown headings).

    Try in order: ``txts``, ``texts``, ``text`` (splitlines), then ``to_markdown()``.
    """
    for attr in ("txts", "texts"):
        value = getattr(result, attr, None)
        if value is not None:
            return _normalize_lines(value)

    text = getattr(result, "text", None)
    if text is not None:
        if isinstance(text, str):
            return _normalize_lines(text.splitlines())
        return _normalize_lines(text)

    to_markdown = getattr(result, "to_markdown", None)
    if callable(to_markdown):
        markdown = to_markdown()
        if not isinstance(markdown, str):
            msg = (
                "to_markdown() returned "
                f"{type(markdown).__name__}, expected str"
            )
            raise TypeError(msg)
        return _lines_from_markdown(markdown)

    msg = (
        "PHOCR result has no usable txts, texts, text, or to_markdown(); "
        f"got {type(result).__name__}"
    )
    raise TypeError(msg)


def _normalize_lines(items: object) -> list[str]:
    lines: list[str] = []
    for raw in _iter_raw_lines(items):
        stripped = raw.strip()
        if stripped:
            lines.append(stripped)
    return lines


def _iter_raw_lines(items: object) -> Iterator[str]:
    if isinstance(items, str):
        yield from items.splitlines()
        return
    if isinstance(items, (bytes, bytearray)):
        msg = (
            "OCR line payload must be str or an iterable of str, "
            f"got {type(items).__name__}"
        )
        raise TypeError(msg)
    if not isinstance(items, Iterable):
        msg = f"OCR line payload must be iterable, got {type(items).__name__}"
        raise TypeError(msg)
    for item in items:
        if isinstance(item, str):
            yield from item.splitlines()
        else:
            yield str(item)


def _lines_from_markdown(markdown: str) -> list[str]:
    lines: list[str] = []
    for raw in markdown.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines
