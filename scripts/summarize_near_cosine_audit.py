#!/usr/bin/env python3
"""Build priority shortlist from near_cluster_cosine_audit.csv."""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
CSV = _REPO / "agent_docs" / "reports" / "near_cluster_cosine_audit.csv"
OUT = _REPO / "agent_docs" / "reports" / "near_cluster_cosine_audit_priority.md"


def main() -> int:
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    for r in rows:
        r["min_cosine"] = float(r["min_cosine"])
        r["n"] = int(r["n"])
        m = re.match(r"^(\d+)_", r["winery"])
        r["size_hint"] = int(m.group(1)) if m else 0

    focus = [r for r in rows if r["size_hint"] >= 15 or r["n"] >= 5]
    focus.sort(key=lambda r: (r["min_cosine"], -r["n"]))

    buckets: dict[str, int] = defaultdict(int)
    for r in rows:
        s = r["size_hint"]
        if s < 5:
            b = "<5"
        elif s < 10:
            b = "5-9"
        elif s < 20:
            b = "10-19"
        else:
            b = ">=20"
        buckets[b] += 1

    print(f"Total flagged: {len(rows)}")
    print(f"Focus (winery>=15 or cluster n>=5): {len(focus)}")
    print("Flagged by winery size prefix:", dict(buckets))
    print()
    for r in focus[:40]:
        print(f"{r['min_cosine']:.3f}  n={r['n']:2d}  {r['path']}")

    lines = [
        "# Near-cluster cosine audit — priority shortlist",
        "",
        "Model: `bin/dinov2_wine_phase1.onnx`. Flag if any pair cosine **< 0.8**.",
        f"Full list: [{len(rows)} folders](near_cluster_cosine_audit.md) / CSV.",
        "",
        "Filter for selective review: winery code ≥15 **or** cluster size ≥5 "
        "(skip tiny dump `group/` folders when tired).",
        "",
        f"**{len(focus)}** priority folders. Weakest pairs first.",
        "",
        "| min | n | path | pair |",
        "|----:|--:|------|------|",
    ]
    for r in focus:
        lines.append(
            f"| {r['min_cosine']:.3f} | {r['n']} | `{r['path']}` | "
            f"`{r['file_a']}` ↔ `{r['file_b']}` |"
        )
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
