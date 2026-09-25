"""OPT-001 / OPT-002 — DINO batch encode + YOLO cropper.device providers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest
from pydantic import ValidationError

from core.config import (
    AppSettings,
    ComputeSettings,
    CropperSettings,
    DatabaseSettings,
    DinoPreprocessSettings,
    load_app_settings,
    load_database_settings,
)
from core.cropper.onnx_yolo import OnnxYoloCropper, select_yolo_onnx_providers
from core.retrieve.dino_encoder import DinoOnnxEncoder

_CPU = "CPUExecutionProvider"
_CUDA = "CUDAExecutionProvider"
_REPO = Path(__file__).resolve().parents[1]


def _dino_preprocess(**overrides: Any) -> DinoPreprocessSettings:
    base: dict[str, Any] = {
        "input_size": 8,
        "normalize_mean": (0.5, 0.5, 0.5),
        "normalize_std": (0.5, 0.5, 0.5),
        "l2_normalize": True,
        "encode_batch_size": 16,
    }
    base.update(overrides)
    return DinoPreprocessSettings.model_validate(base)


def _cropper_settings(**overrides: Any) -> CropperSettings:
    base: dict[str, Any] = {
        "device": "cpu",
        "confidence": 0.5,
        "input_size": 640,
        "letterbox_color": (114, 114, 114),
        "output_dir": "data/tmp/crops",
        "box_area_min": 0.05,
        "box_area_max": 0.50,
        "box_conf_keep_ratio": 0.85,
        "min_crop_side": 100,
        "catalog_crops_dir": "data/tmp/catalog_crops",
        "catalog_crops_review_dir": "data/tmp/catalog_crops_review",
    }
    base.update(overrides)
    return CropperSettings.model_validate(base)


def _stub_dino_encoder(
    *,
    encode_batch_size: int = 2,
    embedding_dim: int = 4,
    session: MagicMock | None = None,
) -> DinoOnnxEncoder:
    """Minimal encoder without loading a real ONNX session."""
    enc = object.__new__(DinoOnnxEncoder)
    enc._encode_batch_size = encode_batch_size
    enc._embedding_dim = embedding_dim
    enc._l2_normalize = True
    enc._input_name = "pixel_values"
    enc._input_size = 8
    enc._mean = np.zeros(3, dtype=np.float32)
    enc._std = np.ones(3, dtype=np.float32)
    if session is None:
        session = MagicMock()

        def _run(_names: list[str], feeds: dict[str, np.ndarray]) -> list[np.ndarray]:
            batch = int(feeds["pixel_values"].shape[0])
            # Non-zero so L2 normalize succeeds.
            return [np.full((batch, embedding_dim), 0.5, dtype=np.float32)]

        session.run.side_effect = _run
    enc._session = session
    return enc


# --- OPT-001: DINO batch -------------------------------------------------


def test_encode_batch_size_loads_from_yaml() -> None:
    """[OPT-001] dino.encode_batch_size from database.yaml default >= 1."""
    db = load_database_settings()
    assert db.dino.encode_batch_size >= 1
    assert db.dino.encode_batch_size == 16


def test_encode_batch_size_rejects_zero() -> None:
    """[OPT-001] pydantic Field(ge=1) rejects encode_batch_size=0."""
    with pytest.raises(ValidationError):
        _dino_preprocess(encode_batch_size=0)


def test_encode_images_return_length_matches_input() -> None:
    """[OPT-001] encode_images length always equals len(paths)."""
    enc = _stub_dino_encoder(encode_batch_size=2)
    chw = np.zeros((3, 8, 8), dtype=np.float32)

    def _prep(path: str) -> np.ndarray:
        if path == "missing.jpg":
            raise FileNotFoundError(path)
        return chw

    enc._preprocess_path = _prep  # type: ignore[method-assign]
    paths = ["a.jpg", "missing.jpg", "c.jpg"]
    out = enc.encode_images(paths)
    assert len(out) == len(paths)


def test_encode_images_missing_path_none_siblings_ok() -> None:
    """[OPT-001] bad preprocess → None at index; siblings still vectors."""
    enc = _stub_dino_encoder(encode_batch_size=4)
    chw = np.zeros((3, 8, 8), dtype=np.float32)

    def _prep(path: str) -> np.ndarray:
        if "missing" in path:
            raise FileNotFoundError(path)
        return chw

    enc._preprocess_path = _prep  # type: ignore[method-assign]
    out = enc.encode_images(["ok1.jpg", "missing.jpg", "ok2.jpg"])
    assert out[0] is not None
    assert isinstance(out[0], list)
    assert len(out[0]) == enc.embedding_dim
    assert out[1] is None
    assert out[2] is not None
    assert isinstance(out[2], list)


def test_encode_images_serial_fallback_on_batched_ort_error() -> None:
    """[OPT-001] batched session.run failure → serial per-OK tensor."""
    session = MagicMock()
    calls: list[int] = []

    def _run(_names: list[str], feeds: dict[str, np.ndarray]) -> list[np.ndarray]:
        batch = int(feeds["pixel_values"].shape[0])
        calls.append(batch)
        if batch > 1:
            raise RuntimeError("batch EP boom")
        return [np.full((1, 4), 0.25, dtype=np.float32)]

    session.run.side_effect = _run
    enc = _stub_dino_encoder(encode_batch_size=4, session=session)
    chw = np.zeros((3, 8, 8), dtype=np.float32)
    enc._preprocess_path = lambda _p: chw  # type: ignore[method-assign]

    out = enc.encode_images(["a.jpg", "b.jpg"])
    assert out[0] is not None and out[1] is not None
    assert calls[0] == 2  # failed batch
    assert calls.count(1) == 2  # serial fallback


def test_encode_image_raises_on_missing_file() -> None:
    """[OPT-001] encode_image still raises FileNotFoundError (compat)."""
    enc = _stub_dino_encoder(encode_batch_size=1)

    def _prep(path: str) -> np.ndarray:
        raise FileNotFoundError(f"Image not found for DINO encode: {path}")

    enc._preprocess_path = _prep  # type: ignore[method-assign]
    with pytest.raises(FileNotFoundError, match="missing-compat"):
        enc.encode_image("missing-compat.jpg")


def test_encode_images_batch_size_one_ok() -> None:
    """[OPT-001] encode_batch_size=1 (serial equivalent) does not crash."""
    enc = _stub_dino_encoder(encode_batch_size=1)
    chw = np.zeros((3, 8, 8), dtype=np.float32)
    enc._preprocess_path = lambda _p: chw  # type: ignore[method-assign]
    out = enc.encode_images(["one.jpg", "two.jpg"])
    assert len(out) == 2
    assert all(v is not None and len(v) == 4 for v in out)


def test_dino_encoder_ctor_rejects_encode_batch_size_below_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[OPT-001] explicit encode_batch_size < 1 raises ValueError."""
    db = DatabaseSettings(
        dino_model_path="bin/dinov2_wine_final.onnx",
        embedding_dim=4,
        dino=_dino_preprocess(encode_batch_size=16),
    )
    compute = ComputeSettings(device="cpu", cv_threads=0, ort_threads=0)

    mock_session = MagicMock()
    mock_session.get_inputs.return_value = [MagicMock(name="pixel_values")]
    mock_out = MagicMock()
    mock_out.name = "pooler_output"
    mock_session.get_outputs.return_value = [mock_out]
    mock_session.get_providers.return_value = [_CPU]

    monkeypatch.setattr(
        "core.retrieve.dino_encoder.ort.InferenceSession",
        lambda *a, **k: mock_session,
    )
    # Bypass real file check by pointing at existing model path.
    with pytest.raises(ValueError, match="encode_batch_size must be >= 1"):
        DinoOnnxEncoder(
            db,
            compute,
            providers=[_CPU],
            repo_root=_REPO,
            encode_batch_size=0,
        )


# --- OPT-002: YOLO providers ---------------------------------------------


def test_select_yolo_providers_cpu_only() -> None:
    """[OPT-002] device=cpu → CPU only even if CUDA listed."""
    assert select_yolo_onnx_providers(
        "cpu", available=[_CUDA, _CPU]
    ) == [_CPU]


def test_select_yolo_providers_cuda_with_cuda() -> None:
    """[OPT-002] device=cuda + CUDA available → [CUDA, CPU]."""
    assert select_yolo_onnx_providers(
        "cuda", available=[_CUDA, _CPU]
    ) == [_CUDA, _CPU]


def test_select_yolo_providers_cuda_without_cuda(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """[OPT-002] device=cuda without CUDA → CPU (+ warning)."""
    with caplog.at_level("WARNING"):
        providers = select_yolo_onnx_providers("cuda", available=[_CPU])
    assert providers == [_CPU]
    assert any("cuda" in r.message.lower() for r in caplog.records)


def test_select_yolo_providers_auto_with_and_without_cuda() -> None:
    """[OPT-002] auto → CUDA pair if present, else CPU."""
    assert select_yolo_onnx_providers(
        "auto", available=[_CUDA, _CPU]
    ) == [_CUDA, _CPU]
    assert select_yolo_onnx_providers("auto", available=[_CPU]) == [_CPU]


def test_default_yaml_cropper_device_is_cpu() -> None:
    """[OPT-002] compute_cropper.yaml cropper.device default == cpu."""
    settings = load_app_settings()
    assert settings.cropper.device == "cpu"


def test_cropper_uses_cropper_device_not_compute(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """[OPT-002] compute=cuda + cropper=cpu → InferenceSession gets CPU-only."""
    fake_model = tmp_path / "fake_yolo.onnx"
    fake_model.write_bytes(b"onnx-stub")
    settings = AppSettings(
        yolo_model_path=str(fake_model),
        compute=ComputeSettings(device="cuda", cv_threads=0, ort_threads=0),
        cropper=_cropper_settings(device="cpu", output_dir=str(tmp_path / "crops")),
    )

    captured: list[list[str] | None] = []

    def _fake_session(
        _path: str,
        providers: list[str] | None = None,
        sess_options: Any = None,
        **_kwargs: Any,
    ) -> MagicMock:
        captured.append(list(providers) if providers is not None else None)
        sess = MagicMock()
        sess.get_inputs.return_value = [MagicMock(name="images")]
        sess.get_outputs.return_value = [MagicMock(name="output0")]
        sess.get_providers.return_value = list(providers or [])
        return sess

    monkeypatch.setattr(
        "core.cropper.onnx_yolo.ort.InferenceSession",
        _fake_session,
    )
    monkeypatch.setattr(
        "core.cropper.onnx_yolo.select_yolo_onnx_providers",
        lambda device, available=None: select_yolo_onnx_providers(
            device, available=[_CUDA, _CPU]
        ),
    )

    OnnxYoloCropper(settings)
    assert len(captured) == 1
    assert captured[0] == [_CPU]


def test_cropper_device_rejects_unknown() -> None:
    """[OPT-002] cropper.device validator rejects invalid values."""
    with pytest.raises(ValidationError):
        _cropper_settings(device="gpu")
