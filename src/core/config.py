"""Settings models loaded from YAML / env (no magic numbers in call sites)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, field_validator, model_validator

from core.env import profile_overlay_path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATABASE_YAML = _REPO_ROOT / "config" / "database.yaml"
_DEFAULT_COMPUTE_CROPPER_YAML = _REPO_ROOT / "config" / "compute_cropper.yaml"
_DEFAULT_OCR_RERANK_YAML = _REPO_ROOT / "config" / "ocr_rerank.yaml"
_DEFAULT_PRODUCT_YAML = _REPO_ROOT / "config" / "product.yaml"


class ComputeSettings(BaseModel):
    device: str
    cv_threads: int
    ort_threads: int
    # Parallel image-encoder ORT runs per process; 0 = unlimited.
    max_concurrent_inference: int = 0

    @field_validator("cv_threads", "ort_threads", "max_concurrent_inference")
    @classmethod
    def thread_limits_must_be_non_negative(cls, value: int) -> int:
        if value < 0:
            msg = f"thread limit must be >= 0 (0 = unlimited), got {value}"
            raise ValueError(msg)
        return value


class CropperSettings(BaseModel):
    device: str
    confidence: float
    input_size: int
    letterbox_color: tuple[int, int, int]
    output_dir: str
    box_area_min: float
    box_area_max: float
    box_conf_keep_ratio: float
    min_crop_side: int = Field(gt=0)
    catalog_crops_dir: str
    catalog_crops_review_dir: str

    @field_validator("device")
    @classmethod
    def device_must_be_known(cls, value: str) -> str:
        name = value.strip().lower()
        if name not in {"cpu", "cuda", "auto"}:
            msg = f"cropper.device must be cpu | cuda | auto, got {value!r}"
            raise ValueError(msg)
        return name


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
    # Label evidence (confident rerank): words that never identify a producer / brand.
    producer_stopwords: list[str] = Field(default_factory=list)
    generic_title_tokens: list[str] = Field(default_factory=list)


class DinoPreprocessSettings(BaseModel):
    """Image encoder ONNX preprocess (must match training / export)."""

    input_size: int = Field(gt=0)
    # stretch = legacy DINO square resize; letterbox = SigLIP2 training preprocess.
    resize_mode: Literal["stretch", "letterbox"] = "stretch"
    pad_fill_rgb: tuple[int, int, int] | None = None
    normalize_mean: tuple[float, float, float]
    normalize_std: tuple[float, float, float]
    l2_normalize: bool = True
    encode_batch_size: int = Field(ge=1)

    @field_validator("pad_fill_rgb")
    @classmethod
    def pad_fill_must_be_byte_range(
        cls, value: tuple[int, int, int] | None
    ) -> tuple[int, int, int] | None:
        if value is not None and any(c < 0 or c > 255 for c in value):
            msg = f"pad_fill_rgb channels must be in 0..255, got {value}"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def letterbox_requires_pad_fill(self) -> DinoPreprocessSettings:
        if self.resize_mode == "letterbox" and self.pad_fill_rgb is None:
            msg = "dino.pad_fill_rgb is required when resize_mode == 'letterbox'"
            raise ValueError(msg)
        return self


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


class OcrSettings(BaseModel):
    """OCR backend selection from ``config/ocr_rerank.yaml`` ``ocr`` block."""

    engine: str = "phocr"
    llm_task: str = "ocr_label"
    lang: str = "ru"
    limit_side_len: int = Field(gt=0)
    min_confidence: float = 0.0
    min_line_chars: int = Field(ge=0)
    drop_spaced_letters: bool = True

    @field_validator("engine")
    @classmethod
    def engine_must_be_known(cls, value: str) -> str:
        name = value.strip().lower()
        if name not in {"phocr", "llm", "mock"}:
            msg = f"ocr.engine must be phocr | llm | mock, got {value!r}"
            raise ValueError(msg)
        return name


class MarginTier(BaseModel):
    """OCR trigger for one image-confidence band: ``score_1 >= min_score``."""

    min_score: float
    margin_min: float


class PolicySettings(BaseModel):
    """Eval decision knobs (see ``eval_predict.md``)."""

    top_k: int = Field(gt=0)
    margin_min: float
    # First tier (by min_score, high → low) with score_1 >= min_score sets the
    # OCR margin; no tiers / no match → ``margin_min``.
    margin_tiers: list[MarginTier] = Field(default_factory=list)
    abs_min: float
    enable_rerank: bool
    enable_not_found_gate: bool = False
    # always: text leader wins; confident: only on strong label evidence.
    rerank_mode: Literal["always", "confident"] = "always"
    strong_combos: list[list[str]] = Field(
        default_factory=lambda: [["manufacturer", "grape"], ["manufacturer", "brand"]]
    )
    max_img_drop: float | None = None
    # Color rule after OCR: label color (these synonyms → categories.name) that
    # contradicts the winner switches to the best top-K hit of that color whose
    # manufacturer OCR confirms. Empty → off.
    color_synonyms: dict[str, list[str]] = Field(default_factory=dict)

    def margin_min_for(self, score_1: float) -> float:
        """Порог разрыва для OCR при данной уверенности top-1."""
        for tier in sorted(self.margin_tiers, key=lambda t: t.min_score, reverse=True):
            if score_1 >= tier.min_score:
                return tier.margin_min
        return self.margin_min

    @field_validator("strong_combos")
    @classmethod
    def combos_must_use_known_signals(cls, value: list[list[str]]) -> list[list[str]]:
        known = {"manufacturer", "grape", "brand"}
        for combo in value:
            unknown = set(combo) - known
            if not combo or unknown:
                msg = f"strong_combos entries must be non-empty subsets of {known}"
                raise ValueError(msg)
        return value


class DecisionLogSettings(BaseModel):
    """Structured per-request decision log (JSONL file)."""

    path: str
    ocr_lines_cap: int = Field(gt=0, default=32)


class OcrRerankSettings(BaseModel):
    """Combined OCR / fuzzy / policy settings from ``config/ocr_rerank.yaml``."""

    ocr: OcrSettings
    fuzzy: FuzzySettings
    field_weights: dict[str, float]
    policy: PolicySettings
    decision_log: DecisionLogSettings
    rerank_top: int = Field(gt=0)


class ConfidenceSettings(BaseModel):
    """Image top-1 cosine thresholds for product confidence levels."""

    high_min: float
    medium_min: float
    not_found_min: float

    @model_validator(mode="after")
    def thresholds_must_be_ordered(self) -> ConfidenceSettings:
        if not self.not_found_min <= self.medium_min <= self.high_min:
            msg = (
                "confidence thresholds must satisfy "
                "not_found_min <= medium_min <= high_min, got "
                f"{self.not_found_min} / {self.medium_min} / {self.high_min}"
            )
            raise ValueError(msg)
        return self


class AnalogSettings(BaseModel):
    """Analog selection: result limit, OCR color synonyms, Latin grape aliases."""

    limit: int = Field(gt=0)
    color_synonyms: dict[str, list[str]] = Field(default_factory=dict)
    # Catalog grape (dictionary value) → Latin / OCR spellings (whole-phrase match).
    grape_aliases: dict[str, list[str]] = Field(default_factory=dict)

    @field_validator("grape_aliases")
    @classmethod
    def grape_aliases_must_be_non_empty(
        cls, value: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        for grape, aliases in value.items():
            if not grape.strip():
                msg = "analogs.grape_aliases keys must be non-empty strings"
                raise ValueError(msg)
            if any(not alias.strip() for alias in aliases):
                msg = f"analogs.grape_aliases[{grape!r}] has an empty alias"
                raise ValueError(msg)
        return value


class StorageSettings(BaseModel):
    """Query photo storage and retention."""

    queries_dir: str
    retention_days: int = Field(gt=0)


class UploadSettings(BaseModel):
    """Upload validation limits (checked by the caller before ``search``)."""

    max_mb: float = Field(gt=0)
    content_types: list[str] = Field(min_length=1)


class ProductSettings(BaseModel):
    """Product API / UI settings from ``config/product.yaml``."""

    confidence: ConfidenceSettings
    analogs: AnalogSettings
    storage: StorageSettings
    feedback_log: str
    upload: UploadSettings


def _read_yaml_mapping(yaml_path: Path) -> dict[object, object]:
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = f"config must be a mapping: {yaml_path}"
        raise TypeError(msg)
    return raw


def _deep_merge(
    base: dict[object, object], overlay: dict[object, object]
) -> dict[object, object]:
    """Mappings merge recursively; lists and scalars from ``overlay`` replace."""
    merged = dict(base)
    for key, value in overlay.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = value
    return merged


def _load_yaml_mapping(yaml_path: Path) -> dict[object, object]:
    """Base YAML + ``config/profiles/<APP_ENV>/<same name>`` overlay when present."""
    raw = _read_yaml_mapping(yaml_path)
    overlay = profile_overlay_path(yaml_path)
    if overlay is None:
        return raw
    return _deep_merge(raw, _read_yaml_mapping(overlay))


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


def load_product_settings(
    path: Path | str | None = None,
) -> ProductSettings:
    """Load confidence, analogs, storage, feedback, and upload settings."""
    yaml_path = Path(path) if path is not None else _DEFAULT_PRODUCT_YAML
    return ProductSettings.model_validate(_load_yaml_mapping(yaml_path))


def load_ocr_settings(
    path: Path | str | None = None,
) -> OcrSettings:
    """Load OCR knobs from ``config/ocr_rerank.yaml`` (``ocr`` mapping)."""
    yaml_path = Path(path) if path is not None else _DEFAULT_OCR_RERANK_YAML
    mapping = _load_yaml_mapping(yaml_path)
    ocr_block = mapping.get("ocr")
    if not isinstance(ocr_block, dict):
        msg = f"config must contain an 'ocr' mapping: {yaml_path}"
        raise TypeError(msg)
    return OcrSettings.model_validate(ocr_block)


def load_ocr_rerank_settings(
    path: Path | str | None = None,
) -> OcrRerankSettings:
    """Load OCR, fuzzy, policy, and decision-log settings."""
    yaml_path = Path(path) if path is not None else _DEFAULT_OCR_RERANK_YAML
    raw = _load_yaml_mapping(yaml_path)

    ocr_raw = raw.get("ocr")
    if not isinstance(ocr_raw, dict):
        msg = f"ocr_rerank.yaml missing mapping 'ocr': {yaml_path}"
        raise TypeError(msg)

    hybrid = raw.get("hybrid")
    if not isinstance(hybrid, dict):
        msg = f"ocr_rerank.yaml missing mapping 'hybrid': {yaml_path}"
        raise TypeError(msg)
    fuzzy_raw = hybrid.get("fuzzy")
    if not isinstance(fuzzy_raw, dict):
        msg = f"ocr_rerank.yaml missing mapping 'hybrid.fuzzy': {yaml_path}"
        raise TypeError(msg)
    rerank_top = hybrid.get("rerank_top")
    if not isinstance(rerank_top, int) or rerank_top <= 0:
        msg = f"hybrid.rerank_top must be a positive int, got {rerank_top!r}"
        raise TypeError(msg)

    confidence = raw.get("confidence")
    if not isinstance(confidence, dict):
        msg = f"ocr_rerank.yaml missing mapping 'confidence': {yaml_path}"
        raise TypeError(msg)
    text_conf = confidence.get("text")
    if not isinstance(text_conf, dict):
        msg = f"ocr_rerank.yaml missing mapping 'confidence.text': {yaml_path}"
        raise TypeError(msg)
    field_weights = text_conf.get("field_weights")
    if not isinstance(field_weights, dict):
        msg = "confidence.text.field_weights must be a mapping"
        raise TypeError(msg)

    policy_raw = raw.get("policy")
    if not isinstance(policy_raw, dict):
        msg = f"ocr_rerank.yaml missing mapping 'policy': {yaml_path}"
        raise TypeError(msg)

    log_raw = raw.get("decision_log")
    if not isinstance(log_raw, dict):
        msg = f"ocr_rerank.yaml missing mapping 'decision_log': {yaml_path}"
        raise TypeError(msg)

    return OcrRerankSettings(
        ocr=OcrSettings.model_validate(ocr_raw),
        fuzzy=FuzzySettings.model_validate(fuzzy_raw),
        field_weights={str(k): float(v) for k, v in field_weights.items()},
        policy=PolicySettings.model_validate(policy_raw),
        decision_log=DecisionLogSettings.model_validate(log_raw),
        rerank_top=rerank_top,
    )
