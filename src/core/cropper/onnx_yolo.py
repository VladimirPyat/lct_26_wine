"""ONNX Runtime YOLO-кроппер этикетки (без ultralytics)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict

import cv2
import numpy as np
import onnxruntime as ort

from core.compute_threads import onnx_session_options
from core.config import AppSettings
from core.contracts import CropResult, LabelCropper

logger = logging.getLogger(__name__)

_CPU_EP = "CPUExecutionProvider"
_CUDA_EP = "CUDAExecutionProvider"


class OnnxYoloCropper:
    """Детектирует бокс этикетки с наибольшей уверенностью и кропает, иначе passthrough.

    Пороги и пути читаются из ``AppSettings.cropper`` (YAML). Числовых дефолтов
    в Python нет. Имя файла кропа уникально, чтобы параллельные запросы с
    одним stem не перетирали друг друга. ORT EP выбирается по
    ``cropper.device`` (default YAML: ``cpu``); ``compute.device`` — только
    PHOCR/DINO.
    """

    def __init__(
        self,
        settings: AppSettings,
        *,
        providers: list[str] | None = None,
    ) -> None:
        model_path = Path(settings.yolo_model_path)
        if not model_path.is_file():
            msg = f"YOLO ONNX model not found: {model_path}"
            raise FileNotFoundError(msg)
        chosen = (
            list(providers)
            if providers is not None
            else select_yolo_onnx_providers(settings.cropper.device)
        )
        options = onnx_session_options(settings.compute.ort_threads)
        if options is None:
            self._session = ort.InferenceSession(str(model_path), providers=chosen)
        else:
            self._session = ort.InferenceSession(
                str(model_path),
                sess_options=options,
                providers=chosen,
            )
        self._input_name = self._session.get_inputs()[0].name
        self._output_name = self._session.get_outputs()[0].name
        logger.info("YOLO ONNX providers: %s", self._session.get_providers())
        cropper = settings.cropper
        self.confidence = cropper.confidence
        self.input_size = cropper.input_size
        self.letterbox_color = tuple(cropper.letterbox_color)
        self.output_dir = Path(cropper.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.box_area_min = cropper.box_area_min
        self.box_area_max = cropper.box_area_max
        self.box_conf_keep_ratio = cropper.box_conf_keep_ratio
        self.min_crop_side = cropper.min_crop_side

    def crop(self, image_path: str) -> CropResult:
        """Кроп лучшего бокса этикетки или исходный путь при fallback (query path)."""
        source = Path(image_path)
        if not source.is_file():
            msg = f"Image not found for cropping: {image_path}"
            raise FileNotFoundError(msg)

        image_bgr = cv2.imread(str(source))
        if image_bgr is None:
            msg = f"Failed to read image for cropping: {image_path}"
            raise FileNotFoundError(msg)

        bbox = self._detect_best_box(image_bgr)
        if bbox is None:
            logger.error(
                "YOLO crop fallback to full image reason=no_box path=%s",
                source,
            )
            return CropResult(cropped_path=str(source), used_fallback=True)

        x1, y1, x2, y2 = bbox
        cropped = image_bgr[y1:y2, x1:x2]
        if cropped.size == 0:
            logger.error(
                "YOLO crop fallback to full image reason=empty_crop path=%s",
                source,
            )
            return CropResult(cropped_path=str(source), used_fallback=True)

        dest = self.output_dir / f"{source.stem}_crop_{uuid.uuid4().hex}{source.suffix}"
        if not cv2.imwrite(str(dest), cropped):
            msg = f"Failed to write cropped image: {dest}"
            raise OSError(msg)
        return CropResult(cropped_path=str(dest), used_fallback=False)

    def crop_strict_to_path(
        self,
        image_path: str,
        dest: Path,
        *,
        min_side: int | None = None,
    ) -> tuple[bool, str, tuple[int, int] | None]:
        """Catalog crop: write label crop to ``dest``; never fall back to full frame.

        Returns ``(ok, reason, crop_wh)``. Reasons: ``ok``, ``no_box``,
        ``empty_crop``, ``too_small``, ``write_fail``, ``read_fail``.
        """
        side = self.min_crop_side if min_side is None else min_side
        source = Path(image_path)
        image_bgr = cv2.imread(str(source))
        if image_bgr is None:
            return False, "read_fail", None

        bbox = self._detect_best_box(image_bgr)
        if bbox is None:
            return False, "no_box", None

        x1, y1, x2, y2 = bbox
        cropped = image_bgr[y1:y2, x1:x2]
        if cropped.size == 0:
            return False, "empty_crop", None

        height, width = cropped.shape[:2]
        crop_wh = (width, height)
        if width < side or height < side:
            return False, "too_small", crop_wh

        dest.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(dest), cropped):
            return False, "write_fail", crop_wh
        return True, "ok", crop_wh

    def _detect_best_box(
        self, image_bgr: np.ndarray
    ) -> tuple[int, int, int, int] | None:
        tensor, scale, pad_x, pad_y = _letterbox(
            image_bgr, self.input_size, self.letterbox_color
        )
        outputs = self._session.run(
            [self._output_name],
            {self._input_name: tensor},
        )[0]
        return _best_box_xyxy(
            outputs[0],
            confidence=self.confidence,
            scale=scale,
            pad_x=pad_x,
            pad_y=pad_y,
            orig_w=image_bgr.shape[1],
            orig_h=image_bgr.shape[0],
            area_min=self.box_area_min,
            area_max=self.box_area_max,
            conf_keep_ratio=self.box_conf_keep_ratio,
        )


def _letterbox(
    image_bgr: np.ndarray,
    size: int,
    color: tuple[int, ...],
) -> tuple[np.ndarray, float, int, int]:
    """Масштаб с сохранением пропорций и серым паддингом (как Ultralytics)."""
    height, width = image_bgr.shape[:2]
    scale = min(size / width, size / height)
    new_w = int(round(width * scale))
    new_h = int(round(height * scale))
    resized = cv2.resize(image_bgr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    pad_x = (size - new_w) // 2
    pad_y = (size - new_h) // 2
    padded = np.full((size, size, 3), color, dtype=np.uint8)
    padded[pad_y : pad_y + new_h, pad_x : pad_x + new_w] = resized
    rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
    chw = np.transpose(rgb, (2, 0, 1)).astype(np.float32) / 255.0
    batch = np.expand_dims(chw, axis=0)
    return np.ascontiguousarray(batch), scale, pad_x, pad_y


class YoloBox(TypedDict):
    """Decoded YOLO box in original-image pixels."""

    conf: float
    area: float
    dist: float
    xyxy: tuple[int, int, int, int]


def _best_box_xyxy(
    output: np.ndarray,
    *,
    confidence: float,
    scale: float,
    pad_x: int,
    pad_y: int,
    orig_w: int,
    orig_h: int,
    area_min: float,
    area_max: float,
    conf_keep_ratio: float,
) -> tuple[int, int, int, int] | None:
    """Разобрать выход YOLOv8 ONNX ``[4 + num_classes, num_preds]``.

    Сначала кандидаты ``score >= confidence``. Если есть боксы с долей
    площади кадра в ``[area_min, area_max]`` и ``conf >= max_conf *
    conf_keep_ratio``, взять из них максимум ``conf * (1 - dist_to_center)``
    (этикетка ближе к центру кадра). Иначе — прежний argmax confidence.
    """
    decoded = _decode_yolo_boxes(
        output,
        confidence=confidence,
        scale=scale,
        pad_x=pad_x,
        pad_y=pad_y,
        orig_w=orig_w,
        orig_h=orig_h,
    )
    if not decoded:
        return None
    chosen = select_label_box(
        decoded,
        area_min=area_min,
        area_max=area_max,
        conf_keep_ratio=conf_keep_ratio,
    )
    if chosen is None:
        return None
    return chosen["xyxy"]


def _decode_yolo_boxes(
    output: np.ndarray,
    *,
    confidence: float,
    scale: float,
    pad_x: int,
    pad_y: int,
    orig_w: int,
    orig_h: int,
) -> list[YoloBox]:
    """Декодировать боксы выше порога confidence в координаты исходника."""
    if output.ndim != 2:
        return []
    preds = output.T
    if preds.shape[1] < 5:
        return []
    scores = preds[:, 4]
    keep = scores >= confidence
    if not np.any(keep):
        return []
    filtered = preds[keep]
    frame_area = float(orig_w * orig_h)
    diag = float((orig_w**2 + orig_h**2) ** 0.5) or 1.0
    cx0, cy0 = orig_w / 2.0, orig_h / 2.0
    boxes: list[YoloBox] = []
    for row in filtered:
        cx, cy, width, height = (float(v) for v in row[:4])
        conf = float(row[4])
        x1 = (cx - width / 2.0 - pad_x) / scale
        y1 = (cy - height / 2.0 - pad_y) / scale
        x2 = (cx + width / 2.0 - pad_x) / scale
        y2 = (cy + height / 2.0 - pad_y) / scale
        x1_i = max(0, min(orig_w, int(round(x1))))
        y1_i = max(0, min(orig_h, int(round(y1))))
        x2_i = max(0, min(orig_w, int(round(x2))))
        y2_i = max(0, min(orig_h, int(round(y2))))
        if x2_i <= x1_i or y2_i <= y1_i:
            continue
        area = (x2_i - x1_i) * (y2_i - y1_i) / frame_area
        bcx = (x1_i + x2_i) / 2.0
        bcy = (y1_i + y2_i) / 2.0
        dist = (((bcx - cx0) ** 2 + (bcy - cy0) ** 2) ** 0.5) / diag
        boxes.append(
            YoloBox(
                conf=conf,
                area=area,
                dist=dist,
                xyxy=(x1_i, y1_i, x2_i, y2_i),
            )
        )
    return boxes


def select_label_box(
    boxes: list[YoloBox],
    *,
    area_min: float,
    area_max: float,
    conf_keep_ratio: float,
) -> YoloBox | None:
    """Этикеточный бокс: площадь в диапазоне, затем центр; иначе max conf."""
    if not boxes:
        return None
    max_conf = max(box["conf"] for box in boxes)
    keep_floor = max_conf * conf_keep_ratio
    label_like = [
        box
        for box in boxes
        if area_min <= box["area"] <= area_max and box["conf"] >= keep_floor
    ]
    pool = label_like or boxes

    def _center_score(box: YoloBox) -> float:
        return box["conf"] * (1.0 - box["dist"])

    if label_like:
        return max(pool, key=_center_score)
    return max(pool, key=lambda box: box["conf"])


def select_yolo_onnx_providers(
    device: str,
    *,
    available: Sequence[str] | None = None,
) -> list[str]:
    """Pick ORT providers for YOLO from ``cropper.device`` (cpu|cuda|auto)."""
    if available is not None:
        available_list = list(available)
    else:
        available_list = list(ort.get_available_providers())
    normalized = device.strip().lower()
    want_cuda = normalized in {"cuda", "auto"}
    if want_cuda and _CUDA_EP in available_list:
        return [_CUDA_EP, _CPU_EP]
    if normalized == "cuda":
        logger.warning(
            "cropper.device=cuda but %s unavailable; falling back to CPU",
            _CUDA_EP,
        )
    return [_CPU_EP]


def create_label_cropper(settings: AppSettings) -> LabelCropper:
    """Собрать ONNX-кроппер (EP из ``cropper.device``)."""
    return OnnxYoloCropper(settings)
