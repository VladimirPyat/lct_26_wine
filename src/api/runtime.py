"""Shared FastAPI app state for eval (models loaded once at startup)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from core.config import (
    AppSettings,
    OcrRerankSettings,
    load_app_settings,
    load_database_settings,
    load_ocr_rerank_settings,
)
from core.cropper.onnx_yolo import create_label_cropper
from core.ocr.base import IOCREngine
from core.ocr.factory import create_ocr_engine
from core.ocr.selection import EffectiveOcr, select_ocr_engine
from core.retrieve.dino_encoder import DinoOnnxEncoder, create_dino_encoder
from core.text.fuzzy import FuzzyReranker
from db.session import create_db_engine, create_session_factory

if TYPE_CHECKING:
    from core.contracts import LabelCropper

logger = logging.getLogger(__name__)

_CUDA_EP = "CUDAExecutionProvider"


@dataclass
class EvalRuntime:
    """Heavy models + settings shared across eval requests."""

    repo_root: Path
    app_settings: AppSettings
    ocr_rerank: OcrRerankSettings
    cropper: LabelCropper
    encoder: DinoOnnxEncoder
    reranker: FuzzyReranker
    engine: Engine
    session_factory: sessionmaker[Session]
    # ONNX file name from database.yaml ``dino_model_path`` (decision log trace).
    encoder_model: str = ""
    # OCR engine chosen once at startup (ocr_engine.md «Engine selection»).
    ocr_effective: EffectiveOcr = "phocr"
    ocr_reason: str = ""
    _ocr: IOCREngine | None = field(default=None, init=False, repr=False)

    def get_ocr(self) -> IOCREngine | None:
        """OCR-движок по выбору при старте; ``None`` — OCR отключён (без rerank).

        PHOCR строится лениво — только когда rerank действительно запускается.
        """
        if self.ocr_effective == "none":
            return None
        if self._ocr is None and self.ocr_effective == "phocr":
            ocr = self.ocr_rerank.ocr
            compute = self.app_settings.compute
            self._ocr = create_ocr_engine(
                "phocr",
                llm_task=ocr.llm_task,
                use_cuda=compute.device.lower() == "cuda",
                lang=ocr.lang,
                limit_side_len=ocr.limit_side_len,
                ort_threads=compute.ort_threads,
            )
        return self._ocr


def cuda_available(app_settings: AppSettings, encoder: DinoOnnxEncoder) -> bool:
    """CUDA доступна: ``compute.device == cuda`` и сессия энкодера на CUDA EP."""
    if app_settings.compute.device.lower() != "cuda":
        return False
    return _CUDA_EP in encoder.active_providers


def build_eval_runtime(repo_root: Path | None = None) -> EvalRuntime:
    """Load YAML + YOLO/DINO once (OCR deferred until first rerank)."""
    root = repo_root if repo_root is not None else Path(__file__).resolve().parents[2]
    app_settings = load_app_settings()
    # Resolve YOLO path relative to repo root when not absolute.
    yolo_path = Path(app_settings.yolo_model_path)
    if not yolo_path.is_absolute():
        app_settings = app_settings.model_copy(
            update={"yolo_model_path": str(root / yolo_path)}
        )
    database = load_database_settings()
    ocr_rerank = load_ocr_rerank_settings()
    cropper = create_label_cropper(app_settings)
    encoder = create_dino_encoder(database, app_settings.compute)
    reranker = FuzzyReranker(
        ocr_rerank.field_weights,
        ocr_rerank.fuzzy,
        min_line_chars=ocr_rerank.ocr.min_line_chars,
        drop_spaced_letters=ocr_rerank.ocr.drop_spaced_letters,
    )
    ocr = ocr_rerank.ocr
    selection = select_ocr_engine(
        ocr.engine,
        cuda_available=cuda_available(app_settings, encoder),
        llm_probe=lambda: create_ocr_engine("llm", llm_task=ocr.llm_task),
    )
    logger.info(
        "OCR engine: configured=%s effective=%s reason=%s",
        ocr.engine,
        selection.effective,
        selection.reason,
    )
    engine = create_db_engine()
    runtime = EvalRuntime(
        repo_root=root,
        app_settings=app_settings,
        ocr_rerank=ocr_rerank,
        cropper=cropper,
        encoder=encoder,
        reranker=reranker,
        engine=engine,
        session_factory=create_session_factory(engine),
        encoder_model=Path(database.dino_model_path).name,
        ocr_effective=selection.effective,
        ocr_reason=selection.reason,
    )
    runtime._ocr = selection.engine
    return runtime
