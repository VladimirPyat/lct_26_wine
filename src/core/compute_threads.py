"""Лимиты потоков OpenCV и ONNX Runtime из ``compute.cv_threads`` / ``ort_threads``.

``0`` — не трогать библиотечный дефолт (все ядра). Подходит для dev.
``>0`` — жёсткий лимит; на prod ставят по числу ядер сервера, учитывая
``process_pool_max_workers`` (каждый воркер умножает потоки).
"""

from __future__ import annotations

import logging

import cv2
import onnxruntime as ort

logger = logging.getLogger(__name__)


def apply_cv_thread_limit(cv_threads: int) -> None:
    """Вызвать ``cv2.setNumThreads`` только если лимит > 0."""
    if cv_threads < 0:
        msg = f"compute.cv_threads must be >= 0 (0 = unlimited), got {cv_threads}"
        raise ValueError(msg)
    if cv_threads == 0:
        return
    cv2.setNumThreads(cv_threads)
    logger.info("OpenCV threads limited to %s", cv_threads)


def onnx_session_options(ort_threads: int) -> ort.SessionOptions | None:
    """``SessionOptions`` с ``intra_op_num_threads``, либо ``None`` если 0."""
    if ort_threads < 0:
        msg = f"compute.ort_threads must be >= 0 (0 = unlimited), got {ort_threads}"
        raise ValueError(msg)
    if ort_threads == 0:
        return None
    options = ort.SessionOptions()
    options.intra_op_num_threads = ort_threads
    options.inter_op_num_threads = 1
    logger.info("ONNX Runtime intra_op threads limited to %s", ort_threads)
    return options
