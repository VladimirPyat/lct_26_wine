"""Удаление фото и результатов поиска старше ``storage.retention_days``.

Запуск (можно из cron)::

    uv run python scripts/cleanup_search_queries.py [--dry-run] [--days N]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from core.config import load_product_settings  # noqa: E402
from core.product.storage import cleanup_expired  # noqa: E402


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="only list files that would be removed",
    )
    parser.add_argument(
        "--days",
        type=float,
        default=None,
        help="override storage.retention_days from config/product.yaml",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="path to product.yaml (default: config/product.yaml)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI; код возврата 0 при успехе, 2 при неверных аргументах."""
    args = _parse_args(argv)
    settings = load_product_settings(args.config)
    days = args.days if args.days is not None else settings.storage.retention_days
    if days < 0:
        print("--days must be >= 0", file=sys.stderr)
        return 2
    queries_dir = Path(settings.storage.queries_dir)
    if not queries_dir.is_absolute():
        queries_dir = _REPO_ROOT / queries_dir
    expired = cleanup_expired(queries_dir, days, dry_run=args.dry_run)
    action = "would remove" if args.dry_run else "removed"
    for path in expired:
        print(f"{action}: {path.name}")
    print(
        f"{action} {len(expired)} file(s) older than {days:g} day(s) in {queries_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
