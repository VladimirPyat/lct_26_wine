"""Config profiles: APP_ENV overlays from config/profiles/<name>/ over base YAML."""

from __future__ import annotations

from pathlib import Path

import pytest

from core import config as cfg
from core.env import active_profile, profile_overlay_path


@pytest.fixture
def app_env(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    def _set(value: str | None) -> None:
        if value is None:
            monkeypatch.delenv("APP_ENV", raising=False)
        else:
            monkeypatch.setenv("APP_ENV", value)

    return _set


def test_default_profile_is_dev_and_has_no_overlay(app_env) -> None:  # type: ignore[no-untyped-def]
    app_env("dev")
    assert active_profile() == "dev"
    assert profile_overlay_path(cfg._DEFAULT_DATABASE_YAML) is None


def test_unknown_profile_fails_fast(app_env) -> None:  # type: ignore[no-untyped-def]
    app_env("staging-nope")
    with pytest.raises(ValueError, match="APP_ENV"):
        active_profile()


def test_vps_overlay_values(app_env) -> None:  # type: ignore[no-untyped-def]
    app_env("vps")
    db = cfg.load_database_settings()
    app = cfg.load_app_settings()
    ocr = cfg.load_ocr_rerank_settings()
    assert db.dino_model_path.endswith("_int8.onnx")
    assert db.dino.encode_batch_size == 1
    assert db.embedding_dim == 1152  # untouched base key survives the merge
    assert db.dino.resize_mode == "letterbox"
    assert app.compute.device == "cpu"
    assert app.compute.ort_threads == 2
    assert app.compute.max_concurrent_inference == 1
    assert app.cropper.device == "cpu"
    assert app.cropper.confidence > 0  # sibling keys of an overlaid mapping kept
    assert ocr.ocr.engine == "llm"
    assert ocr.policy.margin_tiers  # list from base not dropped


def test_explicit_path_outside_config_is_not_overlaid(app_env, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    app_env("vps")
    copy = tmp_path / "database.yaml"
    base_text = cfg._DEFAULT_DATABASE_YAML.read_text(encoding="utf-8")
    copy.write_text(base_text, encoding="utf-8")
    assert cfg.load_database_settings(copy).dino_model_path.endswith("_fp16.onnx")


def test_deep_merge_replaces_lists_and_scalars() -> None:
    base: dict[object, object] = {"a": {"x": 1, "y": [1, 2]}, "b": 1}
    merged = cfg._deep_merge(base, {"a": {"y": [3]}, "c": 2})
    assert merged == {"a": {"x": 1, "y": [3]}, "b": 1, "c": 2}
    assert base == {"a": {"x": 1, "y": [1, 2]}, "b": 1}
