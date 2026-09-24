"""DINO ONNX image encoder (catalog + query embeddings)."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort  # type: ignore[import-untyped]

from core.compute_threads import onnx_session_options
from core.config import (
    ComputeSettings,
    DatabaseSettings,
    load_app_settings,
    load_database_settings,
)

logger = logging.getLogger(__name__)

_CPU_EP = "CPUExecutionProvider"
_CUDA_EP = "CUDAExecutionProvider"
_OUTPUT_POOLER = "pooler_output"


class DinoOnnxEncoder:
    """Encode a bottle/label image to a fixed-dim embedding via DINOv2 ONNX.

    Preprocess (resize + ImageNet normalize) comes from ``DatabaseSettings.dino``.
    ORT device/threads come from ``ComputeSettings`` (``compute_cropper.yaml``).
    """

    def __init__(
        self,
        database: DatabaseSettings,
        compute: ComputeSettings,
        *,
        providers: list[str] | None = None,
        repo_root: Path | None = None,
    ) -> None:
        if repo_root is not None:
            root = repo_root
        else:
            root = Path(__file__).resolve().parents[3]
        model_path = Path(database.dino_model_path)
        if not model_path.is_absolute():
            model_path = root / model_path
        if not model_path.is_file():
            msg = f"DINO ONNX model not found: {model_path}"
            raise FileNotFoundError(msg)

        chosen = (
            list(providers)
            if providers is not None
            else select_dino_onnx_providers(compute.device)
        )
        options = onnx_session_options(compute.ort_threads)
        if options is None:
            self._session = ort.InferenceSession(str(model_path), providers=chosen)
        else:
            self._session = ort.InferenceSession(
                str(model_path),
                sess_options=options,
                providers=chosen,
            )
        self._input_name = self._session.get_inputs()[0].name
        output_names = {out.name for out in self._session.get_outputs()}
        if _OUTPUT_POOLER not in output_names:
            msg = (
                f"DINO ONNX missing output {_OUTPUT_POOLER!r}; "
                f"have {sorted(output_names)}"
            )
            raise RuntimeError(msg)
        self._embedding_dim = database.embedding_dim
        dino = database.dino
        self._input_size = dino.input_size
        self._mean = np.asarray(dino.normalize_mean, dtype=np.float32)
        self._std = np.asarray(dino.normalize_std, dtype=np.float32)
        self._l2_normalize = dino.l2_normalize
        logger.info(
            "DINO ONNX providers=%s embedding_dim=%s input_size=%s",
            self._session.get_providers(),
            self._embedding_dim,
            self._input_size,
        )

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    def encode_image(self, path: str) -> list[float]:
        """Return L2-normalized (if configured) pooler vector of ``embedding_dim``."""
        source = Path(path)
        if not source.is_file():
            msg = f"Image not found for DINO encode: {path}"
            raise FileNotFoundError(msg)

        image_bgr = cv2.imread(str(source))
        if image_bgr is None:
            msg = f"Failed to read image for DINO encode: {path}"
            raise FileNotFoundError(msg)

        tensor = self._preprocess(image_bgr)
        outputs = self._session.run([_OUTPUT_POOLER], {self._input_name: tensor})
        vector = np.asarray(outputs[0][0], dtype=np.float32).reshape(-1)
        if vector.shape[0] != self._embedding_dim:
            msg = (
                f"DINO embedding dim mismatch: got {vector.shape[0]}, "
                f"expected {self._embedding_dim}"
            )
            raise RuntimeError(msg)
        if self._l2_normalize:
            norm = float(np.linalg.norm(vector))
            if norm <= 0.0:
                msg = f"DINO embedding has zero L2 norm for image: {path}"
                raise RuntimeError(msg)
            vector = vector / norm
        return vector.astype(np.float32).tolist()

    def _preprocess(self, image_bgr: np.ndarray) -> np.ndarray:
        """BGR → RGB, resize square, ImageNet normalize, NCHW batch."""
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(
            rgb,
            (self._input_size, self._input_size),
            interpolation=cv2.INTER_LINEAR,
        )
        scaled = resized.astype(np.float32) / 255.0
        normalized = (scaled - self._mean) / self._std
        chw = np.transpose(normalized, (2, 0, 1))
        return np.ascontiguousarray(chw[np.newaxis, ...])


def select_dino_onnx_providers(
    device: str,
    *,
    available: Sequence[str] | None = None,
) -> list[str]:
    """Pick ORT providers for DINO from ``compute.device``."""
    if available is not None:
        available_list = list(available)
    else:
        available_list = list(ort.get_available_providers())
    if device.lower() == "cuda" and _CUDA_EP in available_list:
        return [_CUDA_EP, _CPU_EP]
    if device.lower() == "cuda":
        logger.warning(
            "compute.device=cuda but %s unavailable; falling back to CPU",
            _CUDA_EP,
        )
    return [_CPU_EP]


def create_dino_encoder(
    database: DatabaseSettings | None = None,
    compute: ComputeSettings | None = None,
) -> DinoOnnxEncoder:
    """Build encoder from YAML defaults (database + compute_cropper)."""
    db = database if database is not None else load_database_settings()
    if compute is None:
        compute = load_app_settings().compute
    return DinoOnnxEncoder(db, compute)


_default_encoder: DinoOnnxEncoder | None = None


def encode_image(path: str) -> list[float]:
    """Encode with a process-wide default encoder (lazy-loaded from YAML)."""
    global _default_encoder
    if _default_encoder is None:
        _default_encoder = create_dino_encoder()
    return _default_encoder.encode_image(path)
