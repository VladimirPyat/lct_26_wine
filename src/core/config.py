"""Settings models loaded from YAML / env (no magic numbers in call sites)."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


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


class AppSettings(BaseModel):
    """Subset needed by YOLO cropper; full app config lands in later stages."""

    yolo_model_path: str
    compute: ComputeSettings
    cropper: CropperSettings
