#!/usr/bin/env python3
"""Build margin-tier inventory from near_groups (after human near_clusters review).

Run when labeling is ready::

    # 1) rescan folders → near_clusters/_meta/near_groups.csv
    uv run python scripts/scan_near_groups.py

    # 2) tier tables + copy into embed_train_data/near/ for Colab
    uv run python scripts/build_margin_tiers.py

Or both in one shot::

    uv run python scripts/build_margin_tiers.py --scan

Outputs (default under ``data/train_dataset/embed_train_data/near/``):

- ``near_groups.csv`` — scan + catalog orphans reconciled to full catalog/train
- ``catalog_orphans.csv`` — files that were in catalog but missing from near_clusters
- ``margin_tiers.csv`` — per-file: group, winery, kind, n_near_mates, n_sw_mates
- ``margin_tier_report.md`` — human summary for QA before Phase3b
- ``margin_tier_stats.json`` — machine summary

Reconcile uses ``by_manufact_index.csv`` (1973 clustered) + ``catalog/train`` (2006):
the delta (~33) are small/forgotten makers → singletons, weak same-winery only.

Tier mapping (Phase3b plan):

- same ``group_id`` + ``kind=cluster`` → near (P1 / m_near)
- same winery, different group → same-winery (N1 / m_sw)
- else → eligible for far hard-mine (N2 / m_far)
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger("build_margin_tiers")

_REPO = Path(__file__).resolve().parents[1]
_DATA = _REPO / "data" / "train_dataset"
_SCAN_DEFAULT = _DATA / "near_clusters" / "_meta" / "near_groups.csv"
_OUT_DEFAULT = _DATA / "embed_train_data" / "near"
_CATALOG_DEFAULT = _DATA / "embed_train_data" / "dataset" / "catalog" / "train"
_INDEX_DEFAULT = _DATA / "by_manufact_index.csv"
_IMG_EXT = {".webp", ".jpg", ".jpeg", ".png"}

# filename stem prefix → existing near_clusters / index dir (when orphan belongs to known maker)
_ORPHAN_WINERY_ALIASES = {
    "golubitskoe-estate": "031_Golubitskoe Estate",
    "golubitskoe-rose": "031_Golubitskoe Estate",
    "golubitskoe": "031_Golubitskoe Estate",
    "satera-satera-esse": "052_ESSE",
}


def _load_near_groups(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _list_catalog(catalog: Path) -> list[str]:
    if not catalog.is_dir():
        return []
    return sorted(
        p.name for p in catalog.iterdir() if p.is_file() and p.suffix.lower() in _IMG_EXT
    )


def _load_index_dirs(index: Path) -> list[str]:
    if not index.is_file():
        return []
    return [r["dir"] for r in csv.DictReader(index.open(encoding="utf-8"))]


def _infer_orphan_winery(filename: str, index_dirs: list[str]) -> str:
    stem = Path(filename).stem.lower().replace("_", "-")
    for prefix, winery in sorted(_ORPHAN_WINERY_ALIASES.items(), key=lambda x: -len(x[0])):
        if stem.startswith(prefix) or prefix in stem:
            return winery
    # match against index dir name only if slug is long enough and clearly in stem
    best = None
    best_len = 0
    for d in index_dirs:
        name = d.split("_", 1)[-1].lower().replace(" ", "-").replace("_", "-")
        if len(name) < 6:
            continue
        if stem.startswith(name) or f"-{name}-" in f"-{stem}-" or stem.endswith(f"-{name}"):
            if len(name) > best_len:
                best, best_len = d, len(name)
    return best or ""


def _brand_key(filename: str) -> str:
    """Group orphan pairs that share a brand-like prefix."""
    stem = Path(filename).stem.lower()
    for prefix in (
        "a-gordienko-m-nikolaev",
        "aromatnoe",
        "artvin",
        "golubitskoe",
        "orlov",
        "radiowine",
        "semeynaya-vinodelnya-mihaila-kolesnikova",
        "viktor-stashko",
        "wein-und-wasser",
        "yaiyla",
        "ya-jla",
        "fioletovyj",
    ):
        key = stem.replace("_", "-")
        if key.startswith(prefix) or stem.startswith(prefix):
            if prefix in {"ya-jla", "yaiyla"}:
                return "yaiyla"
            return prefix
    return stem.replace("_", "-")


def reconcile_catalog_orphans(
    rows: list[dict],
    *,
    catalog: Path,
    index: Path,
) -> tuple[list[dict], list[dict]]:
    """Append catalog files missing from near_groups as singletons (weak SW only)."""
    have = {r["file"] for r in rows}
    catalog_files = _list_catalog(catalog)
    missing = [f for f in catalog_files if f not in have]
    if not missing:
        return rows, []

    index_dirs = _load_index_dirs(index)
    # brand_key → list of files
    by_brand: dict[str, list[str]] = defaultdict(list)
    for f in missing:
        by_brand[_brand_key(f)].append(f)

    extra: list[dict] = []
    for brand, files in sorted(by_brand.items()):
        # prefer alias/index winery from any file
        winery = ""
        for f in files:
            winery = _infer_orphan_winery(f, index_dirs)
            if winery:
                break
        if not winery:
            # synthetic small maker: all files in brand share weak SW
            winery = f"000_orphan::{brand}"
        for f in files:
            stem = Path(f).stem
            extra.append(
                {
                    "file": f,
                    "path": f"catalog_orphan/{winery}/{f}",
                    "winery": winery,
                    "group_id": f"{winery}::catalog_orphan::{stem}",
                    "kind": "catalog_orphan",
                    "group_folder": "catalog_orphan",
                }
            )
    logger.info(
        "catalog reconcile: catalog=%s near_groups=%s orphans_added=%s",
        len(catalog_files),
        len(have),
        len(extra),
    )
    return rows + extra, extra


def _build_tiers(rows: list[dict]) -> tuple[list[dict], dict]:
    by_group: dict[str, list[str]] = defaultdict(list)
    by_winery: dict[str, list[str]] = defaultdict(list)
    meta: dict[str, dict] = {}

    for r in rows:
        fn = r["file"]
        meta[fn] = r
        by_group[r["group_id"]].append(fn)
        by_winery[r["winery"]].append(fn)

    tier_rows: list[dict] = []
    n_near_edges = 0
    n_sw_edges = 0

    for fn, r in meta.items():
        gid = r["group_id"]
        winery = r["winery"]
        kind = r.get("kind", "")
        group_mates = [x for x in by_group[gid] if x != fn]
        # near mates only for multi-member clusters
        if kind == "cluster" and len(by_group[gid]) > 1:
            near_mates = group_mates
        else:
            near_mates = []
        sw_mates = [
            x
            for x in by_winery[winery]
            if x != fn and meta[x]["group_id"] != gid
        ]
        n_near_edges += len(near_mates)
        n_sw_edges += len(sw_mates)
        tier_rows.append(
            {
                "file": fn,
                "winery": winery,
                "group_id": gid,
                "kind": kind,
                "group_folder": r.get("group_folder", ""),
                "n_near_mates": len(near_mates),
                "n_sw_mates": len(sw_mates),
                "tier_primary": (
                    "near_cluster"
                    if near_mates
                    else ("singleton" if kind != "cluster" or len(by_group[gid]) == 1 else "cluster_solo")
                ),
            }
        )

    # undirected edge counts (each pair counted twice above)
    stats = {
        "n_files": len(tier_rows),
        "n_wineries": len(by_winery),
        "n_groups": len(by_group),
        "n_cluster_groups": len(
            {
                g
                for g, files in by_group.items()
                if any(meta[f].get("kind") == "cluster" for f in files) and len(files) > 1
            }
        ),
        "n_near_pair_directed": n_near_edges,
        "n_near_pairs_undirected": n_near_edges // 2,
        "n_sw_pair_directed": n_sw_edges,
        "n_sw_pairs_undirected": n_sw_edges // 2,
        "n_with_near_mates": sum(1 for t in tier_rows if int(t["n_near_mates"]) > 0),
        "n_with_sw_mates": sum(1 for t in tier_rows if int(t["n_sw_mates"]) > 0),
        "kind_counts": {},
    }
    kind_counts: dict[str, int] = defaultdict(int)
    for t in tier_rows:
        kind_counts[t["kind"] or "?"] += 1
    stats["kind_counts"] = dict(kind_counts)

    # per-winery rollup
    winery_stats = []
    for w, files in sorted(by_winery.items(), key=lambda x: -len(x[1])):
        cluster_groups = {
            meta[f]["group_id"]
            for f in files
            if meta[f].get("kind") == "cluster" and len(by_group[meta[f]["group_id"]]) > 1
        }
        winery_stats.append(
            {
                "winery": w,
                "n_files": len(files),
                "n_multi_clusters": len(cluster_groups),
                "n_with_near": sum(
                    1
                    for f in files
                    if meta[f].get("kind") == "cluster"
                    and len(by_group[meta[f]["group_id"]]) > 1
                ),
                "n_singletons_like": sum(
                    1
                    for f in files
                    if meta[f].get("kind") != "cluster"
                    or len(by_group[meta[f]["group_id"]]) == 1
                ),
            }
        )
    stats["wineries"] = winery_stats
    return tier_rows, stats


def _write_report(path: Path, stats: dict, src: Path) -> None:
    lines = [
        "# Margin tier report",
        "",
        f"Source: `{src}`",
        "",
        "## Totals",
        "",
        f"- files: **{stats['n_files']}**",
        f"- wineries: **{stats['n_wineries']}**",
        f"- groups: **{stats['n_groups']}** (multi-member clusters: **{stats['n_cluster_groups']}**)",
        f"- near pairs (undirected): **{stats['n_near_pairs_undirected']}**",
        f"- same-winery cross-group pairs (undirected): **{stats['n_sw_pairs_undirected']}**",
        f"- files with ≥1 near mate: **{stats['n_with_near_mates']}**",
        f"- files with ≥1 SW mate: **{stats['n_with_sw_mates']}**",
        f"- catalog orphans added: **{stats.get('catalog_orphans', 0)}**",
        "",
        "### kind counts",
        "",
        "| kind | n |",
        "|------|--:|",
    ]
    for k, n in sorted(stats["kind_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"| `{k}` | {n} |")
    orphan_files = stats.get("catalog_orphan_files") or []
    if orphan_files:
        lines.extend(["", "### Catalog orphans (not in near_clusters / index)", ""])
        for f in orphan_files:
            lines.append(f"- `{f}`")
    lines.extend(
        [
            "",
            "## Wineries (by size)",
            "",
            "| winery | n | multi-clusters | in near | singleton-like |",
            "|--------|--:|---------------:|--------:|---------------:|",
        ]
    )
    for w in stats["wineries"]:
        lines.append(
            f"| {w['winery']} | {w['n_files']} | {w['n_multi_clusters']} | "
            f"{w['n_with_near']} | {w['n_singletons_like']} |"
        )
    lines.extend(
        [
            "",
            "## Phase3b mapping",
            "",
            "| tier | margin knob | who |",
            "|------|-------------|-----|",
            "| P1 near | `m_near` | same multi-member `group_id` |",
            "| N1 same-winery | `m_sw` | same winery, other group |",
            "| N2 far | `m_far` | mined top-K, not near / not SW |",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Run scripts/scan_near_groups.py first",
    )
    parser.add_argument(
        "--near-groups",
        type=Path,
        default=_SCAN_DEFAULT,
        help="Input near_groups.csv (default: near_clusters/_meta/)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=_OUT_DEFAULT,
        help="Output dir (default: embed_train_data/near/)",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=_CATALOG_DEFAULT,
        help="Catalog train dir to reconcile against (default: embed_train catalog/train)",
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=_INDEX_DEFAULT,
        help="by_manufact_index.csv for orphan→winery hints",
    )
    parser.add_argument(
        "--no-catalog-reconcile",
        action="store_true",
        help="Do not append catalog files missing from near_groups",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.scan:
        cmd = [
            sys.executable,
            str(_REPO / "scripts" / "scan_near_groups.py"),
            "--out",
            str(args.near_groups),
        ]
        logger.info("running: %s", " ".join(cmd))
        rc = subprocess.call(cmd)
        if rc != 0:
            logger.error("scan_near_groups failed rc=%s", rc)
            return rc

    if not args.near_groups.is_file():
        logger.error(
            "missing %s — run scan_near_groups.py or pass --scan",
            args.near_groups,
        )
        return 1

    rows = _load_near_groups(args.near_groups)
    if not rows:
        logger.error("empty near_groups: %s", args.near_groups)
        return 1

    orphans: list[dict] = []
    if not args.no_catalog_reconcile:
        rows, orphans = reconcile_catalog_orphans(
            rows, catalog=args.catalog, index=args.index
        )

    # n<=3 among orphan synthetic wineries already singleton; also force small
    # known makers if somehow clustered (safety)
    by_w: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_w[r["winery"]].append(r)
    fixed: list[dict] = []
    for winery, wrows in by_w.items():
        if len(wrows) <= 3 and any(r.get("kind") == "cluster" for r in wrows):
            for r in wrows:
                stem = Path(r["file"]).stem
                fixed.append(
                    {
                        **r,
                        "group_id": f"{winery}::auto_singleton::{stem}",
                        "kind": "auto_singleton",
                        "group_folder": "auto_singleton",
                    }
                )
        else:
            fixed.extend(wrows)
    rows = fixed

    tier_rows, stats = _build_tiers(rows)
    stats["catalog_orphans"] = len(orphans)
    stats["catalog_orphan_files"] = [r["file"] for r in orphans]
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    fields_ng = ["file", "path", "winery", "group_id", "kind", "group_folder"]
    dst_groups = out / "near_groups.csv"
    with dst_groups.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields_ng)
        w.writeheader()
        w.writerows(rows)
    logger.info("wrote near_groups → %s (%s rows)", dst_groups, len(rows))
    # keep _meta scan copy + orphans in sync for SSOT
    if orphans or rows:
        meta_out = args.near_groups
        meta_out.parent.mkdir(parents=True, exist_ok=True)
        with meta_out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields_ng)
            w.writeheader()
            w.writerows(rows)
        logger.info("updated scan SSOT → %s", meta_out)

    if orphans:
        orphan_path = out / "catalog_orphans.csv"
        with orphan_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields_ng)
            w.writeheader()
            w.writerows(orphans)
        logger.info("orphan list → %s (%s)", orphan_path, len(orphans))

    tiers_path = out / "margin_tiers.csv"
    fields = [
        "file",
        "winery",
        "group_id",
        "kind",
        "group_folder",
        "n_near_mates",
        "n_sw_mates",
        "tier_primary",
    ]
    with tiers_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(tier_rows)
    logger.info("wrote %s (%s rows)", tiers_path, len(tier_rows))

    # strip heavy wineries list from json top-level duplicate — keep compact
    json_stats = {k: v for k, v in stats.items() if k != "wineries"}
    json_stats["wineries_top20"] = stats["wineries"][:20]
    json_path = out / "margin_tier_stats.json"
    json_path.write_text(json.dumps(json_stats, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = out / "margin_tier_report.md"
    _write_report(report_path, stats, args.near_groups)
    logger.info("wrote %s", report_path)

    print(
        f"OK files={stats['n_files']} near_pairs={stats['n_near_pairs_undirected']} "
        f"sw_pairs={stats['n_sw_pairs_undirected']} → {out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
