#!/usr/bin/env python3
"""Offline replay of the production OCR rerank policy on compare_dino_onnx.py output.

No DB / API: hits are rebuilt from ``*_per_query.json`` (``top10`` + ``top10_scores``)
and catalog metadata CSV; OCR runs on the saved YOLO query crops and is cached.
Calls the real ``core.policy.decision.decide`` with policy variants.

Example:
  uv run python scripts/simulate_ocr_rerank.py \\
    --run siglip=agent_docs/reports/gap_siglip_owner_eval_{set}_per_query.json \\
    --sets 1 2 \\
    --crops agent_docs/reports/gap_siglip_owner_eval_{set}_query_crops \\
    --out-json agent_docs/reports/ocr_rerank_sim.json
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
from core.ocr.factory import create_ocr_engine  # noqa: E402
from core.policy.decision import decide  # noqa: E402
from core.text.fuzzy import FuzzyReranker  # noqa: E402


def _load_catalog(paths: list[Path]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for path in paths:
        with path.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                slug = (row.get("slug") or "").strip()
                if slug and slug not in out:
                    out[slug] = row
    return out


def _hits(
    top: list[str], scores: list[float], catalog: dict[str, dict[str, str]], k: int
) -> list[RankedHit]:
    hits: list[RankedHit] = []
    for i, (fname, score) in enumerate(zip(top[:k], scores[:k], strict=True)):
        slug = Path(fname).stem
        row = catalog.get(slug, {})
        hits.append(
            RankedHit(
                wine_id=i + 1,
                slug=slug,
                score=float(score),
                title=(row.get("title") or "").strip(),
                manufacturer=(row.get("manufacturer") or "").strip(),
                category=(row.get("category") or "").strip(),
                image_path=f"/static/wines/{slug}.webp",
                grape_variety=(row.get("grape_variety") or "").strip(),
            )
        )
    return hits


def _ocr_lines(
    crop: Path, cache: dict[str, list[str]], engine_factory
) -> list[str]:
    key = crop.name
    if key not in cache:
        cache[key] = list(engine_factory().recognize(str(crop)))
    return cache[key]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--run",
        action="append",
        required=True,
        help="tag=path_template with {set}, e.g. siglip=reports/gap_siglip_owner_eval_{set}_per_query.json",
    )
    p.add_argument(
        "--crops",
        required=True,
        help="Crop dir template with {set} (crops are model-independent)",
    )
    p.add_argument("--sets", nargs="+", default=["1", "2"])
    p.add_argument(
        "--catalog-csv",
        type=Path,
        nargs="+",
        default=[
            _REPO / "scripts" / "catalog_prepare" / "wines_clean_ready.csv",
            _REPO / "scripts" / "catalog_prepare" / "wines_ready.csv",
            _REPO / "scripts" / "catalog_prepare" / "wines_additional.csv",
        ],
    )
    p.add_argument("--margins", type=float, nargs="+", default=[0.03, 0.05, 0.08, 0.10, 1.0])
    p.add_argument("--top-ks", type=int, nargs="+", default=[5, 10])
    p.add_argument("--modes", nargs="+", default=["confident", "always"])
    p.add_argument(
        "--ocr-cache",
        type=Path,
        default=_REPO / "agent_docs" / "reports" / "ocr_rerank_sim_ocr_cache.json",
    )
    p.add_argument("--out-json", type=Path, required=True)
    args = p.parse_args()

    settings = load_ocr_rerank_settings()
    compute = load_app_settings().compute
    reranker = FuzzyReranker(
        settings.field_weights,
        settings.fuzzy,
        min_line_chars=settings.ocr.min_line_chars,
        drop_spaced_letters=settings.ocr.drop_spaced_letters,
    )
    catalog = _load_catalog([c for c in args.catalog_csv if c.is_file()])
    print(f"catalog meta rows={len(catalog)}")

    cache: dict[str, list[str]] = {}
    if args.ocr_cache.is_file():
        cache = json.loads(args.ocr_cache.read_text(encoding="utf-8"))
    engine_box: list = []

    def engine_factory():
        if not engine_box:
            ocr = settings.ocr
            engine_box.append(
                create_ocr_engine(
                    ocr.engine,
                    llm_task=ocr.llm_task,
                    use_cuda=compute.device.lower() == "cuda",
                    lang=ocr.lang,
                    limit_side_len=ocr.limit_side_len,
                    ort_threads=compute.ort_threads,
                )
            )
        return engine_box[0]

    report: dict[str, object] = {"prod_policy": settings.policy.model_dump(), "runs": {}}
    for spec in args.run:
        tag, tmpl = spec.split("=", 1)
        queries: list[dict] = []
        for s in args.sets:
            blob = json.loads(Path(tmpl.format(set=s)).read_text(encoding="utf-8"))
            for row in next(iter(blob.values())):
                if "rank" not in row:
                    continue
                crop = Path(args.crops.format(set=s)) / row["query"]
                queries.append({**row, "set": s, "crop": crop})
        missing_meta = {
            Path(f).stem
            for q in queries
            for f in q["top10"]
            if Path(f).stem not in catalog
        }
        if missing_meta:
            print(f"[{tag}] warn: {len(missing_meta)} top-10 slugs without catalog meta")

        variants = []
        base_ok = sum(1 for q in queries if q["rank"] == 1)
        for mode in args.modes:
            for k in args.top_ks:
                for m in args.margins:
                    policy = settings.policy.model_copy(
                        update={"margin_min": m, "top_k": k, "rerank_mode": mode}
                    )
                    per_q = []
                    for q in queries:
                        hits = _hits(q["top10"], q["top10_scores"], catalog, k)
                        gt_slug = Path(q["gt"]).stem

                        def factory(q=q):
                            lines = _ocr_lines(q["crop"], cache, engine_factory)

                            class _Cached:
                                def recognize(self, _path: str) -> list[str]:
                                    return lines

                            return _Cached()

                        d = decide(
                            hits,
                            crop_path=str(q["crop"]),
                            policy=policy,
                            ocr_factory=factory,
                            reranker=reranker,
                            rerank_top=min(settings.rerank_top, k),
                        )
                        per_q.append(
                            {
                                "set": q["set"],
                                "query": q["query"],
                                "gt": gt_slug,
                                "rank": q["rank"],
                                "margin": d.margin,
                                "triggered": d.rerank_triggered,
                                "before": d.winner_before_rerank,
                                "after": d.slug,
                                "reason": d.rerank_reason,
                                "text_leader": d.text_leader,
                                "ok_before": d.winner_before_rerank == gt_slug,
                                "ok_after": d.slug == gt_slug,
                            }
                        )
                    ok_after = sum(1 for r in per_q if r["ok_after"])
                    fixed = [r for r in per_q if r["ok_after"] and not r["ok_before"]]
                    broken = [r for r in per_q if r["ok_before"] and not r["ok_after"]]
                    variants.append(
                        {
                            "mode": mode,
                            "top_k": k,
                            "margin_min": m,
                            "n": len(per_q),
                            "top1_before": base_ok,
                            "top1_after": ok_after,
                            "triggered": sum(1 for r in per_q if r["triggered"]),
                            "fixed": fixed,
                            "broken": broken,
                            "per_query": per_q,
                        }
                    )
                    print(
                        f"[{tag}] mode={mode:9s} top_k={k:2d} margin<{m:.2f}: "
                        f"top1 {base_ok}->{ok_after}/{len(per_q)} "
                        f"ocr_runs={variants[-1]['triggered']} "
                        f"fixed={len(fixed)} broken={len(broken)}"
                    )
                    args.ocr_cache.write_text(
                        json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8"
                    )
        report["runs"][tag] = variants

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
