"""Settings models loaded from YAML / env (no magic numbers in call sites)."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, field_validator

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATABASE_YAML = _REPO_ROOT / "config" / "database.yaml"
_DEFAULT_COMPUTE_CROPPER_YAML = _REPO_ROOT / "config" / "compute_cropper.yaml"
_DEFAULT_OCR_RERANK_YAML = _REPO_ROOT / "config" / "ocr_rerank.yaml"


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


class PolicySettings(BaseModel):
    """Eval decision knobs (see ``eval_predict.md``)."""

    top_k: int = Field(gt=0)
    margin_min: float
    abs_min: float
    enable_rerank: bool
    enable_not_found_gate: bool = False


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
