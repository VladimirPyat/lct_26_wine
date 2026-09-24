"""Eval harness endpoint: ``POST /v1/eval/predict``."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from api.eval_pipeline import EmptyCatalogError, predict_slug
from api.runtime import EvalRuntime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/eval", tags=["eval"])


class PredictResponse(BaseModel):
    slug: str = Field(min_length=1)


@router.post("/predict", response_model=PredictResponse, status_code=200)
async def eval_predict(
    request: Request,
    image: Annotated[UploadFile, File(description="Query bottle/label image")],
) -> PredictResponse:
    """Multipart field ``image`` → ``{\"slug\": \"...\"}`` (always when hits exist)."""
    runtime: EvalRuntime | None = getattr(request.app.state, "eval_runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="eval runtime not initialized")

    suffix = Path(image.filename or "query.jpg").suffix or ".jpg"
    upload_dir = runtime.repo_root / "data" / "tmp" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            dir=str(upload_dir),
        ) as handle:
            tmp_path = Path(handle.name)
            while True:
                chunk = await image.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)

        if tmp_path.stat().st_size == 0:
            raise HTTPException(status_code=400, detail="empty image upload")

        slug = predict_slug(runtime, tmp_path)
        return PredictResponse(slug=slug)
    except HTTPException:
        raise
    except EmptyCatalogError as err:
        logger.error("eval predict empty catalog: %s", err)
        raise HTTPException(status_code=503, detail=str(err)) from err
    except FileNotFoundError as err:
        logger.error("eval predict missing asset: %s", err)
        raise HTTPException(status_code=500, detail=str(err)) from err
    except Exception as err:
        logger.exception("eval predict failed")
        raise HTTPException(status_code=500, detail=str(err)) from err
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
