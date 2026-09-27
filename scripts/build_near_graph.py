#!/usr/bin/env python3
"""Build near-pair edge list from near_groups.csv (for Phase-2+ hard-neg mask).

Rule: every unordered pair of distinct files that share the same ``group_id``
and ``kind == cluster`` becomes a near-edge. Singletons / root leftovers are
not paired with anyone (they may be used as negatives freely).

Output columns: file_a, file_b, group_id, winery, reason

Example::

    uv run python scripts/build_near_graph.py
    uv run python scripts/build_near_graph.py \\
        --groups data/train_dataset/near_clusters/_meta/near_groups.csv \\
        --out data/train_dataset/near_clusters/_meta/near_edges.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger("build_near_graph")

_REPO = Path(__file__).resolve().parents[1]
NEAR = _REPO / "data" / "train_dataset" / "near_clusters"
DEFAULT_GROUPS = NEAR / "_meta" / "near_groups.csv"
DEFAULT_OUT = NEAR / "_meta" / "near_edges.csv"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", type=Path, default=DEFAULT_GROUPS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--include-singletons",
        action="store_true",
        help="Also emit edges inside singleton dirs (usually unwanted)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not args.groups.is_file():
        logger.error("missing groups file %s — run scan_near_groups.py first", args.groups)
        return 1

    members: dict[str, list[dict]] = defaultdict(list)
    for row in csv.DictReader(args.groups.open(encoding="utf-8")):
        if row["kind"] != "cluster" and not args.include_singletons:
            continue
        members[row["group_id"]].append(row)

    edges: list[dict] = []
    for gid, rows in members.items():
        if len(rows) < 2:
            continue
        files = sorted({r["file"] for r in rows})
        winery = rows[0]["winery"]
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                edges.append(
                    {
                        "file_a": files[i],
                        "file_b": files[j],
                        "group_id": gid,
                        "winery": winery,
                        "reason": "same_near_group",
                    }
                )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["file_a", "file_b", "group_id", "winery", "reason"]
        )
        w.writeheader()
        w.writerows(edges)

    n_multi = sum(1 for rows in members.values() if len(rows) >= 2)
    logger.info(
        "near edges=%s from %s multi-member groups → %s",
        len(edges),
        n_multi,
        args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
