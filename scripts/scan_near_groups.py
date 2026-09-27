#!/usr/bin/env python3
"""Scan unified near_clusters layout → near_groups.csv.

Expected layout (per winery)::

    near_clusters/<dir>/
      <group>/          → one near-group (all members share group_id)
      brand_x__cluster/ → one near-group
      singletons/       → each image is its own group
      *.__singletons/   → each image is its own group (flattened brands)
      *.webp at root    → each image is its own group

group_id format: ``{winery_dir}::{folder_or_singleton_stem}``

Skips ``_meta``, ``_staging``. Wineries present in ``by_manufact_index.csv`` but
absent from ``near_clusters`` are taken from ``by_manufact`` as **per-image
singletons** (same-winery weak margin only — no near cluster).

**n ≤ 3 rule:** whatever the folder layout, a winery with 3 or fewer images is
forced to per-image singletons (reviewing near clusters is pointless at that size).

Example::

    uv run python scripts/scan_near_groups.py
    uv run python scripts/scan_near_groups.py --out data/train_dataset/near_clusters/_meta/near_groups.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path

logger = logging.getLogger("scan_near_groups")

_REPO = Path(__file__).resolve().parents[1]
_DATA = _REPO / "data" / "train_dataset"
INDEX = _DATA / "by_manufact_index.csv"
NEAR = _DATA / "near_clusters"
BY_MANUFACT = _DATA / "by_manufact"
DEFAULT_OUT = NEAR / "_meta" / "near_groups.csv"

_IMG_EXT = {".webp", ".jpg", ".jpeg", ".png"}
_SKIP_DIRS = {"_meta", "_staging", ".trash"}


def _is_img(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in _IMG_EXT


def _is_singleton_dir(name: str) -> bool:
    return name == "singletons" or name.endswith("__singletons")


def _list_imgs_flat(folder: Path) -> list[Path]:
    """Top-level images only (small wineries keep files flat in by_manufact)."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if _is_img(p))


def scan_winery(winery_dir: Path, *, path_root: Path = NEAR) -> list[dict]:
    rows: list[dict] = []
    winery = winery_dir.name

    for child in sorted(winery_dir.iterdir()):
        if child.name.startswith("."):
            continue
        if _is_img(child):
            gid = f"{winery}::root::{child.stem}"
            rows.append(
                {
                    "file": child.name,
                    "path": str(child.relative_to(path_root)),
                    "winery": winery,
                    "group_id": gid,
                    "kind": "root_singleton",
                    "group_folder": "",
                }
            )
            continue
        if not child.is_dir():
            continue
        imgs = sorted(p for p in child.iterdir() if _is_img(p))
        if not imgs:
            continue
        if _is_singleton_dir(child.name):
            for img in imgs:
                gid = f"{winery}::{child.name}::{img.stem}"
                rows.append(
                    {
                        "file": img.name,
                        "path": str(img.relative_to(path_root)),
                        "winery": winery,
                        "group_id": gid,
                        "kind": "singleton",
                        "group_folder": child.name,
                    }
                )
        else:
            gid = f"{winery}::{child.name}"
            for img in imgs:
                rows.append(
                    {
                        "file": img.name,
                        "path": str(img.relative_to(path_root)),
                        "winery": winery,
                        "group_id": gid,
                        "kind": "cluster",
                        "group_folder": child.name,
                    }
                )
    return _force_singletons_if_small(rows, winery=winery)


def _force_singletons_if_small(rows: list[dict], *, winery: str) -> list[dict]:
    """n <= 3 → each file its own group (weak same-winery only, no near)."""
    if len(rows) > 3:
        return rows
    out: list[dict] = []
    for r in rows:
        stem = Path(r["file"]).stem
        out.append(
            {
                **r,
                "group_id": f"{winery}::auto_singleton::{stem}",
                "kind": "auto_singleton",
                "group_folder": "auto_singleton",
            }
        )
    return out


def scan_winery_as_singletons(winery_dir: Path, *, path_root: Path) -> list[dict]:
    """Fallback for makers missing from near_clusters: per-image singletons."""
    winery = winery_dir.name
    imgs = _list_imgs_flat(winery_dir)
    if not imgs:
        for sub in sorted(winery_dir.iterdir()):
            if sub.is_dir():
                imgs.extend(sorted(p for p in sub.iterdir() if _is_img(p)))
    rows = [
        {
            "file": img.name,
            "path": str(img.relative_to(path_root)),
            "winery": winery,
            "group_id": f"{winery}::fallback::{img.stem}",
            "kind": "fallback_singleton",
            "group_folder": "fallback",
        }
        for img in imgs
    ]
    return _force_singletons_if_small(rows, winery=winery)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--index",
        type=Path,
        default=INDEX,
        help="by_manufact_index.csv (default: train_dataset one)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    index_dirs = []
    if args.index.is_file():
        index_dirs = [r["dir"] for r in csv.DictReader(args.index.open(encoding="utf-8"))]
    else:
        logger.warning("index missing %s — scan all near_clusters dirs", args.index)

    rows: list[dict] = []
    missing = []
    fallback = []
    targets = index_dirs or [
        p.name
        for p in sorted(NEAR.iterdir())
        if p.is_dir() and p.name not in _SKIP_DIRS and not p.name.startswith("_")
    ]

    for name in targets:
        if name in _SKIP_DIRS:
            continue
        d = NEAR / name
        if d.is_dir():
            part = scan_winery(d, path_root=NEAR)
            logger.info(
                "%s → %s files / %s groups",
                name,
                len(part),
                len({r["group_id"] for r in part}),
            )
            rows.extend(part)
            continue
        # Default: small / deleted from near_clusters → one group from by_manufact
        bm = BY_MANUFACT / name
        if bm.is_dir():
            part = scan_winery_as_singletons(bm, path_root=BY_MANUFACT)
            fallback.append(name)
            logger.info(
                "%s missing in near_clusters → by_manufact as singletons (%s files)",
                name,
                len(part),
            )
            rows.extend(part)
        else:
            missing.append(name)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["file", "path", "winery", "group_id", "kind", "group_folder"]
    with args.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    n_groups = len({r["group_id"] for r in rows})
    n_cluster = len({r["group_id"] for r in rows if r["kind"] == "cluster"})
    logger.info(
        "wrote %s files, %s groups (%s multi-member clusters) → %s",
        len(rows),
        n_groups,
        n_cluster,
        args.out,
    )
    if fallback:
        logger.info("fallback singletons from by_manufact: %s wineries", len(fallback))
    if missing:
        logger.warning("missing dirs (%s): %s", len(missing), missing[:10])

    # summary next to out
    summary = args.out.with_name("near_groups_summary.csv")
    by_winery: dict[str, dict] = {}
    for r in rows:
        s = by_winery.setdefault(
            r["winery"],
            {"winery": r["winery"], "n_files": 0, "n_groups": set(), "n_cluster_groups": set()},
        )
        s["n_files"] += 1
        s["n_groups"].add(r["group_id"])
        if r["kind"] == "cluster":
            s["n_cluster_groups"].add(r["group_id"])
    with summary.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["winery", "n_files", "n_groups", "n_cluster_groups"]
        )
        w.writeheader()
        for winery in sorted(by_winery):
            s = by_winery[winery]
            w.writerow(
                {
                    "winery": winery,
                    "n_files": s["n_files"],
                    "n_groups": len(s["n_groups"]),
                    "n_cluster_groups": len(s["n_cluster_groups"]),
                }
            )
    logger.info("summary → %s", summary)
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
