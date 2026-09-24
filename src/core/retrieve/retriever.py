"""IRetriever: YOLO crop → DINO encode → pgvector top-K."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from core.contracts import LabelCropper, RankedHit
from core.retrieve.dino_encoder import DinoOnnxEncoder
from db.repository import WineRepository


@dataclass(frozen=True)
class RetrieveBundle:
    """Crop path + hits + stage latencies for the eval orchestrator."""

    crop_path: str
    used_fallback: bool
    hits: list[RankedHit]
    latency_ms: dict[str, float] = field(default_factory=dict)


class WineRetriever:
    """Crop → encode → ``WineRepository.search_by_embedding``.

    Satisfies ``IRetriever``; ``retrieve_bundle`` also exposes the crop path
    needed by the OCR/fuzzy decision policy.
    """

    def __init__(
        self,
        cropper: LabelCropper,
        encoder: DinoOnnxEncoder,
        repository: WineRepository,
    ) -> None:
        self._cropper = cropper
        self._encoder = encoder
        self._repository = repository

    def retrieve(self, image_path: str, *, top_k: int) -> list[RankedHit]:
        """Return pgvector top-K hits for ``image_path``."""
        return self.retrieve_bundle(image_path, top_k=top_k).hits

    def retrieve_bundle(self, image_path: str, *, top_k: int) -> RetrieveBundle:
        """Crop, encode, search; return hits plus crop path and latencies."""
        if top_k <= 0:
            msg = f"top_k must be > 0, got {top_k}"
            raise ValueError(msg)

        t0 = time.perf_counter()
        crop = self._cropper.crop(image_path)
        crop_path = crop["cropped_path"]
        if crop_path is None:
            msg = f"Cropper returned no path for image: {image_path}"
            raise RuntimeError(msg)
        crop_ms = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        embedding = self._encoder.encode_image(crop_path)
        encode_ms = (time.perf_counter() - t1) * 1000.0

        t2 = time.perf_counter()
        hits = self._repository.search_by_embedding(embedding, top_k=top_k)
        search_ms = (time.perf_counter() - t2) * 1000.0

        return RetrieveBundle(
            crop_path=crop_path,
            used_fallback=bool(crop["used_fallback"]),
            hits=hits,
            latency_ms={
                "crop": crop_ms,
                "encode": encode_ms,
                "search": search_ms,
            },
        )
