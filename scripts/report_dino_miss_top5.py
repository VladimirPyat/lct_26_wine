#!/usr/bin/env python3
"""Enrich per-query retrieval results with wine metadata for miss@k analysis.

Reads either ``*_per_query.json`` from ``scripts/compare_dino_onnx.py`` or a
notebook ``phase*_retrieval.csv`` (``--retrieval-csv``), plus
``data/owner_database/wines_integrated_updated.csv`` (Slug join).
Optional ``--near-groups`` marks candidates from the GT near-cluster as ``near``.

Writes:
  - markdown miss cards (GT + top-k with winery/color/grape/category)
  - JSON with the same structure + aggregate confusion counts

Example:
  uv run python scripts/report_dino_miss_top5.py \\
    --per-query agent_docs/reports/compare_dino_large_onnx_owner_eval_1_per_query.json \\
    --wines data/owner_database/wines_integrated_updated.csv \\
    --topk 5 \\
    --out-md agent_docs/reports/compare_dino_large_onnx_owner_eval_1_misses.md \\
    --out-json agent_docs/reports/compare_dino_large_onnx_owner_eval_1_misses.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path


def _load_wines(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            slug = (row.get("Slug") or "").strip()
            if not slug:
                continue
            out[slug] = {
                "slug": slug,
                "name": (row.get("Название вина") or "").strip(),
                "winery": (row.get("Винодельня") or "").strip(),
                "color": (row.get("Цвет") or "").strip(),
                "grape": (row.get("Сорт винограда") or "").strip(),
                "category": (row.get("Категория") or "").strip(),
                "region": (row.get("Регион") or "").strip(),
            }
    return out


def _stem(name: str) -> str:
    return Path(name).stem


def _meta(wines: dict[str, dict], catalog_file: str) -> dict:
    slug = _stem(catalog_file)
    base = wines.get(slug)
    if base is None:
        return {
            "file": catalog_file,
            "slug": slug,
            "name": "",
            "winery": "",
            "color": "",
            "grape": "",
            "category": "",
            "region": "",
            "in_csv": False,
        }
    return {"file": catalog_file, "in_csv": True, **base}


def _load_near_groups(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as f:
        return {row["file"]: row["group_id"] for row in csv.DictReader(f)}


def _load_retrieval_csv(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "query": r["query"],
                    "gt": r["gt"],
                    "rank": int(r["rank"]),
                    "top": r["top"].split("|"),
                    "gap12": round(float(r["score_gt"]) - float(r["score_top1"]), 4),
                }
            )
    return rows


def _rel(gt: dict, cand: dict, near: dict[str, str] | None = None) -> str:
    if cand["slug"] == gt["slug"]:
        return "GT"
    if near:
        g_gt, g_c = near.get(gt["file"]), near.get(cand["file"])
        if g_gt and g_gt == g_c:
            return "near"
    if gt.get("winery") and cand.get("winery") and gt["winery"] == cand["winery"]:
        return "same_winery"
    return "other"


def _flags(gt: dict, cand: dict) -> dict:
    return {
        "same_winery": bool(gt.get("winery") and cand.get("winery") and gt["winery"] == cand["winery"]),
        "same_color": bool(gt.get("color") and cand.get("color") and gt["color"] == cand["color"]),
        "same_category": bool(
            gt.get("category") and cand.get("category") and gt["category"] == cand["category"]
        ),
        "same_grape": bool(gt.get("grape") and cand.get("grape") and gt["grape"] == cand["grape"]),
    }


def analyze(
    rows: list[dict],
    wines: dict[str, dict],
    topk: int,
    tag: str,
    near: dict[str, str] | None = None,
) -> dict:
    misses: list[dict] = []
    gt_missing: list[dict] = []
    scored = 0
    for r in rows:
        if r.get("status") == "gt_missing":
            gt_missing.append(
                {
                    "query": r.get("query"),
                    "gt_file": r.get("gt"),
                    "gt": _meta(wines, r.get("gt") or ""),
                }
            )
            continue
        rank = int(r["rank"])
        scored += 1
        if rank <= topk:
            continue
        gt = _meta(wines, r["gt"])
        tops = []
        for i, fname in enumerate(r.get("top") or [], start=1):
            cand = _meta(wines, fname)
            tops.append(
                {
                    "pos": i,
                    **cand,
                    "relation": _rel(gt, cand, near),
                    **_flags(gt, cand),
                }
            )
        misses.append(
            {
                "query": r["query"],
                "rank": rank,
                "gap12": r.get("gap12"),
                "gt": gt,
                "top": tops,
                "top_relations": dict(Counter(t["relation"] for t in tops)),
                "n_same_winery_in_top": sum(1 for t in tops if t["same_winery"]),
                "n_same_color_in_top": sum(1 for t in tops if t["same_color"]),
                "n_same_category_in_top": sum(1 for t in tops if t["same_category"]),
            }
        )

    misses.sort(key=lambda m: m["rank"])

    # aggregates across miss tops (intruders only)
    intruder_files: Counter[str] = Counter()
    intruder_wineries: Counter[str] = Counter()
    rel_slots: Counter[str] = Counter()
    color_pair: Counter[str] = Counter()
    winery_pair: Counter[str] = Counter()
    for m in misses:
        gt_w = m["gt"].get("winery") or "?"
        gt_c = m["gt"].get("color") or "?"
        for t in m["top"]:
            rel_slots[t["relation"]] += 1
            if t["relation"] == "GT":
                continue
            intruder_files[t["file"]] += 1
            if t.get("winery"):
                intruder_wineries[t["winery"]] += 1
            color_pair[f"{gt_c} → {t.get('color') or '?'}"] += 1
            winery_pair[f"{gt_w} → {t.get('winery') or '?'}"] += 1

    return {
        "tag": tag,
        "topk": topk,
        "n_scored": scored,
        "n_miss": len(misses),
        "n_hit": scored - len(misses),
        "R_at_k": (scored - len(misses)) / scored if scored else 0.0,
        "gt_missing": gt_missing,
        "slot_relations_on_miss": dict(rel_slots),
        "top_intruders": intruder_files.most_common(25),
        "top_intruder_wineries": intruder_wineries.most_common(15),
        "color_confusion": color_pair.most_common(20),
        "winery_confusion": winery_pair.most_common(25),
        "misses": misses,
    }


def _fmt_wine(w: dict) -> str:
    bits = [
        w.get("name") or w.get("slug") or "?",
        w.get("winery") or "?",
        w.get("color") or "?",
        w.get("grape") or "?",
        w.get("category") or "?",
    ]
    return " · ".join(bits)


def to_markdown(report: dict, title: str) -> str:
    k = report["topk"]
    lines: list[str] = [
        f"# {title}",
        "",
        f"**Model tag:** `{report['tag']}`  ",
        f"**Scored:** {report['n_scored']}  ·  "
        f"**Hit@{k}:** {report['n_hit']}  ·  "
        f"**Miss@{k}:** {report['n_miss']}  ·  "
        f"**R@{k}:** {report['R_at_k']:.3f}",
        "",
        "Slug meta from `data/owner_database/wines_integrated_updated.csv` "
        "(name · winery · color · grape · category).",
        "",
        "---",
        "",
        "## Aggregates on miss queries (top-k slots)",
        "",
        "| relation | slots |",
        "|----------|------:|",
    ]
    for rel, n in sorted(report["slot_relations_on_miss"].items(), key=lambda x: -x[1]):
        lines.append(f"| `{rel}` | {n} |")
    lines += [
        "",
        "### Frequent intruders (appear in miss top-k, not GT)",
        "",
        "| n | file | winery (from CSV) |",
        "|--:|------|-------------------|",
    ]
    wines_by_file = {}
    for m in report["misses"]:
        for t in m["top"]:
            wines_by_file[t["file"]] = t.get("winery") or ""
    for fname, n in report["top_intruders"]:
        lines.append(f"| {n} | `{fname}` | {wines_by_file.get(fname, '')} |")

    lines += [
        "",
        "### Intruder wineries",
        "",
        "| n | winery |",
        "|--:|--------|",
    ]
    for w, n in report["top_intruder_wineries"]:
        lines.append(f"| {n} | {w} |")

    lines += [
        "",
        "### Color GT → top candidate",
        "",
        "| n | pattern |",
        "|--:|---------|",
    ]
    for pat, n in report["color_confusion"]:
        lines.append(f"| {n} | {pat} |")

    lines += [
        "",
        "### Winery GT → top candidate",
        "",
        "| n | pattern |",
        "|--:|---------|",
    ]
    for pat, n in report["winery_confusion"][:20]:
        lines.append(f"| {n} | {pat} |")

    if report["gt_missing"]:
        lines += ["", "## GT missing from gallery", ""]
        for g in report["gt_missing"]:
            lines.append(
                f"- `{g['query']}` → `{g['gt_file']}`  \n  {_fmt_wine(g['gt'])}"
            )

    lines += ["", "---", "", f"## Miss cards (rank > {k})", ""]
    for m in report["misses"]:
        gt = m["gt"]
        lines += [
            f"### `{m['query']}` — rank **{m['rank']}**",
            "",
            f"**GT:** `{gt.get('file')}`  ",
            f"{_fmt_wine(gt)}",
            "",
            f"gap12={m.get('gap12')} · "
            f"same_winery_in_top={m['n_same_winery_in_top']} · "
            f"same_color_in_top={m['n_same_color_in_top']} · "
            f"same_category_in_top={m['n_same_category_in_top']}",
            "",
            "| # | relation | file | name | winery | color | grape | category |",
            "|--:|----------|------|------|--------|-------|-------|----------|",
        ]
        for t in m["top"]:
            lines.append(
                "| {pos} | `{rel}` | `{file}` | {name} | {winery} | {color} | {grape} | {cat} |".format(
                    pos=t["pos"],
                    rel=t["relation"],
                    file=t["file"],
                    name=(t.get("name") or "—").replace("|", "/"),
                    winery=(t.get("winery") or "—").replace("|", "/"),
                    color=(t.get("color") or "—").replace("|", "/"),
                    grape=(t.get("grape") or "—").replace("|", "/"),
                    cat=(t.get("category") or "—").replace("|", "/"),
                )
            )
        lines.append("")

    lines += [
        "---",
        "",
        "## Training signals (heuristic)",
        "",
        "- High `same_winery` in miss tops → need stronger **within-winery** separation "
        "(margin / hard same-winery negatives).",
        "- High `other` + same color/category → **lookalike packaging / line twins** "
        "across producers; near-cluster or hard-FAR mining.",
        "- Color flips (e.g. red GT → white/sparkling tops) → preprocess / label noise / "
        "weak visual cue; check query crop quality before changing loss.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--per-query", type=Path)
    src.add_argument("--retrieval-csv", type=Path, help="notebook phase*_retrieval.csv")
    p.add_argument("--near-groups", type=Path, default=None)
    p.add_argument(
        "--wines",
        type=Path,
        default=Path("data/owner_database/wines_integrated_updated.csv"),
    )
    p.add_argument("--topk", type=int, default=5)
    p.add_argument("--model-tag", type=str, default=None)
    p.add_argument("--title", type=str, default=None)
    p.add_argument("--out-md", type=Path, required=True)
    p.add_argument("--out-json", type=Path, default=None)
    args = p.parse_args()

    if args.retrieval_csv:
        rows = _load_retrieval_csv(args.retrieval_csv)
        tag = args.model_tag or args.retrieval_csv.stem
    else:
        blob = json.loads(args.per_query.read_text(encoding="utf-8"))
        if not isinstance(blob, dict) or not blob:
            print("empty per-query json", file=sys.stderr)
            return 1
        tag = args.model_tag or next(iter(blob.keys()))
        rows = blob[tag]
    wines = _load_wines(args.wines)
    near = _load_near_groups(args.near_groups) if args.near_groups else None
    report = analyze(rows, wines, args.topk, tag, near)
    # JSON-serializable Counters already converted
    out_json = args.out_json or args.out_md.with_suffix(".json")
    # convert nested Counter leftovers if any
    payload = json.loads(json.dumps(report, ensure_ascii=False, default=dict))
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    title = args.title or f"Miss@{args.topk} top cards — {tag}"
    md = to_markdown(payload, title)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(md, encoding="utf-8")
    print(f"misses={report['n_miss']}/{report['n_scored']} wrote {args.out_md} {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
