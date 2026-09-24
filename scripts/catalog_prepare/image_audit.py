"""Shared helpers: measure image min_side and content hash (Pillow)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image

MIN_SIDE = 200


def measure_min_side(path: Path) -> int | None:
    """Return min(width, height) or None if file missing / unreadable."""
    if not path.is_file():
        return None
    try:
        with Image.open(path) as image:
            width, height = image.size
    except OSError:
        return None
    return min(width, height)


def measure_size(path: Path) -> tuple[int, int] | None:
    """Return (width, height) or None if file missing / unreadable."""
    if not path.is_file():
        return None
    try:
        with Image.open(path) as image:
            return image.size
    except OSError:
        return None


def content_hash(path: Path) -> str | None:
    """SHA-256 hex digest of file bytes, or None if missing."""
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
