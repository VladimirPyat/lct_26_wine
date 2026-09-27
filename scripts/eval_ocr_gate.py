#!/usr/bin/env python3
"""Offline check of the OCR rerank policy on Dev crops (no DB, no API).

Top-5 per query comes from ``crop_score_gaps.json`` (embedding eval output);
metadata from catalog CSVs; OCR = production engine from ``ocr_rerank.yaml``
on ``dev_*/queries_crop``. Runs ``core.policy.decision.decide`` for each
``margin_min`` x ``rerank_mode`` and reports R@1 and switch outcomes.

Usage:
  uv run python scripts/eval_ocr_gate.py
  uv run python scripts/eval_ocr_gate.py --model dinov2_large_wine_phase3
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.config import load_app_settings, load_ocr_rerank_settings  # noqa: E402
from core.contracts import RankedHit  # noqa: E402
from core.ocr.base import IOCREngine  # noqa: E402
from core.ocr.factory import create_ocr_engine  # noqa: E402
from core.policy.decision import decide  # noqa: E402
from core.text.fuzzy import FuzzyReranker  # noqa: E402

DEV_ROOT = _REPO / "data" / "train_dataset" / "embed_train_data"
REPORTS = _REPO / "agent_docs" / "reports"
READY_CSVS = (
    _REPO / "scripts" / "catalog_prepare" / "wines_ready.csv",
    _REPO / "scripts" / "catalog_prepare" / "wines_additional.csv",
)
OWNER_CSV = _REPO / "data" / "owner_database" / "wines_integrated_updated.csv"
MODES = ("off", "always", "confident")


def load_meta() -> dict[str, dict[str, str]]:
    meta: dict[str, dict[str, str]] = {}
    if OWNER_CSV.is_file():
        with OWNER_CSV.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                meta[row["Slug"].strip()] = {
                    "title": row["Название вина"],
                    "manufacturer": row["Винодельня"],
                    "category": row["Цвет"] or row["Категория"],
                    "grape_variety": row["Сорт винограда"],
                }
    for path in READY_CSVS:
        if not path.is_file():
            continue
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                meta[row["slug"].strip()] = {
                    "title": row["title"],
                    "manufacturer": row["manufacturer"],
                    "category": row["category"],
                    "grape_variety": row["grape_variety"],
                }
    return meta


def build_hits(row: dict, meta: dict[str, dict[str, str]]) -> list[RankedHit]:
    hits: list[RankedHit] = []
    for idx, (fname, score) in enumerate(zip(row["top"], row["s"], strict=True)):
        slug = Path(fname).stem
        m = meta.get(slug, {})
        hits.append(
            RankedHit(
                wine_id=idx + 1,
                slug=slug,
                score=float(score),
                title=m.get("title", slug.replace("-", " ")),
                manufacturer=m.get("manufacturer", ""),
                category=m.get("category", ""),
                image_path=fname,
                grape_variety=m.get("grape_variety", ""),
            )
        )
    return hits


class CachedOCR(IOCREngine):
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def recognize(self, image_path: str) -> list[str]:
        return list(self._lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default="siglip2_wine_p1_epoch_3")
    p.add_argument("--gaps", type=Path, default=REPORTS / "crop_score_gaps.json")
    p.add_argument(
        "--ocr-cache", type=Path, default=REPORTS / "ocr_lines_dev_crops.json"
    )
    p.add_argument(
        "--margins", type=float, nargs="+", default=[0.06, 0.07, 0.08, 0.10]
    )
    p.add_argument("--out-json", type=Path, default=REPORTS / "ocr_gate_eval.json")
    p.add_argument(
        "--max-img-drop",
        type=float,
        default=None,
        help="override policy.max_img_drop (negative = disable)",
    )
    args = p.parse_args(argv)

    settings = load_ocr_rerank_settings()
    compute = load_app_settings().compute
    reranker = FuzzyReranker(
        settings.field_weights,
        settings.fuzzy,
        min_line_chars=settings.ocr.min_line_chars,
        drop_spaced_letters=settings.ocr.drop_spaced_letters,
    )
    rows = json.loads(args.gaps.read_text(encoding="utf-8"))[args.model]
    meta = load_meta()
    max_margin = max(args.margins)

    cache: dict[str, list[str]] = {}
    if args.ocr_cache.is_file():
        cache = json.loads(args.ocr_cache.read_text(encoding="utf-8"))
    engine: IOCREngine | None = None
    for row in rows:
        key = f"{row['set']}/{row['query']}"
        if key in cache or row["s"][0] - row["s"][1] >= max_margin:
            continue
        if engine is None:
            engine = create_ocr_engine(
                settings.ocr.engine,
                llm_task=settings.ocr.llm_task,
                use_cuda=compute.device.lower() == "cuda",
                lang=settings.ocr.lang,
                limit_side_len=settings.ocr.limit_side_len,
                ort_threads=compute.ort_threads,
            )
        crop = DEV_ROOT / row["set"] / "queries_crop" / row["query"]
        cache[key] = engine.recognize(str(crop))
        print(f"ocr {key}: {len(cache[key])} lines")
    args.ocr_cache.write_text(json.dumps(cache, ensure_ascii=False, indent=1), "utf-8")

    results: dict[str, dict] = {}
    details: list[dict] = []
    base_policy = settings.policy
    if args.max_img_drop is not None:
        drop = None if args.max_img_drop < 0 else args.max_img_drop
        base_policy = base_policy.model_copy(update={"max_img_drop": drop})
    print(f"max_img_drop={base_policy.max_img_drop}")
    for margin_min in args.margins:
        for mode in MODES:
            policy = base_policy.model_copy(
                update={
                    "margin_min": margin_min,
                    "enable_rerank": mode != "off",
                    "rerank_mode": "always" if mode == "off" else mode,
                }
            )
            stats = {"r1": 0, "ocr_calls": 0, "fixed": 0, "broken": 0, "n": 0}
            for row in rows:
                key = f"{row['set']}/{row['query']}"
                hits = build_hits(row, meta)
                gt = Path(row["gt"]).stem
                decision = decide(
                    hits,
                    crop_path=key,
                    policy=policy,
                    ocr_factory=lambda k=key: CachedOCR(cache.get(k, [])),
                    reranker=reranker,
                    rerank_top=min(settings.rerank_top, policy.top_k),
                )
                stats["n"] += 1
                stats["r1"] += int(decision.slug == gt)
                stats["ocr_calls"] += int(decision.rerank_triggered)
                before_ok = decision.winner_before_rerank == gt
                after_ok = decision.slug == gt
                stats["fixed"] += int(after_ok and not before_ok)
                stats["broken"] += int(before_ok and not after_ok)
                if decision.rerank_triggered and margin_min == base_policy.margin_min:
                    details.append(
                        {
                            "mode": mode,
                            "query": key,
                            "gt": gt,
                            "margin": round(decision.margin, 4),
                            "image_top1": decision.winner_before_rerank,
                            "text_leader": decision.text_leader,
                            "winner": decision.slug,
                            "reason": decision.rerank_reason,
                            "evidence": decision.evidence,
                        }
                    )
            results[f"{margin_min:.2f}/{mode}"] = stats

    print(f"\nmodel={args.model} n={len(rows)}")
    header = ("margin", "mode", "R@1", "ocr", "fixed", "broken")
    print("{:>7} {:>10} {:>6} {:>4} {:>5} {:>6}".format(*header))
    for name, s in results.items():
        margin, mode = name.split("/")
        print(
            f"{margin:>7} {mode:>10} {s['r1']:>3}/{s['n']:<2} {s['ocr_calls']:>4} "
            f"{s['fixed']:>5} {s['broken']:>6}"
        )
    print(f"\nOCR zone at margin_min={base_policy.margin_min} (confident / always):")
    for d in details:
        if d["mode"] == "off":
            continue
        mark = "OK " if d["winner"] == d["gt"] else "ERR"
        print(
            f"  {mark} {d['mode']:>9} {d['query']:<22} m={d['margin']:.3f} "
            f"img={d['image_top1'][:38]:<38} txt={str(d['text_leader'])[:38]:<38} "
            f"reason={d['reason']}"
        )
    args.out_json.write_text(
        json.dumps({"model": args.model, "results": results, "details": details},
                   ensure_ascii=False, indent=2),
        "utf-8",
    )
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
