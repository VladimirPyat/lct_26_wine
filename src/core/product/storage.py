"""Хранилище фото запросов и результатов поиска: id, пути, очистка по сроку."""

from __future__ import annotations

import re
import time
from pathlib import Path

SEARCH_ID_RE = re.compile(r"^[0-9a-f]{32}$")
# Files owned by the store: ``{search_id}.json`` and ``{search_id}{image_ext}``.
_STORED_FILE_RE = re.compile(r"^[0-9a-f]{32}\.[a-z0-9]{1,5}$")
RESULT_SUFFIX = ".json"
_SECONDS_PER_DAY = 86_400.0


def is_valid_search_id(search_id: str) -> bool:
    """``search_id`` — uuid4 hex из 32 символов ``[0-9a-f]``."""
    return bool(SEARCH_ID_RE.fullmatch(search_id))


def result_path(queries_dir: Path, search_id: str) -> Path | None:
    """Путь к ``{id}.json`` для валидного id (файл может отсутствовать)."""
    if not is_valid_search_id(search_id):
        return None
    return queries_dir / f"{search_id}{RESULT_SUFFIX}"


def photo_path(queries_dir: Path, search_id: str) -> Path | None:
    """Существующее фото запроса по точному id, иначе ``None`` (без обхода путей)."""
    if not is_valid_search_id(search_id) or not queries_dir.is_dir():
        return None
    for candidate in sorted(queries_dir.glob(f"{search_id}.*")):
        if (
            candidate.suffix != RESULT_SUFFIX
            and _STORED_FILE_RE.fullmatch(candidate.name)
            and candidate.is_file()
            and candidate.resolve().parent == queries_dir.resolve()
        ):
            return candidate
    return None


def expired_files(
    queries_dir: Path, retention_days: float, *, now: float | None = None
) -> list[Path]:
    """Файлы хранилища старше ``retention_days`` (по mtime).

    Учитываются только ``{id}.json`` / ``{id}{ext}``; чужие файлы не трогаются.
    """
    if not queries_dir.is_dir():
        return []
    reference = now if now is not None else time.time()
    cutoff = reference - retention_days * _SECONDS_PER_DAY
    return sorted(
        path
        for path in queries_dir.iterdir()
        if path.is_file()
        and _STORED_FILE_RE.fullmatch(path.name)
        and path.stat().st_mtime < cutoff
    )


def cleanup_expired(
    queries_dir: Path,
    retention_days: float,
    *,
    dry_run: bool = False,
    now: float | None = None,
) -> list[Path]:
    """Удалить просроченные файлы хранилища; вернуть список (удалённых / к удалению)."""
    expired = expired_files(queries_dir, retention_days, now=now)
    if not dry_run:
        for path in expired:
            path.unlink(missing_ok=True)
    return expired
