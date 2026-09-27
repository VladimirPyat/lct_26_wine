#!/usr/bin/env python3
"""Bring near_clusters to one flat layout for group scanning.

Canonical layout (per winery dir from by_manufact_index.csv)::

    near_clusters/<dir>/
      <group>/          # any subdir with images = one near-group
        *.webp          # symlinks → crop/
      singletons/       # all leftovers in ONE folder (browse-friendly);
                        # scanner still treats each file as its own group
      (no root images)  # root leftovers are folded into singletons/

Sources
-------
- n <= 5: by_manufact flat files → one group ``group``
- 6..10: by_manufact as curated (numbered dirs + root files → singletons)
- n > 10 (and any already in near_clusters): lift ``pipe_*`` / ``simple_*`` /
  flatten ``by_brand/brand_*/…``; brand singletons merge into one ``singletons/``

Wrappers ``pipe_*``, ``simple_*``, ``by_brand`` are removed (old tree → .trash).

Example::

    uv run python scripts/unify_near_clusters.py
    uv run python scripts/unify_near_clusters.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import logging
import shutil
import time
from pathlib import Path

logger = logging.getLogger("unify_near_clusters")

_REPO = Path(__file__).resolve().parents[1]
_DATA = _REPO / "data" / "train_dataset"
INDEX = _DATA / "by_manufact_index.csv"
BY_MANUFACT = _DATA / "by_manufact"
NEAR = _DATA / "near_clusters"
CROP = _DATA / "crop"
TRASH = _REPO / ".trash" / "near_unify"

_IMG_EXT = {".webp", ".jpg", ".jpeg", ".png"}
_TAG_PREFIXES = ("pipe_", "simple_")
_META_NAMES = {
    "membership.csv",
    "summary.json",
    "near_edges.csv",
    "near_edges_all.csv",
    "pairs_above_threshold.csv",
    "absorb_events.json",
    "brands.csv",
    "index.json",
}
_SKIP_ROOT = {"_meta", "_staging"}


def _is_img(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in _IMG_EXT


def _list_imgs(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return sorted(p for p in path.iterdir() if _is_img(p))


def _symlink_to_crop(src: Path, dst: Path) -> None:
    """Create symlink at dst pointing at crop/ (resolve through existing links)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        return
    target = src.resolve()
    # Prefer crop/ relative name if file lives there
    crop_hit = CROP / target.name
    if crop_hit.is_file():
        target = crop_hit.resolve()
    dst.symlink_to(target)


def _trash(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    TRASH.mkdir(parents=True, exist_ok=True)
    dest = TRASH / f"{path.name}_{int(time.time_ns())}"
    shutil.move(str(path), str(dest))
    logger.info("trash → %s", dest)


def _copy_imgs_as_links(src_dir: Path, dst_dir: Path) -> int:
    n = 0
    for img in _list_imgs(src_dir):
        _symlink_to_crop(img, dst_dir / img.name)
        n += 1
    return n


def _collect_from_by_manufact(src: Path, dst: Path) -> dict:
    """Copy curated by_manufact layout (numbered groups + root leftovers)."""
    stats = {"groups": 0, "group_imgs": 0, "root_imgs": 0}
    if not src.is_dir():
        logger.warning("missing by_manufact %s", src)
        return stats

    subdirs = sorted(p for p in src.iterdir() if p.is_dir() and not p.name.startswith("."))
    for sub in subdirs:
        imgs = _list_imgs(sub)
        if not imgs:
            continue
        out = dst / sub.name
        out.mkdir(parents=True, exist_ok=True)
        stats["group_imgs"] += _copy_imgs_as_links(sub, out)
        stats["groups"] += 1

    for img in _list_imgs(src):
        sing = dst / "singletons"
        sing.mkdir(parents=True, exist_ok=True)
        _symlink_to_crop(img, sing / img.name)
        stats["root_imgs"] += 1
    return stats


def _collect_flat_group(src: Path, dst: Path, group_name: str = "group") -> dict:
    """All images under src (top-level) → one near-group."""
    stats = {"groups": 0, "group_imgs": 0, "root_imgs": 0}
    imgs = _list_imgs(src)
    if not imgs:
        # maybe already nested as single folder
        return _collect_from_by_manufact(src, dst)
    out = dst / group_name
    out.mkdir(parents=True, exist_ok=True)
    for img in imgs:
        _symlink_to_crop(img, out / img.name)
    stats["groups"] = 1
    stats["group_imgs"] = len(imgs)
    return stats


def _lift_tag_dir(tag_dir: Path, dst: Path) -> dict:
    """Lift cluster_*/numbered/singletons/root imgs from pipe_* or simple_*."""
    stats = {"groups": 0, "group_imgs": 0, "root_imgs": 0, "singletons": 0}
    for child in sorted(tag_dir.iterdir()):
        if child.name in _META_NAMES:
            continue
        if child.is_file() and _is_img(child):
            sing = dst / "singletons"
            sing.mkdir(parents=True, exist_ok=True)
            _symlink_to_crop(child, sing / child.name)
            stats["root_imgs"] += 1
            continue
        if not child.is_dir():
            continue
        imgs = _list_imgs(child)
        if not imgs:
            continue
        out = dst / child.name
        out.mkdir(parents=True, exist_ok=True)
        n = _copy_imgs_as_links(child, out)
        if child.name == "singletons":
            stats["singletons"] += n
        else:
            stats["groups"] += 1
            stats["group_imgs"] += n
    return stats


def _flatten_by_brand(brand_root: Path, dst: Path) -> dict:
    """by_brand/brand_X/{cluster_*,singletons,numbered} → brand_X__name/."""
    stats = {"groups": 0, "group_imgs": 0, "root_imgs": 0, "singletons": 0}
    for brand_dir in sorted(brand_root.iterdir()):
        if not brand_dir.is_dir():
            continue
        brand = brand_dir.name
        if brand.startswith("brand_"):
            brand_key = brand[len("brand_") :]
        else:
            brand_key = brand
        for child in sorted(brand_dir.iterdir()):
            if child.name in _META_NAMES:
                continue
            if child.is_file() and _is_img(child):
                # rare: images directly under brand
                out = dst / f"{brand_key}__root"
                out.mkdir(parents=True, exist_ok=True)
                _symlink_to_crop(child, out / child.name)
                stats["group_imgs"] += 1
                stats["groups"] += 1
                continue
            if not child.is_dir():
                continue
            imgs = _list_imgs(child)
            if not imgs:
                continue
            if child.name == "singletons":
                out = dst / "singletons"
            else:
                out = dst / f"{brand_key}__{child.name}"
            out.mkdir(parents=True, exist_ok=True)
            n = _copy_imgs_as_links(child, out)
            if child.name == "singletons":
                stats["singletons"] += n
            else:
                stats["groups"] += 1
                stats["group_imgs"] += n
    return stats


def _find_active_source(winery_dir: str, n: int) -> tuple[str, Path | None]:
    """Return (kind, path) for content to materialize."""
    bm = BY_MANUFACT / winery_dir
    nc = NEAR / winery_dir

    if n <= 5:
        return "bm_flat", bm if bm.is_dir() else None

    if n <= 10:
        # Curated clusters live in by_manufact (user-edited).
        return "bm_curated", bm if bm.is_dir() else None

    # Large: prefer existing near_clusters tags
    if nc.is_dir():
        brands = nc / "by_brand"
        if brands.is_dir():
            return "nc_by_brand", brands
        for child in sorted(nc.iterdir()):
            if child.is_dir() and (
                child.name.startswith(_TAG_PREFIXES) or child.name.startswith("simple_")
            ):
                return "nc_tag", child
        # already flat?
        has_groups = any(
            p.is_dir() and not p.name.startswith(".") for p in nc.iterdir()
        ) or any(_is_img(p) for p in nc.iterdir())
        if has_groups:
            return "nc_flat", nc
    return "missing", None


def _materialize(winery_dir: str, n: int, staging: Path, *, dry_run: bool) -> dict:
    kind, src = _find_active_source(winery_dir, n)
    dst = staging / winery_dir
    row = {"dir": winery_dir, "n": n, "kind": kind, "ok": False}
    if src is None:
        logger.error("no source for %s kind=%s", winery_dir, kind)
        return row

    logger.info("%s n=%s kind=%s ← %s", winery_dir, n, kind, src)
    if dry_run:
        row["ok"] = True
        return row

    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)

    if kind == "bm_flat":
        stats = _collect_flat_group(src, dst, group_name="group")
    elif kind == "bm_curated":
        stats = _collect_from_by_manufact(src, dst)
    elif kind == "nc_by_brand":
        stats = _flatten_by_brand(src, dst)
    elif kind == "nc_tag":
        stats = _lift_tag_dir(src, dst)
    elif kind == "nc_flat":
        # Re-link existing flat tree into staging (skip tag wrappers if any)
        stats = {"groups": 0, "group_imgs": 0, "root_imgs": 0, "singletons": 0}
        for child in sorted(src.iterdir()):
            if child.name in _META_NAMES:
                continue
            if child.is_dir() and (
                child.name == "by_brand"
                or child.name.startswith(_TAG_PREFIXES)
                or child.name.startswith("simple_")
            ):
                continue
            if _is_img(child):
                _symlink_to_crop(child, dst / child.name)
                stats["root_imgs"] += 1
            elif child.is_dir():
                imgs = _list_imgs(child)
                if not imgs:
                    continue
                out = dst / child.name
                out.mkdir(parents=True, exist_ok=True)
                nn = _copy_imgs_as_links(child, out)
                if child.name == "singletons" or child.name.endswith("__singletons"):
                    stats["singletons"] = stats.get("singletons", 0) + nn
                else:
                    stats["groups"] += 1
                    stats["group_imgs"] += nn
    else:
        return row

    row.update(stats)
    row["ok"] = True
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Only process these winery dir names (repeatable)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    rows = list(csv.DictReader(INDEX.open(encoding="utf-8")))
    if args.only:
        want = set(args.only)
        rows = [r for r in rows if r["dir"] in want]

    staging = NEAR / "_staging"
    if not args.dry_run:
        if staging.exists():
            _trash(staging)
        staging.mkdir(parents=True, exist_ok=True)
        meta = NEAR / "_meta"
        meta.mkdir(parents=True, exist_ok=True)
        for name in ("brand_batch_gt31.csv", "brand_batch_run.log"):
            p = NEAR / name
            if p.exists():
                dest = meta / name
                if dest.exists():
                    _trash(dest)
                shutil.move(str(p), str(dest))

    results = []
    for r in rows:
        winery = r["dir"]
        n = int(r["n_crops"])
        results.append(_materialize(winery, n, staging, dry_run=args.dry_run))

    if args.dry_run:
        ok = sum(1 for x in results if x.get("ok"))
        logger.info("dry-run done ok=%s / %s", ok, len(results))
        for x in results:
            print(f"{x['dir']}\tn={x['n']}\tkind={x['kind']}\tok={x.get('ok')}")
        return 0 if all(x.get("ok") for x in results) else 1

    # Swap: trash old winery dirs, move staging in
    for x in results:
        if not x.get("ok"):
            continue
        old = NEAR / x["dir"]
        if old.exists():
            _trash(old)
        shutil.move(str(staging / x["dir"]), str(NEAR / x["dir"]))

    if staging.exists():
        leftover = list(staging.iterdir())
        if leftover:
            logger.warning("staging leftovers: %s", [p.name for p in leftover])
        else:
            staging.rmdir()

    report = NEAR / "_meta" / "unify_report.csv"
    report.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "dir",
        "n",
        "kind",
        "ok",
        "groups",
        "group_imgs",
        "root_imgs",
        "singletons",
    ]
    with report.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for x in results:
            w.writerow(x)

    ok = sum(1 for x in results if x.get("ok"))
    logger.info("unify done ok=%s / %s report=%s", ok, len(results), report)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
