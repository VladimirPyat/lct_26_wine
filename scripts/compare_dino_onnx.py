#!/usr/bin/env python3
"""Compare two (or more) DINO ONNX checkpoints on catalog + query manifests.

No torch — onnxruntime + cv2/numpy only (project ``ml`` extra).

Example:
  uv run python scripts/compare_dino_onnx.py \\
    --onnx bin/dinov2_wine_phase1.onnx bin/dinov2_wine_phase2.onnx \\
    --catalog data/train_dataset/embed_train_data/catalog/train \\
    --queries data/train_dataset/embed_train_data/dev_a/queries \\
    --manifest data/train_dataset/embed_train_data/dev_a/manifest.tsv \\
    --near-groups data/train_dataset/embed_train_data/near/near_groups.csv \\
    --topk 5
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
_IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
# Colab notebooks letterbox with this RGB fill (albumentations PadIfNeeded).
_PAD_FILL_RGB = (123, 116, 103)


def _list_images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in _IMG_EXT
    )


def _letterbox(rgb: np.ndarray, size: int, fill: tuple[int, int, int]) -> np.ndarray:
    h, w = rgb.shape[:2]
    scale = size / max(h, w)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    resized = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
    out = np.full((size, size, 3), fill, dtype=np.uint8)
    top, left = (size - nh) // 2, (size - nw) // 2
    out[top : top + nh, left : left + nw] = resized
    return out


def _preprocess(
    path: Path,
    size: int,
    *,
    resize: str = "stretch",
    mean: np.ndarray = _MEAN,
    std: np.ndarray = _STD,
) -> np.ndarray:
    bgr = cv2.imread(str(path))
    if bgr is None:
        raise FileNotFoundError(path)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    if resize == "letterbox":
        resized = _letterbox(rgb, size, _PAD_FILL_RGB)
    else:
        resized = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_LINEAR)
    x = resized.astype(np.float32) / 255.0
    x = (x - mean) / std
    return np.transpose(x, (2, 0, 1)).astype(np.float32)


def _l2(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=-1, keepdims=True).clip(min=1e-12)
    return x / n


class OnnxEmbedder:
    def __init__(
        self,
        path: Path,
        input_size: int = 224,
        batch: int = 16,
        *,
        resize: str = "stretch",
        mean: np.ndarray = _MEAN,
        std: np.ndarray = _STD,
        providers: list[str] | None = None,
    ):
        self.path = path
        self.input_size = input_size
        self.batch = batch
        self.resize = resize
        self.mean = np.asarray(mean, dtype=np.float32)
        self.std = np.asarray(std, dtype=np.float32)
        self.sess = ort.InferenceSession(
            str(path), providers=providers or ["CPUExecutionProvider"]
        )
        self.input_name = self.sess.get_inputs()[0].name
        outs = {o.name for o in self.sess.get_outputs()}
        if "pooler_output" in outs:
            self.out_name = "pooler_output"
        elif "embedding" in outs:
            self.out_name = "embedding"
        else:
            self.out_name = self.sess.get_outputs()[0].name
        print(
            f"load {path.name}: in={self.input_name} out={self.out_name} "
            f"size={input_size} resize={resize} "
            f"mean={self.mean.tolist()} std={self.std.tolist()} "
            f"providers={self.sess.get_providers()}"
        )

    def encode(self, paths: list[Path]) -> np.ndarray:
        embs: list[np.ndarray] = []
        for i in range(0, len(paths), self.batch):
            chunk = paths[i : i + self.batch]
            stack = np.stack(
                [
                    _preprocess(
                        p,
                        self.input_size,
                        resize=self.resize,
                        mean=self.mean,
                        std=self.std,
                    )
                    for p in chunk
                ],
                axis=0,
            )
            out = self.sess.run([self.out_name], {self.input_name: stack})[0]
            embs.append(_l2(np.asarray(out, dtype=np.float32)))
        return np.concatenate(embs, axis=0) if embs else np.zeros((0, 768), np.float32)


def _crop_queries(
    q_paths: list[Path], out_dir: Path, config: Path | None
) -> tuple[list[Path], dict[str, dict]]:
    """YOLO label crop via the production ``OnnxYoloCropper``; full frame on fallback.

    Query path in the API has no min-side gate, so ``min_side=1`` here.
    """
    if str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))
    from core.config import load_app_settings
    from core.cropper.onnx_yolo import OnnxYoloCropper

    settings = load_app_settings(config)
    cropper = OnnxYoloCropper(settings)
    print(
        f"yolo crop: model={settings.yolo_model_path} "
        f"conf={settings.cropper.confidence} out={out_dir}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    cropped: list[Path] = []
    info: dict[str, dict] = {}
    for src in q_paths:
        dest = out_dir / src.name
        ok, reason, wh = cropper.crop_strict_to_path(str(src), dest, min_side=1)
        if ok:
            cropped.append(dest)
            info[src.name] = {"crop": "crop", "reason": reason, "crop_wh": list(wh or ())}
        else:
            cropped.append(src)
            info[src.name] = {"crop": "fallback", "reason": reason, "crop_wh": []}
            print(f"warn: crop fallback {src.name} reason={reason}")
    n_fb = sum(1 for v in info.values() if v["crop"] == "fallback")
    print(f"yolo crop: crop={len(q_paths) - n_fb} fallback={n_fb}")
    return cropped, info


def _load_golden(path: Path) -> list[tuple[str, str]]:
    """owner_eval predictions.golden.jsonl → (query_filename, catalog_filename).

    GT is ``predicted_slug``; catalog files are ``{slug}.webp``.
    """
    rows: list[tuple[str, str]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            q = Path(str(obj["image_path"])).name
            slug = str(obj["predicted_slug"]).strip()
            rows.append((q, f"{slug}.webp"))
    return rows


def _load_manifest(path: Path) -> list[tuple[str, str]]:
    """Return (query_filename, gt_catalog_filename) rows.

    Supports:
      - embed_train_data/dev_*/manifest.tsv → query_file, catalog_file
      - owner_eval predictions.golden.jsonl (via ``_load_golden``)
      - generic query/gt columns
    """
    rows: list[tuple[str, str]] = []
    if path.suffix.lower() == ".jsonl":
        return _load_golden(path)
    with path.open(newline="", encoding="utf-8") as f:
        sample = f.read(2048)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,")
        reader = csv.DictReader(f, dialect=dialect)
        fields = {n.lower(): n for n in (reader.fieldnames or [])}
        q_key = (
            fields.get("query_file")
            or fields.get("query")
            or fields.get("filename")
            or fields.get("image")
            or fields.get("image_path")
        )
        g_key = (
            fields.get("catalog_file")
            or fields.get("gt")
            or fields.get("gallery")
            or fields.get("target")
            or fields.get("label")
            or fields.get("sku")
        )
        if not q_key or not g_key:
            f.seek(0)
            plain = csv.reader(f, dialect=dialect)
            next(plain, None)
            for row in plain:
                if len(row) >= 2:
                    rows.append((Path(row[0]).name, Path(row[1]).name))
            return rows
        for row in reader:
            rows.append((Path(row[q_key]).name, Path(row[g_key]).name))
    return rows


def _load_near_map(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    out: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (
                row.get("file")
                or row.get("filename")
                or row.get("name")
            )
            group = (
                row.get("group_id")
                or row.get("group")
                or row.get("cluster")
                or row.get("near_group")
            )
            if name and group:
                out[Path(name).name] = str(group)
    return out


def _retrieval_metrics(
    q_embs: np.ndarray,
    q_names: list[str],
    gt_names: list[str],
    cat_embs: np.ndarray,
    cat_ids: list[str],
    topk: int,
) -> dict:
    id_to_idx = {n: i for i, n in enumerate(cat_ids)}
    sims = q_embs @ cat_embs.T
    ranks, hits1, hits5, gaps = [], [], [], []
    flips_detail = []
    for i, gt in enumerate(gt_names):
        if gt not in id_to_idx:
            flips_detail.append({"query": q_names[i], "gt": gt, "status": "gt_missing"})
            continue
        order = np.argsort(-sims[i])
        gt_i = id_to_idx[gt]
        rank = int(np.where(order == gt_i)[0][0]) + 1
        ranks.append(rank)
        hits1.append(1.0 if rank == 1 else 0.0)
        hits5.append(1.0 if rank <= topk else 0.0)
        s_sorted = sims[i, order]
        gap = float(s_sorted[0] - s_sorted[1]) if len(s_sorted) > 1 else 0.0
        gaps.append(gap)
        top = [cat_ids[j] for j in order[:topk]]
        flips_detail.append(
            {
                "query": q_names[i],
                "gt": gt,
                "rank": rank,
                "gap12": gap,
                "top": top,
            }
        )
    n = len(ranks)
    return {
        "n": n,
        "R@1": float(np.mean(hits1)) if n else 0.0,
        f"R@{topk}": float(np.mean(hits5)) if n else 0.0,
        "MRR": float(np.mean([1.0 / r for r in ranks])) if n else 0.0,
        "median_rank": float(np.median(ranks)) if n else 0.0,
        "mean_gap12": float(np.mean(gaps)) if n else 0.0,
        "per_query": flips_detail,
    }


def _false_far_stats(
    cat_embs: np.ndarray,
    cat_ids: list[str],
    near_map: dict[str, str],
    pool_k: int = 30,
    thr: float = 0.80,
) -> dict:
    if not near_map:
        return {"skipped": True}
    sims = cat_embs @ cat_embs.T
    n = len(cat_ids)
    false_far = 0
    total_pool = 0
    high_cos_far = 0
    for i, name in enumerate(cat_ids):
        g_i = near_map.get(name)
        order = np.argsort(-sims[i])
        taken = 0
        for j in order:
            if j == i:
                continue
            other = cat_ids[j]
            g_j = near_map.get(other)
            if g_i and g_j and g_i == g_j:
                continue  # excluded as near — not in hard-FAR pool
            total_pool += 1
            taken += 1
            # false-FAR heuristic: very high cosine but different/missing group
            if float(sims[i, j]) >= thr:
                high_cos_far += 1
                if g_i and g_j and g_i != g_j:
                    false_far += 1
                elif not g_j or not g_i:
                    false_far += 1
            if taken >= pool_k:
                break
    return {
        "pool_slots": total_pool,
        "high_cos_far_ge_thr": high_cos_far,
        "false_far_heuristic": false_far,
        "false_far_rate": (false_far / total_pool) if total_pool else 0.0,
        "thr": thr,
        "pool_k": pool_k,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--onnx", nargs="+", type=Path, required=True)
    p.add_argument("--catalog", type=Path, required=True)
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="TSV/CSV manifest, or owner_eval predictions.golden.jsonl",
    )
    p.add_argument(
        "--golden",
        type=Path,
        default=None,
        help="Alias for --manifest when using predictions.golden.jsonl",
    )
    p.add_argument("--near-groups", type=Path, default=None)
    p.add_argument("--topk", type=int, default=5)
    p.add_argument("--input-size", type=int, default=224)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument(
        "--resize",
        choices=["stretch", "letterbox"],
        default="stretch",
        help="stretch = production DinoOnnxEncoder; letterbox = Colab notebooks",
    )
    p.add_argument(
        "--preprocess-json",
        type=Path,
        default=None,
        help="*_preprocess.json from notebook export (input_size, mean/std, resize)",
    )
    p.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    p.add_argument("--out-json", type=Path, default=None)
    p.add_argument(
        "--catalog-cache",
        type=Path,
        default=None,
        help="Optional .npz: load/save L2 catalog embeddings (keys: ids, embs, onnx)",
    )
    p.add_argument(
        "--crop-queries",
        action="store_true",
        help="YOLO-crop queries with the production cropper before encoding",
    )
    p.add_argument(
        "--crop-config",
        type=Path,
        default=None,
        help="compute_cropper.yaml (default: config/compute_cropper.yaml)",
    )
    p.add_argument(
        "--crop-dir",
        type=Path,
        default=None,
        help="Where to write query crops (default: <out-json stem>_query_crops/)",
    )
    args = p.parse_args()

    manifest_path = args.golden or args.manifest
    if manifest_path is None:
        print("need --manifest or --golden", file=sys.stderr)
        return 1

    cat_paths = _list_images(args.catalog)
    if not cat_paths:
        print(f"empty catalog: {args.catalog}", file=sys.stderr)
        return 1
    cat_ids = [p.name for p in cat_paths]
    pairs = _load_manifest(manifest_path)
    q_dir = args.queries
    q_paths, q_names, gt_names = [], [], []
    for qn, gt in pairs:
        qp = q_dir / qn
        if not qp.is_file():
            hits = list(q_dir.rglob(qn))
            qp = hits[0] if hits else qp
        if not qp.is_file():
            print(f"warn: missing query {qn}")
            continue
        q_paths.append(qp)
        q_names.append(qn)
        gt_names.append(gt)

    input_size, resize, mean, std = args.input_size, args.resize, _MEAN, _STD
    if args.preprocess_json is not None:
        meta = json.loads(args.preprocess_json.read_text(encoding="utf-8"))
        input_size = int(meta["input_size"])
        mean = np.asarray(meta["image_mean"], dtype=np.float32)
        std = np.asarray(meta["image_std"], dtype=np.float32)
        is_lb = str(meta.get("resize", "")).startswith("letterbox")
        resize = "letterbox" if is_lb else "stretch"
    pre_tag = f"{resize}{input_size}"

    near_map = _load_near_map(args.near_groups)
    print(f"catalog={len(cat_paths)} queries={len(q_paths)} near_map={len(near_map)}")

    out = args.out_json or (_REPO / "agent_docs" / "reports" / "compare_dino_onnx.json")
    crop_info: dict[str, dict] = {}
    if args.crop_queries:
        crop_dir = args.crop_dir or out.with_name(out.stem + "_query_crops")
        q_paths, crop_info = _crop_queries(q_paths, crop_dir, args.crop_config)

    all_reports = {}
    per_model_queries: dict[str, list] = {}
    for onnx_path in args.onnx:
        tag = onnx_path.stem
        enc = OnnxEmbedder(
            onnx_path,
            input_size=input_size,
            batch=args.batch,
            resize=resize,
            mean=mean,
            std=std,
            providers=(
                ["CUDAExecutionProvider", "CPUExecutionProvider"]
                if args.device == "cuda"
                else None
            ),
        )
        cat_embs: np.ndarray | None = None
        cache = args.catalog_cache
        if cache is not None and cache.is_file():
            blob = np.load(cache, allow_pickle=False)
            cached_onnx = str(blob["onnx"][0]) if "onnx" in blob.files else ""
            cached_ids = [str(x) for x in blob["ids"].tolist()]
            cached_pre = str(blob["pre"][0]) if "pre" in blob.files else "stretch224"
            if (
                cached_onnx == str(onnx_path.resolve())
                and cached_ids == cat_ids
                and cached_pre == pre_tag
            ):
                cat_embs = np.asarray(blob["embs"], dtype=np.float32)
                print(f"load catalog cache [{tag}] <- {cache} shape={cat_embs.shape}")
            else:
                print(f"warn: catalog cache mismatch, re-encode ({cache})")
        if cat_embs is None:
            print(f"encode catalog [{tag}]...")
            cat_embs = enc.encode(cat_paths)
            if cache is not None:
                cache.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(
                    cache,
                    ids=np.array(cat_ids),
                    embs=cat_embs,
                    onnx=np.array([str(onnx_path.resolve())]),
                    pre=np.array([pre_tag]),
                )
                print(f"wrote catalog cache -> {cache}")
        print(f"encode queries [{tag}]...")
        q_embs = enc.encode(q_paths)
        metrics = _retrieval_metrics(
            q_embs, q_names, gt_names, cat_embs, cat_ids, args.topk
        )
        for row in metrics["per_query"]:
            if row["query"] in crop_info:
                row.update(crop_info[row["query"]])
        ff = _false_far_stats(cat_embs, cat_ids, near_map)
        gt_missing = sum(1 for r in metrics["per_query"] if r.get("status") == "gt_missing")
        all_reports[tag] = {
            "onnx": str(onnx_path),
            "R@1": metrics["R@1"],
            f"R@{args.topk}": metrics[f"R@{args.topk}"],
            "MRR": metrics["MRR"],
            "median_rank": metrics["median_rank"],
            "mean_gap12": metrics["mean_gap12"],
            "n": metrics["n"],
            "gt_missing": gt_missing,
            "crop_queries": bool(args.crop_queries),
            "crop_fallback": sum(1 for v in crop_info.values() if v["crop"] == "fallback"),
            "false_far": ff,
        }
        per_model_queries[tag] = metrics["per_query"]
        print(
            f"[{tag}] n={metrics['n']} gt_missing={gt_missing} "
            f"R@1={metrics['R@1']:.3f} "
            f"R@{args.topk}={metrics[f'R@{args.topk}']:.3f} "
            f"MRR={metrics['MRR']:.3f} gap12={metrics['mean_gap12']:.3f} "
            f"false_far_rate={ff.get('false_far_rate', float('nan')):.3f}"
        )

    # flip list if exactly two models
    if len(per_model_queries) >= 2:
        tags = list(per_model_queries.keys())
        a, b = tags[0], tags[1]
        by_q_a = {r["query"]: r for r in per_model_queries[a]}
        by_q_b = {r["query"]: r for r in per_model_queries[b]}
        flips = []
        for q in by_q_a:
            if q not in by_q_b:
                continue
            ra, rb = by_q_a[q].get("rank"), by_q_b[q].get("rank")
            if ra is None or rb is None:
                continue
            if (ra <= args.topk) != (rb <= args.topk) or ra != rb:
                flips.append(
                    {
                        "query": q,
                        f"rank_{a}": ra,
                        f"rank_{b}": rb,
                        "delta": int(rb) - int(ra),
                    }
                )
        flips.sort(key=lambda x: x["delta"])
        all_reports["_flips"] = flips
        worse = [f for f in flips if f["delta"] > 0]
        better = [f for f in flips if f["delta"] < 0]
        print(f"flips {a}->{b}: better={len(better)} worse={len(worse)} changed={len(flips)}")
        for f in worse[:15]:
            print(f"  LOSE {f['query']}: rank {f[f'rank_{a}']} -> {f[f'rank_{b}']}")
        for f in better[:15]:
            print(f"  WIN  {f['query']}: rank {f[f'rank_{a}']} -> {f[f'rank_{b}']}")

    out.parent.mkdir(parents=True, exist_ok=True)
    # keep per-query out of summary file size — store flips + summary
    payload = {
        "summary": {k: v for k, v in all_reports.items() if k != "_flips"},
        "flips": all_reports.get("_flips", []),
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"wrote {out}")
    per_q_path = out.with_name(out.stem + "_per_query.json")
    per_q_path.write_text(
        json.dumps(per_model_queries, indent=2, ensure_ascii=False)
    )
    print(f"wrote {per_q_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
