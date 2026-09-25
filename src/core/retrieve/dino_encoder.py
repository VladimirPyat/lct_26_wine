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
    Catalog encode batches via ``dino.encode_batch_size``.
    """

    def __init__(
        self,
        database: DatabaseSettings,
        compute: ComputeSettings,
        *,
        providers: list[str] | None = None,
        repo_root: Path | None = None,
        encode_batch_size: int | None = None,
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
        if encode_batch_size is not None:
            if encode_batch_size < 1:
                msg = f"encode_batch_size must be >= 1, got {encode_batch_size}"
                raise ValueError(msg)
            self._encode_batch_size = encode_batch_size
        else:
            self._encode_batch_size = dino.encode_batch_size
        logger.info(
            "DINO ONNX providers=%s embedding_dim=%s input_size=%s "
            "encode_batch_size=%s",
            self._session.get_providers(),
            self._embedding_dim,
            self._input_size,
            self._encode_batch_size,
        )

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    @property
    def encode_batch_size(self) -> int:
        return self._encode_batch_size

    def encode_image(self, path: str) -> list[float]:
        """Return L2-normalized (if configured) pooler vector of ``embedding_dim``.

        Batch-of-one semantics: on failure raise (preserves callers that expect
        ``FileNotFoundError`` / ``RuntimeError``).
        """
        result = self.encode_images([path])[0]
        if result is not None:
            return result
        # Soft path returned None — re-run raising so callers keep exception types.
        chw = self._preprocess_path(path)
        nchw = np.ascontiguousarray(chw[np.newaxis, ...])
        outputs = self._session.run(
            [_OUTPUT_POOLER],
            {self._input_name: nchw},
        )
        return self._finalize_vector(np.asarray(outputs[0][0]), path)

    def encode_images(self, paths: Sequence[str]) -> list[list[float] | None]:
        """Encode many images; length always equals ``len(paths)``.

        Failed indices are ``None`` and do not abort siblings. Chunk size is
        ``encode_batch_size``. On batched ORT error, falls back to serial
        ``session.run`` for that micro-batch's OK tensors.
        """
        results: list[list[float] | None] = [None] * len(paths)
        chunk = self._encode_batch_size
        for start in range(0, len(paths), chunk):
            slice_paths = paths[start : start + chunk]
            ok_indices: list[int] = []
            ok_chw: list[np.ndarray] = []
            for offset, path in enumerate(slice_paths):
                global_i = start + offset
                try:
                    ok_chw.append(self._preprocess_path(path))
                    ok_indices.append(global_i)
                except (FileNotFoundError, OSError, RuntimeError) as exc:
                    logger.debug(
                        "DINO preprocess skip index=%s path=%s: %s",
                        global_i,
                        path,
                        exc,
                    )
                    results[global_i] = None

            if not ok_chw:
                continue

            stacked = np.ascontiguousarray(np.stack(ok_chw, axis=0))
            try:
                outputs = self._session.run(
                    [_OUTPUT_POOLER],
                    {self._input_name: stacked},
                )
                batch_out = np.asarray(outputs[0])
                for j, global_i in enumerate(ok_indices):
                    try:
                        results[global_i] = self._finalize_vector(
                            batch_out[j], paths[global_i]
                        )
                    except RuntimeError as exc:
                        logger.debug(
                            "DINO postprocess skip index=%s path=%s: %s",
                            global_i,
                            paths[global_i],
                            exc,
                        )
                        results[global_i] = None
            except Exception as exc:
                logger.warning(
                    "DINO batched ORT failed (size=%s); serial fallback: %s",
                    len(ok_chw),
                    exc,
                )
                for j, global_i in enumerate(ok_indices):
                    results[global_i] = self._run_one(ok_chw[j], paths[global_i])
        return results

    def _preprocess_path(self, path: str) -> np.ndarray:
        """Load image → CHW float32 (no batch dim). Raises on failure."""
        source = Path(path)
        if not source.is_file():
            msg = f"Image not found for DINO encode: {path}"
            raise FileNotFoundError(msg)

        image_bgr = cv2.imread(str(source))
        if image_bgr is None:
            msg = f"Failed to read image for DINO encode: {path}"
            raise FileNotFoundError(msg)
        return self._preprocess_chw(image_bgr)

    def _preprocess_chw(self, image_bgr: np.ndarray) -> np.ndarray:
        """BGR → RGB, resize square, ImageNet normalize, CHW (no batch)."""
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(
            rgb,
            (self._input_size, self._input_size),
            interpolation=cv2.INTER_LINEAR,
        )
        scaled = resized.astype(np.float32) / 255.0
        normalized = (scaled - self._mean) / self._std
        chw = np.transpose(normalized, (2, 0, 1))
        return np.ascontiguousarray(chw)

    def _finalize_vector(self, raw: np.ndarray, path: str) -> list[float]:
        vector = np.asarray(raw, dtype=np.float32).reshape(-1)
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

    def _run_one(self, chw: np.ndarray, path: str) -> list[float] | None:
        """Single-image ORT + finalize; ``None`` on ORT/postprocess failure."""
        nchw = np.ascontiguousarray(chw[np.newaxis, ...])
        try:
            outputs = self._session.run(
                [_OUTPUT_POOLER],
                {self._input_name: nchw},
            )
            return self._finalize_vector(np.asarray(outputs[0][0]), path)
        except Exception as exc:
            logger.debug("DINO serial ORT skip path=%s: %s", path, exc)
            return None


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
    *,
    encode_batch_size: int | None = None,
) -> DinoOnnxEncoder:
    """Build encoder from YAML defaults (database + compute_cropper)."""
    db = database if database is not None else load_database_settings()
    if compute is None:
        compute = load_app_settings().compute
    return DinoOnnxEncoder(db, compute, encode_batch_size=encode_batch_size)


_default_encoder: DinoOnnxEncoder | None = None


def encode_image(path: str) -> list[float]:
    """Encode with a process-wide default encoder (lazy-loaded from YAML)."""
    global _default_encoder
    if _default_encoder is None:
        _default_encoder = create_dino_encoder()
    return _default_encoder.encode_image(path)
