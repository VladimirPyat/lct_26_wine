"""Retrieval: DINO encode + pgvector top-K (Stage 1)."""

from core.retrieve.dino_encoder import (
    DinoOnnxEncoder,
    create_dino_encoder,
    encode_image,
)

__all__ = [
    "DinoOnnxEncoder",
    "create_dino_encoder",
    "encode_image",
]
