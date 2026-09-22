"""Minimal types copied for adapting migration OCR/cropper/fuzzy in a new repo.

These are NOT a runnable package. Remap imports when integrating:
  - FuzzySettings → used by text/fuzzy.py
  - WineRecord → used by text/fuzzy.py (faiss_row can become embed_row / drop)
  - CropResult / LabelCropper → used by cropper/onnx_yolo.py
  - CropperSettings / ComputeSettings → wire from YAML samples
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypedDict

from pydantic import BaseModel, field_validator


class CropResult(TypedDict):
    cropped_path: str | None
    used_fallback: bool


class LabelCropper(Protocol):
    def crop(self, image_path: str) -> CropResult: ...


@dataclass
class WineRecord:
    id: int
    external_id: int
    title: str
    manufacturer: str
    category: str
    region: str
    color: str
    slug: str
    image_path: str
    product_url: str | None
    faiss_row: int | None  # legacy; replace with pgvector / drop in new schema


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


class SearchResult(TypedDict):
    """Legacy shape still referenced by fuzzy.rerank; slim down in new repo."""

    wine_id: int
    external_id: int
    score: float
    inliers: int | None
    good_matches: int | None
    vlad_rank: int | None
    image_path: str
