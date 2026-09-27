#!/usr/bin/env python3
"""Check that catalog crops (DB embeddings) and static full bottles are one image set.

For every slug of the import CSV:

1. set check — crop exists ⇔ static exists; no extra files in either dir;
2. static == source — byte-identical for WebP sources, same size otherwise;
3. crop ⊂ static — the crop is found inside the static bottle by
   ``cv2.matchTemplate`` (coarse downscaled, then exact full-res window) with
   grey-level RMSE ≤ ``--max-rmse``.

Writes a per-slug CSV report; exit 1 if any problem. No DB.

  uv run python scripts/catalog_prepare/verify_catalog_assets.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

_REPO = Path(__file__).resolve().parents[2]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from db.import_catalog import resolve_source_image  # noqa: E402

_REPORT_FIELDS = ("slug", "status", "detail", "match_rmse")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--csv",
        type=Path,
        default=_REPO / "scripts" / "catalog_prepare" / "wines_clean_ready.csv",
    )
    parser.add_argument(
        "--crops-dir", type=Path, default=_REPO / "data/tmp/catalog_crops"
    )
    parser.add_argument("--static-dir", type=Path, default=_REPO / "static/wines")
    parser.add_argument(
        "--clean-images", type=Path, default=_REPO / "data/clean/images"
    )
    parser.add_argument(
        "--owner-images", type=Path, default=_REPO / "data/owner_database/images"
    )
    parser.add_argument(
        "--site-images", type=Path, default=_REPO / "data/site_database/images"
    )
    parser.add_argument(
        "--review-csv",
        type=Path,
        default=_REPO / "data/tmp/catalog_crops_review/reasons.csv",
        help="Crop-pass quarantine reasons (slugs expected to have no crop)",
    )
    parser.add_argument(
        "--max-rmse",
        type=float,
        default=8.0,
        help="Max grey-level RMSE of crop vs static region (WebP noise ≈ 1-4)",
    )
    parser.add_argument(
        "--match-side",
        type=int,
        default=480,
        help="Static long side (px) for template matching",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=_REPO / "data/tmp/catalog_assets_check.csv",
    )
    return parser


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crop_match_rmse(static_bgr: np.ndarray, crop_bgr: np.ndarray, side: int) -> float:
    """Pixel RMSE of ``crop`` at its best position inside ``static`` (0 = exact).

    Coarse position by ``matchTemplate`` on a downscaled copy, then exact
    full-resolution search in a small window around it. A crop cut from this
    static differs only by WebP compression (RMSE of a few grey levels).
    """
    sh, sw = static_bgr.shape[:2]
    ch, cw = crop_bgr.shape[:2]
    if ch > sh or cw > sw:
        return float("inf")
    static_g = cv2.cvtColor(static_bgr, cv2.COLOR_BGR2GRAY)
    crop_g = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    scale = min(1.0, side / max(sh, sw))
    small_static = cv2.resize(
        static_g, (max(1, round(sw * scale)), max(1, round(sh * scale))),
        interpolation=cv2.INTER_AREA,
    )
    small_crop = cv2.resize(
        crop_g, (max(1, round(cw * scale)), max(1, round(ch * scale))),
        interpolation=cv2.INTER_AREA,
    )
    if (
        small_crop.shape[0] > small_static.shape[0]
        or small_crop.shape[1] > small_static.shape[1]
    ):
        return float("inf")
    coarse = cv2.matchTemplate(small_static, small_crop, cv2.TM_CCOEFF_NORMED)
    _, _, _, (sx, sy) = cv2.minMaxLoc(coarse)
    radius = int(np.ceil(2.0 / scale)) + 2
    x0 = max(0, round(sx / scale) - radius)
    y0 = max(0, round(sy / scale) - radius)
    x1 = min(sw, round(sx / scale) + radius + cw)
    y1 = min(sh, round(sy / scale) + radius + ch)
    window = static_g[y0:y1, x0:x1]
    if window.shape[0] < ch or window.shape[1] < cw:
        return float("inf")
    sqdiff = cv2.matchTemplate(
        window.astype(np.float32), crop_g.astype(np.float32), cv2.TM_SQDIFF
    )
    return float(np.sqrt(max(0.0, float(sqdiff.min())) / (ch * cw)))


def _load_review_slugs(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["slug"] for row in csv.DictReader(handle) if row.get("slug")}


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    with args.csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    review = _load_review_slugs(args.review_csv)
    crop_files = {p.stem for p in args.crops_dir.glob("*.webp")}
    static_files = {p.stem for p in args.static_dir.glob("*.webp")}
    csv_slugs = {row["slug"] for row in rows}

    report: list[dict[str, object]] = []

    def add(
        slug: str, status: str, detail: str = "", rmse: float | None = None
    ) -> None:
        shown = "" if rmse is None else f"{rmse:.3f}"
        report.append(
            {"slug": slug, "status": status, "detail": detail, "match_rmse": shown}
        )

    for slug in sorted(crop_files - csv_slugs):
        add(slug, "extra_crop", "crop file not in CSV")
    for slug in sorted(static_files - csv_slugs):
        add(slug, "extra_static", "static file not in CSV")

    for row in rows:
        slug = row["slug"]
        has_crop, has_static = slug in crop_files, slug in static_files
        if not has_crop and not has_static:
            add(slug, "review" if slug in review else "no_assets")
            continue
        if has_crop != has_static:
            add(slug, "crop_without_static" if has_crop else "static_without_crop")
            continue

        crop_path = args.crops_dir / f"{slug}.webp"
        static_path = args.static_dir / f"{slug}.webp"
        source = resolve_source_image(
            row,
            owner_images=args.owner_images,
            site_images=args.site_images,
            clean_images=args.clean_images,
        )
        static_bgr = cv2.imread(str(static_path))
        crop_bgr = cv2.imread(str(crop_path))
        if static_bgr is None or crop_bgr is None:
            add(slug, "unreadable")
            continue
        if source is None:
            add(slug, "source_missing")
            continue
        if source.suffix.lower() == ".webp":
            if _sha256(source) != _sha256(static_path):
                add(slug, "static_differs_from_source", str(source))
                continue
        else:
            source_bgr = cv2.imread(str(source))
            if source_bgr is None or source_bgr.shape[:2] != static_bgr.shape[:2]:
                add(slug, "static_differs_from_source", str(source))
                continue
        rmse = crop_match_rmse(static_bgr, crop_bgr, args.match_side)
        if rmse > args.max_rmse:
            add(slug, "crop_not_in_static", "", rmse)
            continue
        add(slug, "ok", "", rmse)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(report)

    counts = Counter(str(item["status"]) for item in report)
    scores = [float(str(i["match_rmse"])) for i in report if i["match_rmse"] != ""]
    print(f"csv rows={len(rows)} crops={len(crop_files)} static={len(static_files)}")
    print("status:", dict(sorted(counts.items())))
    if scores:
        median = float(np.median(scores))
        p99 = float(np.quantile(scores, 0.99))
        print(f"match_rmse: median={median:.3f} p99={p99:.3f} max={max(scores):.3f}")
    print(f"report → {args.report}")
    bad = {k: v for k, v in counts.items() if k not in {"ok", "review"}}
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
