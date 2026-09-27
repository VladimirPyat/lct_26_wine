"""Pure image preprocess helpers shared by the encoder and offline scripts."""

from __future__ import annotations

import cv2
import numpy as np


def letterbox_rgb(
    rgb: np.ndarray,
    size: int,
    fill: tuple[int, int, int],
) -> np.ndarray:
    """Scale longest side to ``size`` and center on a ``size``×``size`` canvas.

    Matches the training notebooks (albumentations ``LongestMaxSize`` +
    ``PadIfNeeded``): ``round`` for the new side, ``INTER_LINEAR``, fill in RGB.
    """
    h, w = rgb.shape[:2]
    scale = size / max(h, w)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    resized = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
    out = np.full((size, size, 3), fill, dtype=np.uint8)
    top, left = (size - nh) // 2, (size - nw) // 2
    out[top : top + nh, left : left + nw] = resized
    return out
