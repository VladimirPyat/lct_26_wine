"""Retrieval: DINO encode + pgvector top-K (Stage 1–2)."""

from core.retrieve.dino_encoder import (
    DinoOnnxEncoder,
    create_dino_encoder,
    encode_image,
)
from core.retrieve.retriever import RetrieveBundle, WineRetriever

__all__ = [
    "DinoOnnxEncoder",
    "RetrieveBundle",
    "WineRetriever",
    "create_dino_encoder",
    "encode_image",
]
