#!/usr/bin/env python3
"""Cluster visually-near labels inside by_manufact folders (trained DINO ONNX).

Does NOT use manufacturer alone as "near". Within one winery folder, builds
connected components where cosine(a,b) >= threshold. Those multi-member
clusters are candidates to exclude from hard-FAR negatives.

Examples:
  # rename by_manufact dirs to NN_Name
  uv run python scripts/cluster_manufact_near.py --rename-only

  # simple k-means for mid-size wineries (10..20), k=n//5 → subfolders 1,2,..
  uv run python scripts/cluster_manufact_near.py --skip-rename --simple

  # cluster largest folder (Фанагория) at threshold 0.85
  uv run python scripts/cluster_manufact_near.py \\
      --skip-rename --folder 100_Фанагория --threshold 0.85
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

logger = logging.getLogger("cluster_manufact_near")

BY_MANUFACT = _REPO_ROOT / "data" / "train_dataset" / "by_manufact"
OUT_ROOT = _REPO_ROOT / "data" / "train_dataset" / "near_clusters"
INDEX_CSV = _REPO_ROOT / "data" / "train_dataset" / "by_manufact_index.csv"

_COUNT_PREFIX = re.compile(r"^\d{2,4}_")
_IMG_EXT = {".webp", ".jpg", ".jpeg", ".png"}


def _list_images(folder: Path) -> list[Path]:
    return sorted(
        p
        for p in folder.iterdir()
        if p.is_file() or p.is_symlink()
        if p.suffix.lower() in _IMG_EXT
    )


def rename_by_manufact_with_counts(*, root: Path = BY_MANUFACT) -> list[dict]:
    """Rename ``Name`` or ``NN_Name`` → ``{count:03d}_{Name}`` safely."""
    if not root.is_dir():
        raise FileNotFoundError(root)

    dirs = [p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")]
    plan: list[tuple[Path, str, int]] = []
    for path in dirs:
        base = _COUNT_PREFIX.sub("", path.name)
        n = len(_list_images(path))
        plan.append((path, base, n))

    # Phase 1: move all to unique temp
    trash_parent = root / ".__rename_tmp__"
    if trash_parent.exists():
        raise RuntimeError(f"Remove leftover {trash_parent} first")
    trash_parent.mkdir()

    staged: list[tuple[Path, str, int]] = []
    for i, (path, base, n) in enumerate(plan):
        tmp = trash_parent / f"{i:04d}__{base}"
        path.rename(tmp)
        staged.append((tmp, base, n))

    # Phase 2: move to final count-prefixed names
    used: set[str] = set()
    results: list[dict] = []
    for tmp, base, n in sorted(staged, key=lambda x: (-x[2], x[1])):
        name = f"{n:03d}_{base}"
        if name in used:
            k = 2
            while f"{n:03d}_{base}_{k}" in used:
                k += 1
            name = f"{n:03d}_{base}_{k}"
        used.add(name)
        final = root / name
        tmp.rename(final)
        results.append({"winery": base, "n_crops": n, "dir": name})

    trash_parent.rmdir()

    results.sort(key=lambda r: (-r["n_crops"], r["winery"]))
    with INDEX_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["winery", "n_crops", "dir"])
        w.writeheader()
        w.writerows(results)

    logger.info("renamed %s folders with count prefix", len(results))
    return results


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            self.parent[ra] = rb
        elif self.rank[ra] > self.rank[rb]:
            self.parent[rb] = ra
        else:
            self.parent[rb] = ra
            self.rank[ra] += 1


def _encode_folder(paths: list[Path]) -> np.ndarray:
    from core.config import load_app_settings, load_database_settings
    from core.retrieve.dino_encoder import create_dino_encoder

    database = load_database_settings()
    compute = load_app_settings().compute
    encoder = create_dino_encoder(database, compute)
    vectors: list[np.ndarray] = []
    for i, path in enumerate(paths):
        # resolve symlink to real crop
        real = path.resolve()
        emb = encoder.encode_image(str(real))
        vectors.append(np.asarray(emb, dtype=np.float32))
        if (i + 1) % 25 == 0 or i + 1 == len(paths):
            logger.info("encoded %s / %s (%s)", i + 1, len(paths), path.name)
    mat = np.stack(vectors, axis=0)
    # ensure L2
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.clip(norms, 1e-12, None)
    return mat / norms


def _sim_clusters(
    emb: np.ndarray,
    a: list[int],
    b: list[int],
    *,
    metric: str = "max_member",
) -> float:
    if metric == "centroid":
        return float(np.dot(_centroid(emb, a), _centroid(emb, b)))
    return float((emb[a] @ emb[b].T).max())


def _cc_on_indices(
    emb: np.ndarray,
    idxs: list[int],
    threshold: float,
) -> tuple[list[list[int]], int]:
    """Connected components on a subset of embedding rows. Returns clusters of global idxs."""
    if len(idxs) < 2:
        return [[i] for i in idxs], 0
    uf = _UnionFind(len(idxs))
    links = 0
    for a in range(len(idxs)):
        for b in range(a + 1, len(idxs)):
            if float(np.dot(emb[idxs[a]], emb[idxs[b]])) >= threshold:
                uf.union(a, b)
                links += 1
    groups: dict[int, list[int]] = defaultdict(list)
    for local_i, global_i in enumerate(idxs):
        groups[uf.find(local_i)].append(global_i)
    return list(groups.values()), links


def pipeline_three_pass(
    clusters: list[list[int]],
    emb: np.ndarray,
    *,
    soft_threshold: float = 0.60,
    small_max: int = 3,
    metric: str = "max_member",
) -> tuple[list[list[int]], list[dict]]:
    """Clean 3-step refine after hard CC:

    1) (assumed done) hard clusters already in ``clusters``
    2) singletons: CC at soft_threshold, then attach leftovers to nearest multi
    3) merge small clusters (size 2..small_max) into nearest cluster if sim >= soft
    """
    events: list[dict] = []
    multis = [list(c) for c in clusters if len(c) >= 2]
    singles = [c[0] for c in clusters if len(c) == 1]

    # --- step 2a: CC among singletons at soft threshold ---
    if len(singles) >= 2:
        parts, links = _cc_on_indices(emb, singles, soft_threshold)
        new_multi = [p for p in parts if len(p) >= 2]
        still = [p[0] for p in parts if len(p) == 1]
        events.append(
            {
                "action": "step2_singleton_cc",
                "threshold": soft_threshold,
                "links": links,
                "new_multi": len(new_multi),
                "sizes": sorted((len(p) for p in new_multi), reverse=True),
                "still_singles": len(still),
            }
        )
        multis.extend(new_multi)
        singles = still
    else:
        events.append({"action": "step2_singleton_cc", "skipped": True})

    # --- step 2b: attach remaining singletons to nearest multi ---
    leftover: list[int] = []
    for idx in singles:
        if not multis:
            leftover.append(idx)
            continue
        best_i, best_s = -1, -1.0
        for i, m in enumerate(multis):
            s = _sim_clusters(emb, [idx], m, metric=metric)
            if s > best_s:
                best_s, best_i = s, i
        if best_i >= 0 and best_s >= soft_threshold:
            multis[best_i].append(idx)
            events.append(
                {
                    "action": "step2_singleton_attach",
                    "file_idx": idx,
                    "into": best_i,
                    "sim": round(best_s, 6),
                }
            )
        else:
            leftover.append(idx)
            events.append(
                {
                    "action": "step2_singleton_kept",
                    "file_idx": idx,
                    "best_sim": round(best_s, 6) if best_i >= 0 else None,
                }
            )

    # --- step 3: merge small clusters (2..small_max) greedily ---
    # Repeat until no merge
    merged_any = True
    round_i = 0
    while merged_any:
        merged_any = False
        round_i += 1
        # refresh small vs rest
        order = sorted(range(len(multis)), key=lambda i: len(multis[i]))
        used = set()
        new_multis: list[list[int]] = []
        for i in order:
            if i in used:
                continue
            cur = list(multis[i])
            if len(cur) > small_max or len(cur) < 2:
                # large or will handle; keep for now if not absorbed
                continue
            # find best partner among all other multis
            best_j, best_s = -1, -1.0
            for j, other in enumerate(multis):
                if j == i or j in used:
                    continue
                s = _sim_clusters(emb, cur, other, metric=metric)
                if s > best_s:
                    best_s, best_j = s, j
            if best_j >= 0 and best_s >= soft_threshold:
                # merge into partner (keep partner slot)
                if best_j in used:
                    # partner already merged away — skip
                    new_multis.append(cur)
                    used.add(i)
                    continue
                partner = list(multis[best_j])
                combined = partner + cur
                used.add(i)
                used.add(best_j)
                new_multis.append(combined)
                merged_any = True
                events.append(
                    {
                        "action": "step3_merge_small",
                        "round": round_i,
                        "small_n": len(cur),
                        "partner_n": len(partner),
                        "result_n": len(combined),
                        "sim": round(best_s, 6),
                    }
                )
            else:
                used.add(i)
                new_multis.append(cur)
                events.append(
                    {
                        "action": "step3_small_kept",
                        "round": round_i,
                        "small_n": len(cur),
                        "best_sim": round(best_s, 6) if best_j >= 0 else None,
                    }
                )
        # add untouched (large clusters not in used as small)
        for j, m in enumerate(multis):
            if j not in used:
                new_multis.append(list(m))
        multis = new_multis
        if round_i >= 10:
            break

    final = [c for c in multis if c]
    final.extend([[i] for i in leftover])
    final = sorted(final, key=lambda c: (-len(c), c[0]))
    events.append(
        {
            "action": "pipeline_done",
            "n_multi": sum(1 for c in final if len(c) >= 2),
            "n_in_multi": sum(len(c) for c in final if len(c) >= 2),
            "n_singletons": sum(1 for c in final if len(c) == 1),
        }
    )
    return final, events


def _centroid(emb: np.ndarray, idxs: list[int]) -> np.ndarray:
    c = emb[idxs].mean(axis=0)
    n = float(np.linalg.norm(c))
    if n < 1e-12:
        return c
    return c / n


def _absorb_pass(
    clusters: list[list[int]],
    emb: np.ndarray,
    *,
    threshold: float,
    absorb_threshold: float,
    core_min: int,
    absorb_singletons: bool,
    second_pass_threshold: float | None,
    metric: str = "max_member",
    singleton_low_threshold: float | None = 0.55,
) -> tuple[list[list[int]], list[dict]]:
    """Grow near-groups without forcing unrelated lines into big cores.

    1) cores = size >= core_min (from first CC at ``threshold``)
    2) small multis stay unless close to a core (>= absorb_threshold)
    3) second CC among singletons at second_pass_threshold
    4) remaining singletons → nearest multi if sim >= absorb_threshold
    5) leftover singletons: low-threshold CC (singleton_low_threshold)
       — over-merge OK; human splits weak groups later
    """
    events: list[dict] = []
    cores = [list(c) for c in clusters if len(c) >= core_min]
    smalls = [list(c) for c in clusters if 2 <= len(c) < core_min]
    singles = [[i] for c in clusters if len(c) == 1 for i in c]

    def sim_to_cluster(idxs: list[int], cluster: list[int]) -> float:
        if metric == "centroid":
            return float(np.dot(_centroid(emb, idxs), _centroid(emb, cluster)))
        # max pairwise to any member
        block = emb[idxs] @ emb[cluster].T
        return float(block.max())

    # --- small → core only if really close ---
    kept_small: list[list[int]] = []
    for small in sorted(smalls, key=lambda c: -len(c)):
        if not cores:
            kept_small.append(small)
            continue
        best_i, best_s = -1, -1.0
        for i, core in enumerate(cores):
            s = sim_to_cluster(small, core)
            if s > best_s:
                best_s, best_i = s, i
        if best_i >= 0 and best_s >= absorb_threshold:
            cores[best_i].extend(small)
            events.append(
                {
                    "action": "small_to_core",
                    "moved_n": len(small),
                    "into_core": best_i,
                    "sim": round(best_s, 6),
                    "metric": metric,
                }
            )
        else:
            kept_small.append(small)
            events.append(
                {
                    "action": "small_kept_as_line",
                    "moved_n": len(small),
                    "best_sim": round(best_s, 6) if best_i >= 0 else None,
                }
            )

    # Active multis = cores + kept small lines
    multis = cores + kept_small

    # --- second pass: CC among singletons (+ optional orphans) ---
    leftover_singles = list(singles)
    if second_pass_threshold is not None and leftover_singles:
        idxs = [s[0] for s in leftover_singles]
        uf = _UnionFind(len(idxs))
        n_links = 0
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                s = float(np.dot(emb[idxs[a]], emb[idxs[b]]))
                if s >= second_pass_threshold:
                    uf.union(a, b)
                    n_links += 1
        groups: dict[int, list[int]] = defaultdict(list)
        for local_i, global_i in enumerate(idxs):
            groups[uf.find(local_i)].append(global_i)
        new_multi = []
        new_singles = []
        for members in groups.values():
            if len(members) >= 2:
                new_multi.append(members)
            else:
                new_singles.append(members)
        events.append(
            {
                "action": "second_pass_cc",
                "threshold": second_pass_threshold,
                "links": n_links,
                "new_multi": len(new_multi),
                "still_singles": len(new_singles),
            }
        )
        multis.extend(new_multi)
        leftover_singles = new_singles

    # --- singletons → nearest multi ---
    still_singles: list[list[int]] = []
    if absorb_singletons and multis:
        for single in leftover_singles:
            best_i, best_s = -1, -1.0
            for i, m in enumerate(multis):
                s = sim_to_cluster(single, m)
                if s > best_s:
                    best_s, best_i = s, i
            if best_i >= 0 and best_s >= absorb_threshold:
                multis[best_i].extend(single)
                events.append(
                    {
                        "action": "singleton_to_cluster",
                        "file_idx": single[0],
                        "into": best_i,
                        "sim": round(best_s, 6),
                        "metric": metric,
                    }
                )
            else:
                still_singles.append(single)
                events.append(
                    {
                        "action": "singleton_kept",
                        "file_idx": single[0],
                        "best_sim": round(best_s, 6) if best_i >= 0 else None,
                    }
                )
    else:
        still_singles = leftover_singles

    # --- low-threshold CC among leftover singletons (easy to split later) ---
    if (
        singleton_low_threshold is not None
        and still_singles
        and len(still_singles) >= 2
    ):
        idxs = [s[0] for s in still_singles]
        uf = _UnionFind(len(idxs))
        n_links = 0
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                s = float(np.dot(emb[idxs[a]], emb[idxs[b]]))
                if s >= singleton_low_threshold:
                    uf.union(a, b)
                    n_links += 1
        groups_low: dict[int, list[int]] = defaultdict(list)
        for local_i, global_i in enumerate(idxs):
            groups_low[uf.find(local_i)].append(global_i)
        low_multi = []
        low_sing = []
        for members in groups_low.values():
            if len(members) >= 2:
                low_multi.append(members)
            else:
                low_sing.append(members)
        events.append(
            {
                "action": "singleton_low_cc",
                "threshold": singleton_low_threshold,
                "links": n_links,
                "new_multi": len(low_multi),
                "in_multi": sum(len(m) for m in low_multi),
                "still_singles": len(low_sing),
                "sizes": sorted((len(m) for m in low_multi), reverse=True),
            }
        )
        multis.extend(low_multi)
        still_singles = low_sing

    final = [c for c in multis if c]
    final.extend(still_singles)
    final = sorted(final, key=lambda c: (-len(c), c[0]))
    return final, events


def _write_cluster_output(
    *,
    out_dir: Path,
    paths: list[Path],
    clusters: list[list[int]],
    emb: np.ndarray,
    threshold: float,
    pairs: list[tuple[str, str, float]],
    events: list[dict] | None,
    extra_summary: dict | None,
) -> dict:
    if out_dir.exists():
        trash = _REPO_ROOT / ".trash" / "near_clusters" / out_dir.name
        trash.parent.mkdir(parents=True, exist_ok=True)
        dest = trash.parent / f"{out_dir.parent.name}_{out_dir.name}"
        if dest.exists():
            dest = dest.with_name(f"{dest.name}_{out_dir.stat().st_mtime_ns}")
        shutil.move(str(out_dir), str(dest))
    out_dir.mkdir(parents=True, exist_ok=True)

    multi = [c for c in clusters if len(c) >= 2]
    singles = [c for c in clusters if len(c) == 1]

    membership_rows: list[dict] = []
    for ci, members in enumerate(multi):
        cdir = out_dir / f"cluster_{ci:02d}_n{len(members)}"
        cdir.mkdir(parents=True, exist_ok=True)
        for idx in members:
            src = paths[idx].resolve()
            link = cdir / paths[idx].name
            if link.exists() or link.is_symlink():
                trash_link = _REPO_ROOT / ".trash" / "near_cluster_links" / link.name
                trash_link.parent.mkdir(parents=True, exist_ok=True)
                if trash_link.exists() or trash_link.is_symlink():
                    trash_link = trash_link.with_name(
                        f"{link.stem}_{link.stat().st_mtime_ns}{link.suffix}"
                    )
                shutil.move(str(link), str(trash_link))
            link.symlink_to(src)
            membership_rows.append(
                {
                    "file": paths[idx].name,
                    "cluster_id": f"cluster_{ci:02d}",
                    "cluster_size": len(members),
                    "singleton": 0,
                }
            )

    singles_dir = out_dir / "singletons"
    singles_dir.mkdir(parents=True, exist_ok=True)
    for members in singles:
        idx = members[0]
        src = paths[idx].resolve()
        link = singles_dir / paths[idx].name
        if not (link.exists() or link.is_symlink()):
            link.symlink_to(src)
        membership_rows.append(
            {
                "file": paths[idx].name,
                "cluster_id": "singleton",
                "cluster_size": 1,
                "singleton": 1,
            }
        )

    pairs_sorted = sorted(pairs, key=lambda x: -x[2])
    with (out_dir / "pairs_above_threshold.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        w = csv.writer(f)
        w.writerow(["file_a", "file_b", "cosine"])
        w.writerows(pairs_sorted)

    with (out_dir / "membership.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["file", "cluster_id", "cluster_size", "singleton"]
        )
        w.writeheader()
        w.writerows(membership_rows)

    # Near edges: all pairs within each multi cluster (for hard-neg exclusion)
    with (out_dir / "near_edges.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file_a", "file_b", "cosine", "reason"])
        for members in multi:
            for a in range(len(members)):
                for b in range(a + 1, len(members)):
                    i, j = members[a], members[b]
                    s = float(np.dot(emb[i], emb[j]))
                    w.writerow(
                        [
                            paths[i].name,
                            paths[j].name,
                            f"{s:.6f}",
                            "same_cluster",
                        ]
                    )

    if events is not None:
        with (out_dir / "absorb_events.json").open("w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)

    summary = {
        "n_images": len(paths),
        "threshold": threshold,
        "n_multi_clusters": len(multi),
        "n_in_multi": sum(len(c) for c in multi),
        "n_singletons": len(singles),
        "n_pairs_edge_seed": len(pairs),
        "largest_cluster": max((len(c) for c in multi), default=0),
        "out_dir": str(out_dir),
    }
    if extra_summary:
        summary.update(extra_summary)
    with (out_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary


def cluster_folder(
    folder: Path,
    *,
    threshold: float,
    out_root: Path = OUT_ROOT,
    tag: str | None = None,
    absorb: bool = False,
    pipeline: bool = False,
    soft_threshold: float = 0.60,
    small_max: int = 3,
    core_min: int = 3,
    absorb_singletons: bool = True,
    absorb_threshold: float | None = None,
    second_pass_threshold: float | None = 0.75,
    absorb_metric: str = "max_member",
    singleton_low_threshold: float | None = 0.55,
) -> dict:
    """Hard CC at ``threshold``, optional refine (``pipeline`` or legacy ``absorb``)."""
    paths = _list_images(folder)
    if len(paths) < 2:
        logger.warning("%s has <2 images, skip", folder)
        return {"folder": folder.name, "n": len(paths), "skipped": True}

    abs_thr = threshold if absorb_threshold is None else absorb_threshold
    mode = "cc"
    if pipeline:
        mode = "pipeline"
    elif absorb:
        mode = "absorb"

    logger.info(
        "clustering %s n=%s hard=%.3f mode=%s soft=%.3f",
        folder.name,
        len(paths),
        threshold,
        mode,
        soft_threshold if pipeline else abs_thr,
    )
    emb = _encode_folder(paths)
    sims = emb @ emb.T
    np.fill_diagonal(sims, 0.0)

    uf = _UnionFind(len(paths))
    pairs: list[tuple[str, str, float]] = []
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            s = float(sims[i, j])
            if s >= threshold:
                uf.union(i, j)
                pairs.append((paths[i].name, paths[j].name, s))

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(paths)):
        groups[uf.find(i)].append(i)
    cluster_list = sorted(groups.values(), key=lambda idxs: (-len(idxs), idxs[0]))

    base_multi = sum(1 for c in cluster_list if len(c) >= 2)
    base_in_multi = sum(len(c) for c in cluster_list if len(c) >= 2)
    base_singles = sum(1 for c in cluster_list if len(c) == 1)

    events: list[dict] | None = None
    if pipeline:
        cluster_list, events = pipeline_three_pass(
            cluster_list,
            emb,
            soft_threshold=soft_threshold,
            small_max=small_max,
            metric=absorb_metric,
        )
        done = next(e for e in events if e["action"] == "pipeline_done")
        logger.info(
            "pipeline: multi=%s in_multi=%s singletons=%s",
            done["n_multi"],
            done["n_in_multi"],
            done["n_singletons"],
        )
    elif absorb:
        cluster_list, events = _absorb_pass(
            cluster_list,
            emb,
            threshold=threshold,
            absorb_threshold=abs_thr,
            core_min=core_min,
            absorb_singletons=absorb_singletons,
            second_pass_threshold=second_pass_threshold,
            metric=absorb_metric,
            singleton_low_threshold=singleton_low_threshold,
        )

    if tag is None:
        tag = f"t{threshold:.2f}".replace(".", "p")
        if pipeline:
            tag = f"{tag}_pipe_s{soft_threshold:.2f}".replace(".", "p")
        elif absorb:
            tag = (
                f"{tag}_absorb_a{abs_thr:.2f}".replace(".", "p")
                + (
                    f"_s{second_pass_threshold:.2f}".replace(".", "p")
                    if second_pass_threshold is not None
                    else ""
                )
            )

    out_dir = out_root / folder.name / tag
    summary = _write_cluster_output(
        out_dir=out_dir,
        paths=paths,
        clusters=cluster_list,
        emb=emb,
        threshold=threshold,
        pairs=pairs,
        events=events,
        extra_summary={
            "folder": folder.name,
            "mode": mode,
            "soft_threshold": soft_threshold if pipeline else None,
            "small_max": small_max if pipeline else None,
            "core_min": core_min if absorb else None,
            "absorb_threshold": abs_thr if absorb else None,
            "second_pass_threshold": second_pass_threshold if absorb else None,
            "absorb_metric": absorb_metric if (absorb or pipeline) else None,
            "singleton_low_threshold": singleton_low_threshold if absorb else None,
            "before_refine": {
                "n_multi_clusters": base_multi,
                "n_in_multi": base_in_multi,
                "n_singletons": base_singles,
            },
        },
    )

    logger.info(
        "done %s: multi_clusters=%s in_multi=%s singletons=%s → %s",
        folder.name,
        summary["n_multi_clusters"],
        summary["n_in_multi"],
        summary["n_singletons"],
        out_dir,
    )
    return summary


def _spherical_kmeans(
    emb: np.ndarray,
    k: int,
    *,
    n_iter: int = 40,
    seed: int = 42,
) -> np.ndarray:
    """Return label array shape (n,) with values 0..k-1. ``emb`` must be L2-normalized."""
    n = emb.shape[0]
    if k < 1:
        raise ValueError("k must be >= 1")
    if k >= n:
        return np.arange(n, dtype=np.int32)

    rng = np.random.default_rng(seed)
    # farthest-point-ish init: random first, then max min-distance
    centers_idx = [int(rng.integers(0, n))]
    while len(centers_idx) < k:
        # cosine distance = 1 - dot; pick farthest from nearest center
        sims = emb @ emb[centers_idx].T
        nearest = sims.max(axis=1)
        # avoid already chosen
        nearest[centers_idx] = 2.0
        centers_idx.append(int(np.argmin(nearest)))
    centers = emb[centers_idx].copy()

    labels = np.zeros(n, dtype=np.int32)
    for _ in range(n_iter):
        sims = emb @ centers.T
        new_labels = sims.argmax(axis=1).astype(np.int32)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for c in range(k):
            mask = labels == c
            if not np.any(mask):
                # re-seed empty cluster
                centers[c] = emb[int(rng.integers(0, n))]
                continue
            mean = emb[mask].mean(axis=0)
            norm = float(np.linalg.norm(mean))
            centers[c] = mean / norm if norm > 1e-12 else emb[int(rng.integers(0, n))]
    return labels


def simple_cluster_folder(
    folder: Path,
    *,
    divisor: int = 5,
    into_by_manufact: bool = True,
    seed: int = 42,
) -> dict:
    """Simple spherical k-means; k = n // divisor. Writes subfolders ``1``, ``2``, …

    Layout matches manual review: ``by_manufact/<winery>/1/``, ``2/``, …
    Also mirrors under ``near_clusters/<winery>/simple_k{K}/``.
    """
    paths = _list_images(folder)
    n = len(paths)
    k = max(1, n // divisor)
    if n < 2:
        logger.warning("%s: n=%s skip simple", folder.name, n)
        return {"folder": folder.name, "n": n, "skipped": True}

    # Skip if already has numeric cluster subdirs with content
    existing = [
        p
        for p in folder.iterdir()
        if p.is_dir() and p.name.isdigit() and any(p.iterdir())
    ]
    if existing and into_by_manufact:
        logger.warning(
            "%s: already has subfolders %s — skip (remove them to re-run)",
            folder.name,
            [p.name for p in existing],
        )
        return {"folder": folder.name, "n": n, "skipped": True, "reason": "exists"}

    logger.info("simple cluster %s n=%s k=n//%s=%s", folder.name, n, divisor, k)
    emb = _encode_folder(paths)
    labels = _spherical_kmeans(emb, k, seed=seed)

    # Mirror under near_clusters
    mirror = OUT_ROOT / folder.name / f"simple_k{k}"
    if mirror.exists():
        trash = _REPO_ROOT / ".trash" / "near_clusters" / f"{folder.name}_simple_k{k}"
        trash.parent.mkdir(parents=True, exist_ok=True)
        if trash.exists():
            trash = trash.with_name(f"{trash.name}_{mirror.stat().st_mtime_ns}")
        shutil.move(str(mirror), str(trash))
    mirror.mkdir(parents=True, exist_ok=True)

    membership: list[dict] = []
    sizes = [0] * k
    for i, path in enumerate(paths):
        cid = int(labels[i]) + 1  # 1-based folder names
        sizes[cid - 1] += 1
        dest_name = path.name
        real = path.resolve()

        # near_clusters mirror
        mdir = mirror / str(cid)
        mdir.mkdir(parents=True, exist_ok=True)
        mlink = mdir / dest_name
        if not (mlink.exists() or mlink.is_symlink()):
            mlink.symlink_to(real)

        if into_by_manufact:
            cdir = folder / str(cid)
            cdir.mkdir(parents=True, exist_ok=True)
            # move symlink/file from top-level into subfolder
            target = cdir / dest_name
            if path.parent.resolve() == folder.resolve():
                if target.exists() or target.is_symlink():
                    trash_l = _REPO_ROOT / ".trash" / "simple_cluster_links"
                    trash_l.mkdir(parents=True, exist_ok=True)
                    dest_t = trash_l / f"{folder.name}__{cid}__{dest_name}"
                    if dest_t.exists() or dest_t.is_symlink():
                        dest_t = trash_l / (
                            f"{folder.name}__{cid}__{path.stem}_"
                            f"{path.stat().st_mtime_ns}{path.suffix}"
                        )
                    shutil.move(str(target), str(dest_t))
                shutil.move(str(path), str(target))

        membership.append({"file": dest_name, "cluster": cid})

    summary = {
        "folder": folder.name,
        "n": n,
        "k": k,
        "divisor": divisor,
        "sizes": sizes,
        "into_by_manufact": into_by_manufact,
        "mirror": str(mirror),
    }
    with (mirror / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with (mirror / "membership.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "cluster"])
        w.writeheader()
        w.writerows(membership)
    if into_by_manufact:
        with (folder / "simple_clusters.json").open("w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

    logger.info("simple done %s sizes=%s → %s/{{1..%s}}", folder.name, sizes, folder, k)
    return summary


def run_simple_range(
    *,
    min_count: int = 10,
    max_count: int = 20,
    divisor: int = 5,
    into_by_manufact: bool = True,
) -> list[dict]:
    results = []
    for path in sorted(BY_MANUFACT.iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        n = len(_list_images(path))
        if min_count <= n <= max_count:
            results.append(
                simple_cluster_folder(
                    path,
                    divisor=divisor,
                    into_by_manufact=into_by_manufact,
                )
            )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rename-only", action="store_true")
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Spherical k-means; k=n//5; write subfolders 1,2,.. (for mid-size wineries)",
    )
    parser.add_argument(
        "--simple-min",
        type=int,
        default=10,
        help="With --simple: min top-level images (default 10)",
    )
    parser.add_argument(
        "--simple-max",
        type=int,
        default=20,
        help="With --simple: max top-level images (default 20)",
    )
    parser.add_argument(
        "--simple-divisor",
        type=int,
        default=5,
        help="k = n // divisor (default 5)",
    )
    parser.add_argument(
        "--simple-mirror-only",
        action="store_true",
        help="Only write near_clusters/.../simple_kK/; do not rearrange by_manufact",
    )
    parser.add_argument(
        "--folder",
        type=str,
        default=None,
        help="by_manufact subdir name (after rename), e.g. 098_Фанагория",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=15,
        help="Cluster all folders with >= this many images (if --folder not set)",
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="3-pass: hard CC → singleton soft → merge small(2..small_max) at soft thr",
    )
    parser.add_argument(
        "--soft-threshold",
        type=float,
        default=0.60,
        help="Soft cosine for pipeline steps 2–3 (default 0.60)",
    )
    parser.add_argument(
        "--small-max",
        type=int,
        default=3,
        help="Max size treated as 'small' for step-3 merge (default 3)",
    )
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument(
        "--absorb",
        action="store_true",
        help="Legacy absorb refine (prefer --pipeline)",
    )
    parser.add_argument(
        "--core-min",
        type=int,
        default=3,
        help="Min size for a stable core cluster (default 3)",
    )
    parser.add_argument(
        "--absorb-threshold",
        type=float,
        default=0.75,
        help="Sim threshold for small→core / singleton→multi (default 0.75)",
    )
    parser.add_argument(
        "--second-pass-threshold",
        type=float,
        default=0.75,
        help="CC among leftover singletons (default 0.75; <0 to disable)",
    )
    parser.add_argument(
        "--absorb-metric",
        choices=("max_member", "centroid"),
        default="max_member",
    )
    parser.add_argument(
        "--singleton-low-threshold",
        type=float,
        default=0.55,
        help="Final CC among leftover singletons (default 0.55; <0 to disable)",
    )
    parser.add_argument(
        "--no-absorb-singletons",
        action="store_true",
        help="Do not attach singletons to multis after second pass",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default=None,
        help="Output subdir name under near_clusters/<folder>/ (keeps previous runs)",
    )
    parser.add_argument(
        "--skip-rename",
        action="store_true",
        help="Do not rename folders before clustering",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not args.skip_rename or args.rename_only:
        rename_by_manufact_with_counts()
        if args.rename_only:
            return 0

    if args.simple:
        if args.folder:
            folder = BY_MANUFACT / args.folder
            if not folder.is_dir():
                matches = [
                    p
                    for p in BY_MANUFACT.iterdir()
                    if p.is_dir()
                    and (p.name == args.folder or p.name.endswith(args.folder))
                ]
                if not matches:
                    logger.error("folder not found: %s", args.folder)
                    return 1
                folder = matches[0]
            simple_cluster_folder(
                folder,
                divisor=args.simple_divisor,
                into_by_manufact=not args.simple_mirror_only,
            )
        else:
            run_simple_range(
                min_count=args.simple_min,
                max_count=args.simple_max,
                divisor=args.simple_divisor,
                into_by_manufact=not args.simple_mirror_only,
            )
        return 0

    second = args.second_pass_threshold
    if second is not None and second < 0:
        second = None
    low = args.singleton_low_threshold
    if low is not None and low < 0:
        low = None

    kwargs = {
        "threshold": args.threshold,
        "absorb": args.absorb,
        "pipeline": args.pipeline,
        "soft_threshold": args.soft_threshold,
        "small_max": args.small_max,
        "core_min": args.core_min,
        "absorb_singletons": not args.no_absorb_singletons,
        "absorb_threshold": args.absorb_threshold,
        "second_pass_threshold": second,
        "absorb_metric": args.absorb_metric,
        "singleton_low_threshold": low,
        "tag": args.tag,
    }

    if args.folder:
        folder = BY_MANUFACT / args.folder
        if not folder.is_dir():
            matches = [
                p
                for p in BY_MANUFACT.iterdir()
                if p.is_dir() and (p.name == args.folder or p.name.endswith(args.folder))
            ]
            if not matches:
                logger.error("folder not found: %s", args.folder)
                return 1
            folder = matches[0]
        cluster_folder(folder, **kwargs)
        return 0

    targets = []
    for path in sorted(BY_MANUFACT.iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        n = len(_list_images(path))
        if n >= args.min_count:
            targets.append(path)
    targets.sort(key=lambda p: -len(_list_images(p)))
    logger.info("clustering %s folders (min_count=%s)", len(targets), args.min_count)
    for folder in targets:
        cluster_folder(folder, **kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
