#!/usr/bin/env python3
"""Flag near_clusters folders whose internal min pairwise cosine is below a threshold.

Uses Phase1 (or any) DINO ONNX. Skips singleton folders.

Example::

    uv run python scripts/audit_near_cluster_cosine.py \\
      --onnx bin/dinov2_wine_phase1.onnx \\
      --threshold 0.8
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))
from compare_dino_onnx import OnnxEmbedder, _list_images  # noqa: E402

_SING_NAMES = {"singletons", "singletones", "singleton", "__singletons"}
_SKIP_WINERY = {"_meta", "_staging", ".trash"}


def _is_singleton_dir(name: str) -> bool:
    n = name.lower()
    return n in _SING_NAMES or n.endswith("__singletons")


def _pairwise_min(embs: np.ndarray) -> tuple[float, int, int]:
    """Return (min_cosine, i, j) for i < j."""
    sims = embs @ embs.T
    n = embs.shape[0]
    best = 1.0
    bi = bj = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = float(sims[i, j])
            if s < best:
                best = s
                bi, bj = i, j
    return best, bi, bj


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--onnx", type=Path, default=_REPO / "bin" / "dinov2_wine_phase1.onnx")
    p.add_argument(
        "--near-root",
        type=Path,
        default=_REPO / "data" / "train_dataset" / "near_clusters",
    )
    p.add_argument("--threshold", type=float, default=0.8)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument(
        "--out",
        type=Path,
        default=_REPO / "agent_docs" / "reports" / "near_cluster_cosine_audit.md",
    )
    p.add_argument(
        "--out-csv",
        type=Path,
        default=_REPO / "agent_docs" / "reports" / "near_cluster_cosine_audit.csv",
    )
    p.add_argument(
        "--only-paths",
        type=Path,
        default=None,
        help="Text/CSV/MD file: one relative cluster path per line (or `| `path` |` from priority md)",
    )
    p.add_argument("--limit", type=int, default=0, help="With --only-paths: first N paths (0=all)")
    args = p.parse_args(argv)

    if not args.onnx.is_file():
        print(f"missing onnx: {args.onnx}", file=sys.stderr)
        return 1
    if not args.near_root.is_dir():
        print(f"missing near root: {args.near_root}", file=sys.stderr)
        return 1

    enc = OnnxEmbedder(args.onnx, batch=args.batch)
    flagged: list[dict] = []
    ok_rows: list[dict] = []
    skipped_small = 0
    missing = 0
    scanned = 0

    def _audit_cluster(cluster: Path) -> None:
        nonlocal skipped_small, scanned
        if _is_singleton_dir(cluster.name):
            return
        imgs = sorted(
            p
            for p in cluster.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        )
        if len(imgs) < 2:
            skipped_small += 1
            print(f"SKIP (<2 imgs) {cluster.relative_to(args.near_root)}")
            return
        scanned += 1
        embs = enc.encode(imgs)
        mn, i, j = _pairwise_min(embs)
        row = {
            "winery": cluster.parent.name,
            "cluster": cluster.name,
            "n": len(imgs),
            "min_cosine": round(mn, 4),
            "file_a": imgs[i].name,
            "file_b": imgs[j].name,
            "path": str(cluster.relative_to(args.near_root)),
        }
        if mn < args.threshold:
            flagged.append(row)
            print(
                f"FLAG {row['path']} n={row['n']} min={mn:.3f} "
                f"({row['file_a']} ↔ {row['file_b']})"
            )
        else:
            ok_rows.append(row)
            print(f"OK   {row['path']} n={row['n']} min={mn:.3f}")

    if args.only_paths:
        text = args.only_paths.read_text(encoding="utf-8")
        paths: list[str] = []
        for line in text.splitlines():
            raw = line.strip()
            if not raw.startswith("|"):
                continue
            # markdown table: | min | n | `path` | …
            cells = [c.strip() for c in raw.strip("|").split("|")]
            if len(cells) < 3:
                continue
            # skip header / separator (----), not negative floats like -0.14
            if cells[0].lower() in {"min", "min cos", "min cosine"}:
                continue
            if set(cells[0]) <= set("-: "):
                continue
            try:
                float(cells[0])
            except ValueError:
                continue
            cell_path = cells[2]
            if not (cell_path.startswith("`") and cell_path.endswith("`")):
                continue
            rel = cell_path.strip("`")
            if "/" not in rel:
                continue
            paths.append(rel)
        # dedupe preserve order
        seen: set[str] = set()
        uniq: list[str] = []
        for pth in paths:
            if pth not in seen:
                seen.add(pth)
                uniq.append(pth)
        if args.limit > 0:
            uniq = uniq[: args.limit]
        print(f"recheck {len(uniq)} paths from {args.only_paths}")
        for i, rel in enumerate(uniq, 1):
            print(f"--- {i}/{len(uniq)} ---")
            cluster = args.near_root / rel
            if not cluster.is_dir():
                missing += 1
                print(f"MISSING {rel}")
                continue
            _audit_cluster(cluster)
    else:
        wineries = sorted(
            d
            for d in args.near_root.iterdir()
            if d.is_dir() and d.name not in _SKIP_WINERY and not d.name.startswith(".")
        )

        for wi, winery in enumerate(wineries, 1):
            subdirs = sorted(d for d in winery.iterdir() if d.is_dir())
            for cluster in subdirs:
                _audit_cluster(cluster)
            if wi % 10 == 0 or wi == len(wineries):
                print(f"... wineries {wi}/{len(wineries)} flagged_so_far={len(flagged)}")

    flagged.sort(key=lambda r: r["min_cosine"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)

    fields = ["min_cosine", "n", "winery", "cluster", "file_a", "file_b", "path"]
    with args.out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(flagged)

    lines = [
        f"# Near-cluster cosine audit (Phase1 ONNX)",
        "",
        f"- onnx: `{args.onnx}`",
        f"- root: `{args.near_root}`",
        f"- threshold: **{args.threshold}** (flag if any pair &lt; threshold)",
        f"- clusters scanned (≥2 imgs, excl. singletons): **{scanned}**",
        f"- ok (≥ threshold): **{len(ok_rows)}**",
        f"- skipped (&lt;2 imgs): {skipped_small}",
        f"- missing paths: {missing}",
        f"- **flagged: {len(flagged)}**",
        "",
        "## Flagged (weakest pair first)",
        "",
        "| min cos | n | path | pair |",
        "|--------:|--:|------|------|",
    ]
    for r in flagged:
        lines.append(
            f"| {r['min_cosine']:.3f} | {r['n']} | `{r['path']}` | "
            f"`{r['file_a']}` ↔ `{r['file_b']}` |"
        )
    if not flagged:
        lines.append("| — | — | none | — |")
    if ok_rows:
        lines.extend(
            [
                "",
                "## OK (min ≥ threshold)",
                "",
                "| min cos | n | path |",
                "|--------:|--:|------|",
            ]
        )
        for r in sorted(ok_rows, key=lambda x: -x["min_cosine"]):
            lines.append(f"| {r['min_cosine']:.3f} | {r['n']} | `{r['path']}` |")
    lines.append("")
    args.out.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "onnx": str(args.onnx),
        "threshold": args.threshold,
        "scanned": scanned,
        "ok": len(ok_rows),
        "flagged": len(flagged),
        "missing": missing,
        "flagged_paths": [r["path"] for r in flagged],
        "ok_paths": [r["path"] for r in ok_rows],
    }
    json_out = args.out.with_suffix(".json")
    json_out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(
        f"DONE scanned={scanned} ok={len(ok_rows)} flagged={len(flagged)} "
        f"missing={missing} → {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
