"""SIG-006 — encoder preprocess (letterbox / stretch), settings, ONNX dim guard."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from core.config import (
    ComputeSettings,
    DatabaseSettings,
    DinoPreprocessSettings,
    load_database_settings,
)
from core.retrieve.dino_encoder import DinoOnnxEncoder
from core.retrieve.preprocess import letterbox_rgb

_REPO = Path(__file__).resolve().parents[1]
_FILL = (123, 116, 103)
_CPU = "CPUExecutionProvider"


def _settings(**overrides: Any) -> DinoPreprocessSettings:
    base: dict[str, Any] = {
        "input_size": 256,
        "normalize_mean": (0.5, 0.5, 0.5),
        "normalize_std": (0.5, 0.5, 0.5),
        "l2_normalize": True,
        "encode_batch_size": 4,
    }
    base.update(overrides)
    return DinoPreprocessSettings.model_validate(base)


def _load_compare_script() -> ModuleType:
    path = _REPO / "scripts" / "compare_dino_onnx.py"
    spec = importlib.util.spec_from_file_location("compare_dino_onnx_t", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _random_rgb(h: int, w: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


def _stub_encoder(
    *,
    input_size: int,
    resize_mode: str,
    pad_fill_rgb: tuple[int, int, int] | None,
    mean: tuple[float, float, float] = (0.5, 0.5, 0.5),
    std: tuple[float, float, float] = (0.5, 0.5, 0.5),
) -> DinoOnnxEncoder:
    enc = object.__new__(DinoOnnxEncoder)
    enc._input_size = input_size
    enc._resize_mode = resize_mode
    enc._pad_fill_rgb = pad_fill_rgb
    enc._mean = np.asarray(mean, dtype=np.float32)
    enc._std = np.asarray(std, dtype=np.float32)
    return enc


def _patch_session(
    monkeypatch: pytest.MonkeyPatch, output_shape: list[Any]
) -> MagicMock:
    session = MagicMock()
    session.get_inputs.return_value = [MagicMock(name="pixel_values")]
    out = MagicMock()
    out.name = "pooler_output"
    out.shape = output_shape
    session.get_outputs.return_value = [out]
    session.get_providers.return_value = [_CPU]
    monkeypatch.setattr(
        "core.retrieve.dino_encoder.ort.InferenceSession",
        lambda *a, **k: session,
    )
    return session


def _db(tmp_path: Path, embedding_dim: int) -> DatabaseSettings:
    model = tmp_path / "stub_encoder.onnx"
    model.write_bytes(b"onnx-stub")
    return DatabaseSettings(
        dino_model_path=str(model),
        embedding_dim=embedding_dim,
        dino=_settings(resize_mode="letterbox", pad_fill_rgb=_FILL),
    )


_COMPUTE = ComputeSettings(device="cpu", cv_threads=0, ort_threads=0)


# --- letterbox -------------------------------------------------------------


def test_letterbox_100x200_scales_and_centers() -> None:
    """[SIG-006] 100×200 (h×w) → 256×256; content 128×256 centered; pad = fill."""
    rgb = np.full((100, 200, 3), 10, dtype=np.uint8)
    out = letterbox_rgb(rgb, 256, _FILL)
    assert out.shape == (256, 256, 3)
    assert out.dtype == np.uint8
    top = (256 - 128) // 2
    assert np.all(out[top : top + 128, :] == 10)
    assert np.all(out[:top, :] == np.array(_FILL, dtype=np.uint8))
    assert np.all(out[top + 128 :, :] == np.array(_FILL, dtype=np.uint8))


def test_letterbox_matches_compare_script_byte_for_byte() -> None:
    """[SIG-006] script uses the same helper; arrays identical."""
    module = _load_compare_script()
    assert module._letterbox is letterbox_rgb
    rgb = _random_rgb(173, 91, seed=3)
    np.testing.assert_array_equal(
        module._letterbox(rgb, 256, _FILL), letterbox_rgb(rgb, 256, _FILL)
    )


def test_encoder_letterbox_matches_script_preprocess(tmp_path: Path) -> None:
    """[SIG-006] encoder CHW == script ``_preprocess(resize=letterbox)`` CHW."""
    module = _load_compare_script()
    bgr = _random_rgb(140, 300, seed=5)
    path = tmp_path / "q.png"
    assert cv2.imwrite(str(path), bgr)
    enc = _stub_encoder(input_size=256, resize_mode="letterbox", pad_fill_rgb=_FILL)
    mean = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    ours = enc._preprocess_path(str(path))
    theirs = module._preprocess(path, 256, resize="letterbox", mean=mean, std=mean)
    np.testing.assert_array_equal(ours, theirs)


# --- stretch / settings ----------------------------------------------------


def test_resize_mode_defaults_to_stretch() -> None:
    """[SIG-006] resize_mode default = stretch; pad_fill optional."""
    settings = _settings()
    assert settings.resize_mode == "stretch"
    assert settings.pad_fill_rgb is None


def test_stretch_output_unchanged() -> None:
    """[SIG-006] stretch = plain square cv2.resize (no pad), legacy DINO path."""
    bgr = _random_rgb(50, 120, seed=7)
    enc = _stub_encoder(
        input_size=32,
        resize_mode="stretch",
        pad_fill_rgb=None,
        mean=(0.485, 0.456, 0.406),
        std=(0.229, 0.224, 0.225),
    )
    chw = enc._preprocess_chw(bgr)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    expected = cv2.resize(rgb, (32, 32), interpolation=cv2.INTER_LINEAR)
    expected_f = (expected.astype(np.float32) / 255.0 - enc._mean) / enc._std
    assert chw.shape == (3, 32, 32)
    np.testing.assert_array_equal(chw, np.transpose(expected_f, (2, 0, 1)))


def test_letterbox_without_pad_fill_rejected() -> None:
    """[SIG-006] letterbox requires pad_fill_rgb."""
    with pytest.raises(ValidationError, match="pad_fill_rgb"):
        _settings(resize_mode="letterbox")


@pytest.mark.parametrize("fill", [(256, 0, 0), (0, -1, 0)])
def test_pad_fill_out_of_range_rejected(fill: tuple[int, int, int]) -> None:
    """[SIG-006] pad_fill_rgb channels must be 0..255."""
    with pytest.raises(ValidationError, match="0..255"):
        _settings(resize_mode="letterbox", pad_fill_rgb=fill)


def test_unknown_resize_mode_rejected() -> None:
    with pytest.raises(ValidationError):
        _settings(resize_mode="crop")


def test_database_yaml_matches_preprocess_json() -> None:
    """[SIG-006] prod database.yaml equals bin/*_preprocess.json (training)."""
    import json

    db = load_database_settings()
    meta_path = _REPO / "bin" / "siglip2_wine_p1_epoch_3_preprocess.json"
    if not meta_path.is_file():
        pytest.skip(f"preprocess json not present: {meta_path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    # fp16 export shares weights and preprocess with fp32
    assert Path(db.dino_model_path).name in {
        "siglip2_wine_p1_epoch_3.onnx",
        "siglip2_wine_p1_epoch_3_fp16.onnx",
    }
    assert db.embedding_dim == meta["dim"]
    assert db.dino.input_size == meta["input_size"]
    assert db.dino.resize_mode == "letterbox"
    assert str(meta["resize"]).startswith("letterbox")
    assert list(db.dino.pad_fill_rgb or ()) == meta["pad_fill_rgb"]
    assert list(db.dino.normalize_mean) == meta["image_mean"]
    assert list(db.dino.normalize_std) == meta["image_std"]
    assert db.dino.l2_normalize is meta["l2_normalize"]


def test_mean_std_half_maps_255_to_one_and_0_to_minus_one() -> None:
    """[SIG-006] mean/std 0.5: pixel 255 → 1.0, 0 → −1.0."""
    enc = _stub_encoder(input_size=16, resize_mode="letterbox", pad_fill_rgb=(0, 0, 0))
    white = enc._preprocess_chw(np.full((16, 16, 3), 255, dtype=np.uint8))
    black = enc._preprocess_chw(np.zeros((16, 16, 3), dtype=np.uint8))
    np.testing.assert_allclose(white, 1.0)
    np.testing.assert_allclose(black, -1.0)


# --- ONNX output dim guard -------------------------------------------------


def test_dim_guard_rejects_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """[SIG-006] pooler_output [None, 1152] + config 768 → RuntimeError."""
    _patch_session(monkeypatch, [None, 1152])
    with pytest.raises(RuntimeError) as err:
        DinoOnnxEncoder(_db(tmp_path, 768), _COMPUTE, providers=[_CPU])
    msg = str(err.value)
    assert "1152" in msg and "768" in msg and "stub_encoder.onnx" in msg


@pytest.mark.parametrize("shape", [["batch", "dim"], [None, None], []])
def test_dim_guard_skips_symbolic(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, shape: list[Any]
) -> None:
    """[SIG-006] symbolic / unknown output dim → no error."""
    _patch_session(monkeypatch, shape)
    enc = DinoOnnxEncoder(_db(tmp_path, 768), _COMPUTE, providers=[_CPU])
    assert enc.embedding_dim == 768


def test_dim_guard_accepts_match(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_session(monkeypatch, [None, 1152])
    enc = DinoOnnxEncoder(_db(tmp_path, 1152), _COMPUTE, providers=[_CPU])
    assert enc.embedding_dim == 1152
