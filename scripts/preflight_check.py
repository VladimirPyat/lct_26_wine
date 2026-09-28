#!/usr/bin/env python3
"""Check that models, catalog data and the DB are in place before indexing / serving.

Modes:

* ``index`` (default) — before ``scripts/rebuild_catalog_db.sh``: models, owner CSV,
  site JSON, catalog photos, DB reachable;
* ``serve`` — before starting the app: models, DB has wines with embeddings,
  ``static/wines`` filled.

Prints one line per check and what to do for each failure; exit 1 if anything
required is missing. Model paths come from ``config/*.yaml``.

  uv run python scripts/preflight_check.py
  uv run python scripts/preflight_check.py --mode serve
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.config import load_app_settings, load_database_settings  # noqa: E402

DEFAULT_CSV = _REPO / "data" / "wines_integrated_updated.csv"
DEFAULT_SITE_JSON = _REPO / "data" / "site_database" / "wines_database_enriched.json"
DEFAULT_IMAGES = _REPO / "data" / "owner_database" / "images"
DEFAULT_STATIC = _REPO / "static" / "wines"
COL_SLUG = "Slug"

# A Google Drive error page saved under the model name is a few KB.
MIN_MODEL_BYTES = 1_000_000
# Share of CSV wines allowed without a photo (the reference export has 12 of 2103).
MAX_MISSING_PHOTO_SHARE = 0.05

MODEL_HINTS = {
    "yolo_detect_labels_2.onnx": "https://drive.google.com/file/d/1uKGYwkL7Ycm5QMgsWDl5KrTOpwwtCrtg/view",
    "siglip2_wine_p1_epoch_3_fp16.onnx": "https://drive.google.com/file/d/1zVKvqYtkcNy-_OF8mIKMl_RVp-HHhOqK/view",
}
IMAGES_HINT = "images.zip https://drive.google.com/file/d/1tDvAFd8aLY4e2D-3S_bHw6RTSO0afDK8/view"
INDEX_HINT = (
    "build the catalog: scripts/rebuild_catalog_db.sh --yes "
    "(Docker: docker compose run --rm app scripts/rebuild_catalog_db.sh --yes)"
)


@dataclass
class Report:
    """Результаты проверок: ошибки блокируют запуск, предупреждения — нет."""

    errors: int = 0
    warnings: int = 0
    lines: list[str] = field(default_factory=list)

    def ok(self, what: str) -> None:
        self.lines.append(f"  OK    {what}")

    def warn(self, what: str, hint: str = "") -> None:
        self.warnings += 1
        self.lines.append(f"  WARN  {what}" + (f"\n        → {hint}" if hint else ""))

    def fail(self, what: str, hint: str = "") -> None:
        self.errors += 1
        self.lines.append(f"  FAIL  {what}" + (f"\n        → {hint}" if hint else ""))


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(_REPO))
    except ValueError:
        return str(path)


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _REPO / path


def check_model(report: Report, path: Path) -> None:
    """Файл модели есть и не похож на недокачанный / HTML-страницу."""
    hint = MODEL_HINTS.get(path.name, "see manuals/quickstart.md, section 1.2")
    if not path.is_file():
        report.fail(f"model {_rel(path)} not found", f"download: {hint}")
        return
    size = path.stat().st_size
    if size < MIN_MODEL_BYTES:
        report.fail(
            f"model {_rel(path)} is only {size} bytes (broken download?)",
            f"download again: {hint}",
        )
        return
    report.ok(f"model {_rel(path)} ({size / 1e6:.0f} MB)")


def check_models(report: Report) -> None:
    check_model(report, _resolve(load_app_settings().yolo_model_path))
    check_model(report, _resolve(load_database_settings().dino_model_path))


def read_csv_slugs(csv_path: Path) -> list[str]:
    with csv_path.open(encoding="utf-8", newline="") as handle:
        return [
            (row.get(COL_SLUG) or "").strip()
            for row in csv.DictReader(handle)
            if (row.get(COL_SLUG) or "").strip()
        ]


def check_catalog_sources(
    report: Report, csv_path: Path, site_json: Path, images_dir: Path
) -> None:
    """CSV владельца, JSON сайта и фото ``{slug}.webp`` для индексации."""
    slugs: list[str] = []
    csv_name = _rel(csv_path)
    if not csv_path.is_file():
        report.fail(
            f"catalog CSV {csv_name} not found",
            "it is tracked in git: git checkout -- data/",
        )
    else:
        slugs = read_csv_slugs(csv_path)
        if slugs:
            report.ok(f"catalog CSV {csv_name} ({len(slugs)} wines)")
        else:
            report.fail(f"catalog CSV {csv_name} has no rows with column {COL_SLUG!r}")

    if site_json.is_file():
        report.ok(f"site JSON {_rel(site_json)}")
    else:
        report.warn(
            f"site JSON {_rel(site_json)} not found (no rating / dishes / links)",
            "it is tracked in git: git checkout -- data/site_database/",
        )

    images_name = _rel(images_dir)
    photos_hint = (
        f"download {IMAGES_HINT} and unpack {{slug}}.webp files "
        f"directly into {images_name}/"
    )
    has_dir = images_dir.is_dir()
    photos = {p.stem for p in images_dir.glob("*.webp")} if has_dir else set()
    if not photos:
        subdirs = [d for d in images_dir.iterdir() if d.is_dir()] if has_dir else []
        nested = [d for d in subdirs if any(d.glob("*.webp"))]
        extra = (
            f" (found photos in subfolder {_rel(nested[0])}/ — move them one level up)"
            if nested
            else ""
        )
        report.fail(f"no catalog photos *.webp in {images_name}/{extra}", photos_hint)
        return
    if not slugs:
        report.ok(f"catalog photos: {len(photos)} files")
        return
    missing = [s for s in slugs if s not in photos]
    if not missing:
        report.ok(f"catalog photos: all {len(slugs)} wines have a photo")
    elif len(missing) <= MAX_MISSING_PHOTO_SHARE * len(slugs):
        report.ok(
            f"catalog photos: {len(slugs) - len(missing)} of {len(slugs)} wines "
            f"({len(missing)} without photo are skipped by indexing)"
        )
    else:
        sample = ", ".join(missing[:3])
        report.fail(
            f"catalog photos: {len(missing)} of {len(slugs)} wines have no photo "
            f"(e.g. {sample})",
            photos_hint,
        )


def check_db(report: Report, *, need_wines: bool) -> None:
    """БД доступна; для ``serve`` — в ней есть вина с эмбеддингами."""
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError

    from db.session import create_db_engine

    try:
        engine = create_db_engine()
    except RuntimeError as exc:
        report.fail("DATABASE_URL", str(exc))
        return
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            if not need_wines:
                report.ok("database reachable")
                return
            exists = conn.execute(
                text("SELECT to_regclass('public.wines') IS NOT NULL")
            ).scalar()
            if not exists:
                report.fail("database has no table wines", INDEX_HINT)
                return
            total, embedded = conn.execute(
                text("SELECT count(*), count(embedding) FROM wines")
            ).one()
    except SQLAlchemyError as exc:
        report.fail(
            f"database not reachable ({type(exc).__name__})",
            "start it: docker compose up -d db",
        )
        return
    finally:
        engine.dispose()
    if embedded == 0:
        report.fail(f"database: {total} wines, none with embeddings", INDEX_HINT)
    elif embedded < total:
        report.warn(f"database: {embedded}/{total} wines have embeddings", INDEX_HINT)
    else:
        report.ok(f"database: {total} wines with embeddings")


def check_static(report: Report, static_dir: Path) -> None:
    count = sum(1 for _ in static_dir.glob("*.webp")) if static_dir.is_dir() else 0
    if count:
        report.ok(f"UI photos: {count} files in {_rel(static_dir)}/")
    else:
        report.warn(f"no UI photos in {_rel(static_dir)}/ (not shown)", INDEX_HINT)


def run(mode: str, csv_path: Path, images_dir: Path) -> Report:
    report = Report()
    check_models(report)
    if mode == "index":
        check_catalog_sources(report, csv_path, DEFAULT_SITE_JSON, images_dir)
        check_db(report, need_wines=False)
    else:
        check_db(report, need_wines=True)
        check_static(report, DEFAULT_STATIC)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=("index", "serve"), default="index")
    parser.add_argument("--input", type=Path, default=DEFAULT_CSV, help="owner CSV")
    parser.add_argument("--images-dir", type=Path, default=DEFAULT_IMAGES)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    report = run(args.mode, args.input, args.images_dir)
    print(f"== preflight ({args.mode})")
    print("\n".join(report.lines))
    if report.errors:
        print(f"preflight FAILED: {report.errors} problem(s), see → hints above")
        return 1
    print(f"preflight OK ({report.warnings} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
