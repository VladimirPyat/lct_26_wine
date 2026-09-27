#!/usr/bin/env python3
"""Brand-prefix buckets for large wineries, then simple/pipeline inside each brand.

Known rules (Kuban-Vino) or auto slug discovery. If no clear brands → one
bucket ``all``. Assumption: different brands are not near-duplicates.

Per brand size:
  n <= 5  → one near-group (all members near each other)
  6..20   → simple spherical k-means (k = n // 5)
  n > 20  → hard CC 0.85 + soft pipeline 0.60

Batch (default): all by_manufact with n > 30, skip hand-curated Kuban.

Example:
  uv run python scripts/brand_then_cluster.py
  uv run python scripts/brand_then_cluster.py --folder 020_Фанагория
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
_SCRIPTS = _REPO_ROOT / "scripts"
for _p in (_SRC, _SCRIPTS, str(_REPO_ROOT)):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from cluster_manufact_near import (  # noqa: E402
    BY_MANUFACT,
    OUT_ROOT,
    _encode_folder,
    _list_images,
    _spherical_kmeans,
    pipeline_three_pass,
    _UnionFind,
)

logger = logging.getLogger("brand_then_cluster")

_IMG_EXT = {".webp", ".jpg", ".jpeg", ".png"}


def _strip_winery_prefix(stem: str, folder_name: str) -> str:
    """Remove common winery slug prefix derived from folder name."""
    # 096_Кубань-Вино → try kuban-vino-
    base = re.sub(r"^\d+_", "", folder_name)
    # translit-ish known map
    aliases = {
        "Кубань-Вино": ["kuban-vino-", "kuban_vino-"],
    }
    for pref in aliases.get(base, []):
        if stem.startswith(pref):
            return stem[len(pref) :]
    # generic: if stem starts with latin slug of first word — leave as is
    if stem.startswith("kuban-vino-"):
        return stem[len("kuban-vino-") :]
    return stem


def brand_key_kuban(stem: str) -> str:
    """Stable trademark key for Kuban-Vino catalog slugs."""
    s = stem.lower()

    # Specific lines first (may contain 'de-tamane' / 'taman' in the rest of slug)
    if s.startswith("aristov"):
        return "aristov"

    if s.startswith("vysokiy-bereg") or s.startswith("vysokij-bereg"):
        return "vysokiy_bereg"

    if s.startswith("flyor-dyu") or s.startswith("fleur-du"):
        return "fleur_du_sud"

    if s.startswith("lesnaya"):
        return "lesnaya_proseka"

    if s.startswith("makitra"):
        return "makitra"

    # Chateau Tamagne / Шато Тамань (many spellings)
    if (
        s.startswith("shato-taman")
        or s.startswith("shato-tamane")
        or s.startswith("chateau-tamagne")
        or "shato-taman" in s
        or re.search(r"(^|-)de-tamane(-|$)", s)
        or re.search(r"(^|-)de-tamagne(-|$)", s)
    ):
        return "chateau_tamagne"

    parts = s.split("-")
    if len(parts) >= 2:
        return f"other_{parts[0]}_{parts[1]}"
    return f"other_{parts[0]}"


BRAND_FN = {
    "096_Кубань-Вино": brand_key_kuban,
}


def _detect_winery_prefix(stems: list[str]) -> str:
    """Shared leading slug tokens present in most filenames (e.g. fanagoriya-)."""
    if not stems:
        return ""
    first = Counter(s.split("-")[0] for s in stems)
    top1, c1 = first.most_common(1)[0]
    if c1 < 0.7 * len(stems):
        return ""
    two = Counter(
        "-".join(s.split("-")[:2])
        for s in stems
        if s.startswith(top1 + "-") and len(s.split("-")) >= 2
    )
    if two:
        top2, c2 = two.most_common(1)[0]
        if c2 >= 0.55 * len(stems):
            return top2 + "-"
    return top1 + "-"


def _strip_prefix(stem: str, prefix: str) -> str:
    if prefix and stem.startswith(prefix):
        return stem[len(prefix) :]
    return stem


def discover_brands_auto(
    paths: list[Path],
    *,
    min_brand: int = 5,
    min_brands: int = 2,
    min_coverage: float = 0.45,
) -> dict[str, list[Path]]:
    """Infer brand/line keys from slug prefixes; else one bucket ``all``."""
    stems = [p.stem.lower() for p in paths]
    winery_prefix = _detect_winery_prefix(stems)
    stripped = [_strip_prefix(s, winery_prefix) for s in stems]
    logger.info(
        "auto brands: winery_prefix=%r stripped_example=%r",
        winery_prefix,
        stripped[0] if stripped else None,
    )

    counts: Counter[str] = Counter()
    for s in stripped:
        parts = [p for p in s.split("-") if p]
        if not parts:
            continue
        counts[parts[0]] += 1
        if len(parts) >= 2:
            counts["-".join(parts[:2])] += 1

    # Candidate keys with enough members; prefer longer keys when assigning
    candidates = sorted(
        (k for k, v in counts.items() if v >= min_brand),
        key=lambda k: (-len(k.split("-")), -counts[k], k),
    )
    # Drop 1-token keys that are only a prefix of a qualifying 2-token key
    # with almost the same count (e.g. primum vs primum-alveus)
    filtered: list[str] = []
    for k in candidates:
        dominated = False
        if "-" not in k:
            for other in candidates:
                if other.startswith(k + "-") and counts[other] >= 0.8 * counts[k]:
                    dominated = True
                    break
        if not dominated:
            filtered.append(k)
    candidates = filtered

    def assign_key(s: str) -> str | None:
        for k in candidates:  # longer first
            if s == k or s.startswith(k + "-"):
                return k.replace("-", "_")
        return None

    buckets: dict[str, list[Path]] = defaultdict(list)
    for path, s in zip(paths, stripped, strict=True):
        key = assign_key(s)
        if key is None:
            buckets["other"].append(path)
        else:
            buckets[key].append(path)

    # Keep only brands with >= min_brand; fold tiny into other
    final: dict[str, list[Path]] = {}
    other: list[Path] = list(buckets.pop("other", []))
    for k, items in buckets.items():
        if len(items) >= min_brand:
            final[k] = items
        else:
            other.extend(items)
    if other:
        final.setdefault("other", []).extend(other)

    multi = {k: v for k, v in final.items() if k != "other" and len(v) >= min_brand}
    covered = sum(len(v) for v in multi.values())
    if len(multi) < min_brands or covered < min_coverage * len(paths):
        logger.info(
            "auto brands: no clear split (multi=%s coverage=%.2f) → all",
            len(multi),
            covered / max(len(paths), 1),
        )
        return {"all": list(paths)}

    logger.info(
        "auto brands: %s",
        {k: len(v) for k, v in sorted(final.items(), key=lambda x: -len(x[1]))},
    )
    return dict(final)


def assign_brands(folder: Path) -> dict[str, list[Path]]:
    paths = _list_images(folder)
    key_fn = BRAND_FN.get(folder.name)
    if key_fn is not None:
        buckets: dict[str, list[Path]] = defaultdict(list)
        for path in paths:
            stem = _strip_winery_prefix(path.stem, folder.name)
            buckets[key_fn(stem)].append(path)
        return dict(buckets)
    return discover_brands_auto(paths)


def _cluster_paths_simple(paths: list[Path], *, divisor: int = 5) -> list[list[Path]]:
    if len(paths) < 2:
        return [paths]
    emb = _encode_folder(paths)
    k = max(1, len(paths) // divisor)
    labels = _spherical_kmeans(emb, k)
    groups: dict[int, list[Path]] = defaultdict(list)
    for i, path in enumerate(paths):
        groups[int(labels[i])].append(path)
    return [groups[i] for i in sorted(groups.keys())]


def _cluster_paths_pipeline(
    paths: list[Path],
    *,
    hard: float = 0.85,
    soft: float = 0.60,
) -> tuple[list[list[Path]], dict]:
    """Run hard CC + pipeline_three_pass on an arbitrary path list."""
    if len(paths) < 2:
        return [paths], {"mode": "tiny"}
    emb = _encode_folder(paths)
    uf = _UnionFind(len(paths))
    pairs: list[tuple[str, str, float]] = []
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            s = float(np.dot(emb[i], emb[j]))
            if s >= hard:
                uf.union(i, j)
                pairs.append((paths[i].name, paths[j].name, s))
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(paths)):
        groups[uf.find(i)].append(i)
    cluster_list = sorted(groups.values(), key=lambda idxs: (-len(idxs), idxs[0]))
    before = {
        "n_multi": sum(1 for c in cluster_list if len(c) >= 2),
        "n_sing": sum(1 for c in cluster_list if len(c) == 1),
    }
    cluster_list, events = pipeline_three_pass(
        cluster_list, emb, soft_threshold=soft, small_max=3, metric="max_member"
    )
    out_clusters = [[paths[i] for i in c] for c in cluster_list]
    summary = {
        "mode": "pipeline",
        "hard": hard,
        "soft": soft,
        "before": before,
        "events_tail": [e for e in events if e.get("action") == "pipeline_done"],
    }
    # stash for optional write
    summary["_emb"] = emb
    summary["_pairs"] = pairs
    summary["_idx_clusters"] = cluster_list
    return out_clusters, summary


def _write_brand_layout(
    out_dir: Path,
    brand: str,
    clusters: list[list[Path]],
    *,
    mode: str,
) -> dict:
    brand_dir = out_dir / f"brand_{brand}"
    if brand_dir.exists():
        trash = _REPO_ROOT / ".trash" / "brand_clusters" / brand_dir.name
        trash.parent.mkdir(parents=True, exist_ok=True)
        if trash.exists():
            trash = trash.with_name(f"{trash.name}_{brand_dir.stat().st_mtime_ns}")
        shutil.move(str(brand_dir), str(trash))
    brand_dir.mkdir(parents=True, exist_ok=True)

    multi = [c for c in clusters if len(c) >= 2]
    singles = [c for c in clusters if len(c) == 1]

    membership = []
    for ci, members in enumerate(multi):
        cdir = brand_dir / f"cluster_{ci:02d}_n{len(members)}"
        cdir.mkdir(parents=True, exist_ok=True)
        for path in members:
            link = cdir / path.name
            if not (link.exists() or link.is_symlink()):
                link.symlink_to(path.resolve())
            membership.append(
                {"file": path.name, "brand": brand, "cluster": f"cluster_{ci:02d}", "n": len(members)}
            )

    if singles:
        sdir = brand_dir / "singletons"
        sdir.mkdir(parents=True, exist_ok=True)
        for members in singles:
            path = members[0]
            link = sdir / path.name
            if not (link.exists() or link.is_symlink()):
                link.symlink_to(path.resolve())
            membership.append(
                {"file": path.name, "brand": brand, "cluster": "singleton", "n": 1}
            )

    # Near edges: entire brand is a near pool (different brands assumed dissimilar).
    # Visual subclusters are for human review only.
    all_files = [p.name for c in clusters for p in c]
    with (brand_dir / "near_edges.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file_a", "file_b", "brand", "reason"])
        for i in range(len(all_files)):
            for j in range(i + 1, len(all_files)):
                w.writerow([all_files[i], all_files[j], brand, f"same_brand_{mode}"])

    with (brand_dir / "membership.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "brand", "cluster", "n"])
        w.writeheader()
        w.writerows(membership)

    meta = {
        "brand": brand,
        "mode": mode,
        "n": sum(len(c) for c in clusters),
        "n_multi_clusters": len(multi),
        "n_in_multi": sum(len(c) for c in multi),
        "n_singletons": len(singles),
        "cluster_sizes": [len(c) for c in multi],
    }
    with (brand_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


def process_folder(folder: Path, *, tag: str = "by_brand") -> dict:
    buckets = assign_brands(folder)
    out_root = OUT_ROOT / folder.name / tag
    if out_root.exists():
        trash = _REPO_ROOT / ".trash" / "brand_clusters" / f"{folder.name}_{tag}"
        trash.parent.mkdir(parents=True, exist_ok=True)
        if trash.exists():
            trash = trash.with_name(f"{trash.name}_{out_root.stat().st_mtime_ns}")
        shutil.move(str(out_root), str(trash))
    out_root.mkdir(parents=True, exist_ok=True)

    brand_summaries = []
    all_edges = []

    for brand, paths in sorted(buckets.items(), key=lambda x: -len(x[1])):
        n = len(paths)
        logger.info("brand=%s n=%s", brand, n)
        if n <= 5:
            clusters = [paths]  # one flat near group
            mode = "brand_flat"
        elif n <= 20:
            clusters = _cluster_paths_simple(paths, divisor=5)
            mode = "simple"
        else:
            clusters, _pipe_meta = _cluster_paths_pipeline(paths)
            mode = "pipeline"

        meta = _write_brand_layout(out_root, brand, clusters, mode=mode)
        brand_summaries.append(meta)

        edges_path = out_root / f"brand_{brand}" / "near_edges.csv"
        if edges_path.is_file():
            with edges_path.open(encoding="utf-8") as f:
                r = csv.DictReader(f)
                for row in r:
                    all_edges.append(row)

    # combined near edges for training
    with (out_root / "near_edges_all.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file_a", "file_b", "brand", "reason"])
        w.writeheader()
        w.writerows(all_edges)

    index = {
        "folder": folder.name,
        "tag": tag,
        "brands": brand_summaries,
        "n_brands": len(brand_summaries),
        "n_edges": len(all_edges),
        "out": str(out_root),
    }
    with (out_root / "index.json").open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # human-readable brand sizes
    with (out_root / "brands.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "brand",
                "mode",
                "n",
                "n_multi_clusters",
                "n_in_multi",
                "n_singletons",
            ],
        )
        w.writeheader()
        for m in brand_summaries:
            w.writerow({k: m[k] for k in w.fieldnames})

    logger.info(
        "done %s brands=%s edges=%s → %s",
        folder.name,
        len(brand_summaries),
        len(all_edges),
        out_root,
    )
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--folder",
        default=None,
        help="Single by_manufact folder name (default: batch via --min-count)",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=31,
        help="Batch: process folders with n >= this (default 31 = above 30)",
    )
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        help="Folder name substring to skip (repeatable). Default skips Kuban.",
    )
    parser.add_argument("--tag", default="by_brand")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    skips = list(args.skip)
    if not skips:
        skips = ["096_Кубань-Вино"]

    def should_skip(name: str) -> bool:
        return any(s in name for s in skips)

    if args.folder:
        folder = BY_MANUFACT / args.folder
        if not folder.is_dir():
            logger.error("missing %s", folder)
            return 1
        if should_skip(folder.name):
            logger.warning("skip %s", folder.name)
            return 0
        index = process_folder(folder, tag=args.tag)
        print(json.dumps(index, ensure_ascii=False, indent=2))
        return 0

    targets = []
    for path in sorted(BY_MANUFACT.iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        if should_skip(path.name):
            logger.info("skip %s", path.name)
            continue
        n = len(_list_images(path))
        if n >= args.min_count:
            targets.append((n, path))

    targets.sort(key=lambda x: -x[0])
    logger.info("batch targets: %s", len(targets))
    rows = []
    for n, folder in targets:
        logger.info("==== %s n=%s ====", folder.name, n)
        idx = process_folder(folder, tag=args.tag)
        rows.append(
            {
                "folder": folder.name,
                "n": n,
                "n_brands": idx["n_brands"],
                "brands": ",".join(
                    f"{b['brand']}:{b['n']}/{b['mode']}" for b in idx["brands"]
                ),
                "n_edges": idx["n_edges"],
            }
        )
    out_csv = OUT_ROOT / f"brand_batch_gt{args.min_count}.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["folder", "n", "n_brands", "brands", "n_edges"]
        )
        w.writeheader()
        w.writerows(rows)
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    logger.info("batch csv → %s", out_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
