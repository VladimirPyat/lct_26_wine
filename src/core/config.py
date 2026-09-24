"""Settings models loaded from YAML / env (no magic numbers in call sites)."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, field_validator

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATABASE_YAML = _REPO_ROOT / "config" / "database.yaml"
_DEFAULT_COMPUTE_CROPPER_YAML = _REPO_ROOT / "config" / "compute_cropper.yaml"


class ComputeSettings(BaseModel):
    device: str
    cv_threads: int
    ort_threads: int

    @field_validator("cv_threads", "ort_threads")
    @classmethod
    def thread_limits_must_be_non_negative(cls, value: int) -> int:
        if value < 0:
            msg = f"thread limit must be >= 0 (0 = unlimited), got {value}"
            raise ValueError(msg)
        return value


class CropperSettings(BaseModel):
    confidence: float
    input_size: int
    letterbox_color: tuple[int, int, int]
    output_dir: str
    box_area_min: float
    box_area_max: float
    box_conf_keep_ratio: float


class FuzzySettings(BaseModel):
    token_min_len: int
    token_fuzz_min: float
    short_field_len: int
    short_field_score_floor: float
    short_field_dampen: float
    coverage_weight: float
    token_hit_weight: float
    mfr_compact_high: float
    mfr_compact_mid: float
    mfr_bonus_high: float
    mfr_bonus_mid: float
    primary_line_cap: int
    prefilter_min_candidates: int
    exact_title_token_bonus: float
    title_token_ratio_min: float
    shortlist_idf_weight: float
    token_edit_max: int
    token_edit_max_frac: float
    token_edit_idf_scale: float


class DinoPreprocessSettings(BaseModel):
    """DINO ONNX image preprocess (must match export / HF DINOv2)."""

    input_size: int = Field(gt=0)
    normalize_mean: tuple[float, float, float]
    normalize_std: tuple[float, float, float]
    l2_normalize: bool = True


class DatabaseSettings(BaseModel):
    """Postgres catalog / pgvector settings from ``config/database.yaml``."""

    dino_model_path: str
    embedding_dim: int = Field(gt=0)
    dino: DinoPreprocessSettings


class AppSettings(BaseModel):
    """YOLO cropper + shared compute; DINO path lives in ``DatabaseSettings``."""

    yolo_model_path: str
    compute: ComputeSettings
    cropper: CropperSettings


def _load_yaml_mapping(yaml_path: Path) -> dict[object, object]:
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = f"config must be a mapping: {yaml_path}"
        raise TypeError(msg)
    return raw


def load_database_settings(
    path: Path | str | None = None,
) -> DatabaseSettings:
    """Load embedding dim, DINO path, and preprocess from YAML."""
    yaml_path = Path(path) if path is not None else _DEFAULT_DATABASE_YAML
    return DatabaseSettings.model_validate(_load_yaml_mapping(yaml_path))


def load_app_settings(
    path: Path | str | None = None,
) -> AppSettings:
    """Load YOLO + compute settings from ``config/compute_cropper.yaml``."""
    yaml_path = Path(path) if path is not None else _DEFAULT_COMPUTE_CROPPER_YAML
    return AppSettings.model_validate(_load_yaml_mapping(yaml_path))
