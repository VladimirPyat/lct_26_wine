#!/usr/bin/env python3
"""Build onnx_fp16_siglip.ipynb — fp32 SigLIP2 ONNX → fp16 / fp16+graph-opt + strict accuracy gate."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).with_name("onnx_fp16_siglip.ipynb")


def md(text: str) -> dict:
    text = text.strip("\n")
    lines = text.split("\n")
    src = [ln + "\n" for ln in lines[:-1]] + ([lines[-1] + "\n"] if lines else [])
    return {"cell_type": "markdown", "metadata": {}, "source": src}


def code(text: str) -> dict:
    text = text.strip("\n")
    lines = text.split("\n")
    src = [ln + "\n" for ln in lines[:-1]] + ([lines[-1] + "\n"] if lines else [])
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": src,
    }


cells: list[dict] = []

cells.append(
    md(
        """
# SigLIP2 ONNX → FP16 (два варианта) + строгая проверка точности

Исходник — уже проверенный fp32 `siglip2_wine_p1_epoch_3.onnx` на Drive (`_models_v4_siglip/`).
torch / transformers / peft **не нужны**: только `onnx` + `onnxruntime-gpu`. Runtime: **GPU (T4)**.

| Вариант | Файл | Что делаем |
|---|---|---|
| A. fp16 | `siglip2_wine_p1_epoch_3_fp16.onnx` | тот же граф, веса и вычисления → fp16 |
| B. fp16 + opt | `siglip2_wine_p1_epoch_3_fp16_opt.onnx` | сначала фьюзы графа ORT (LayerNorm / Gelu / Attention / SkipLayerNorm, свёртка констант), потом fp16 |

Без квантования. Вход/выход остаются fp32 (`keep_io_types=True`) — `DinoOnnxEncoder` и `*_preprocess.json` не меняются.

## Правило решения
Сравниваем с fp32 на Dev-A и Dev-B (кропы запросов, полный `catalog/train`):
- R@1, R@5, MRR — **не ниже** fp32;
- **ни один** запрос не опустился по рангу GT.

Хоть одно нарушение → вариант отбрасываем, остаёмся на fp32.
Косинус с fp32 и `mean_gap12` — информативно (gap12 влияет на порог OCR `margin_min`).

Финальная проверка — локально на `owner_eval` (1 и 2) через `scripts/compare_dino_onnx.py` (команда в конце).
"""
    )
)

cells.append(md("## 0. Setup"))

cells.append(
    code(
        """
# Latest onnxruntime-gpu targets CUDA 13; Colab ships CUDA 12 → pin a CUDA 12 build.
# Remove CPU onnxruntime if present: it shadows the GPU package.
!nvidia-smi --query-gpu=name,driver_version --format=csv
!pip uninstall -y -q onnxruntime
!pip install -q "onnxruntime-gpu==1.22.0" onnx sympy opencv-python-headless tqdm
import onnxruntime as ort
ort.preload_dlls()   # CUDA/cuDNN 12 libs from Colab's nvidia-* pip packages
print("ort", ort.__version__, ort.get_available_providers())

# get_available_providers() lists compiled EPs even if CUDA libs fail to load — check a real session
import numpy as np, onnx
from onnx import helper as _h, TensorProto as _T
_probe = _h.make_model(
    _h.make_graph([_h.make_node("Relu", ["x"], ["y"])], "probe",
                  [_h.make_tensor_value_info("x", _T.FLOAT, [1])],
                  [_h.make_tensor_value_info("y", _T.FLOAT, [1])]),
    opset_imports=[_h.make_opsetid("", 17)],
    ir_version=8,   # new onnx defaults to IR 14; ORT 1.22 reads up to IR 10
)
_s = ort.InferenceSession(_probe.SerializeToString(), providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
print("session providers:", _s.get_providers())
assert _s.get_providers()[0] == "CUDAExecutionProvider", "CUDA EP не загрузился: GPU runtime (T4)? версия ORT?"
"""
    )
)

cells.append(
    code(
        r"""
from google.colab import drive
drive.mount("/content/drive")

import os, json, csv, shutil
from pathlib import Path

# ============================================================
# ЕДИНСТВЕННЫЙ путь, который обычно нужно менять:
# ============================================================
BASE_PATH = "/content/drive/MyDrive/ЛЦТ26/2_embed_train_data"

MODELS_PATH = f"{BASE_PATH}/_models_v4_siglip"
SRC_TAG = "siglip2_wine_p1_epoch_3"
SRC_ONNX = f"{MODELS_PATH}/{SRC_TAG}.onnx"
SRC_META = f"{MODELS_PATH}/{SRC_TAG}_preprocess.json"

CATALOG = f"{BASE_PATH}/dataset/catalog/train"
DEV_SETS = {
    "dev_a": (f"{BASE_PATH}/dev_a/queries_crop", f"{BASE_PATH}/dev_a/manifest.tsv"),
    "dev_b": (f"{BASE_PATH}/dev_b/queries_crop", f"{BASE_PATH}/dev_b/manifest.tsv"),
}

OUT = {
    "fp32": SRC_ONNX,
    "fp16": f"{MODELS_PATH}/{SRC_TAG}_fp16.onnx",
    "fp16_opt": f"{MODELS_PATH}/{SRC_TAG}_fp16_opt.onnx",
}

# SigLIP2-so400m vision tower
NUM_HEADS, HIDDEN = 16, 1152
# Ops kept in fp32 inside the fp16 graph; leave empty first, add e.g. "LayerNormalization" if parity is poor
FP16_BLOCK_OPS: list[str] = []
# ORT fusion profile for the optimizer ("vit" or "clip")
OPT_MODEL_TYPE = "vit"

LOCAL = "/content/onnx_work"   # local disk: faster than Drive for 1.7 GB loads
os.makedirs(LOCAL, exist_ok=True)

for p in [SRC_ONNX, SRC_META, CATALOG] + [x for pair in DEV_SETS.values() for x in pair]:
    print(("OK  " if os.path.exists(p) else "MISS"), p)
data_file = SRC_ONNX + ".data"
print("external data:", os.path.exists(data_file))
"""
    )
)

cells.append(md("## 1. Вариант A — fp16 (тот же граф)"))

cells.append(
    code(
        r"""
import onnx
from onnxruntime.transformers.float16 import convert_float_to_float16
from onnxruntime.transformers.onnx_model import OnnxModel

local_src = f"{LOCAL}/{SRC_TAG}.onnx"
if not os.path.exists(local_src):
    shutil.copyfile(SRC_ONNX, local_src)
    if os.path.exists(SRC_ONNX + ".data"):
        shutil.copyfile(SRC_ONNX + ".data", local_src + ".data")

model = onnx.load(local_src)
SRC_IR = model.ir_version   # 8 for our export; ORT 1.22 reads up to IR 10
print("source IR", SRC_IR)
m16 = convert_float_to_float16(
    model,
    keep_io_types=True,
    op_block_list=FP16_BLOCK_OPS or None,
)
# keep_io_types appends input Casts at the end of the node list; checker needs topo order
om16 = OnnxModel(m16)
om16.topological_sort()
om16.model.ir_version = SRC_IR
local_a = f"{LOCAL}/{SRC_TAG}_fp16.onnx"
onnx.save(om16.model, local_a)
onnx.checker.check_model(local_a)
del model, m16, om16
print(f"A fp16 -> {local_a} ({os.path.getsize(local_a) / 2**20:.0f} MiB)")
"""
    )
)

cells.append(md("## 2. Вариант B — фьюзы графа + fp16"))

cells.append(
    code(
        r"""
from onnxruntime.transformers.optimizer import optimize_model
from onnxruntime.transformers.fusion_options import FusionOptions

fo = FusionOptions(OPT_MODEL_TYPE)
opt = optimize_model(
    local_src,
    model_type=OPT_MODEL_TYPE,
    num_heads=NUM_HEADS,
    hidden_size=HIDDEN,
    optimization_options=fo,
    opt_level=0,        # python fusions only → portable graph; ORT applies EP-specific opts at load
    use_gpu=True,
)
print("fused ops:", opt.get_fused_operator_statistics())
opt.convert_float_to_float16(
    keep_io_types=True,
    op_block_list=FP16_BLOCK_OPS or None,
)
opt.topological_sort()
opt.model.ir_version = SRC_IR
local_b = f"{LOCAL}/{SRC_TAG}_fp16_opt.onnx"
opt.save_model_to_file(local_b, use_external_data_format=False)
onnx.checker.check_model(local_b)
del opt
print(f"B fp16_opt -> {local_b} ({os.path.getsize(local_b) / 2**20:.0f} MiB)")
"""
    )
)

cells.append(md("## 3. Препроцесс + энкодинг (как в проде: letterbox, mean/std из `*_preprocess.json`)"))

cells.append(
    code(
        r"""
import cv2
import numpy as np
from tqdm.auto import tqdm

meta = json.load(open(SRC_META))
SIZE = int(meta["input_size"])
FILL = tuple(meta["pad_fill_rgb"])
MEAN = np.array(meta["image_mean"], dtype=np.float32)
STD = np.array(meta["image_std"], dtype=np.float32)
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def letterbox_rgb(rgb, size, fill):
    # same as src/core/retrieve/preprocess.py
    h, w = rgb.shape[:2]
    scale = size / max(h, w)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    resized = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
    out = np.full((size, size, 3), fill, dtype=np.uint8)
    top, left = (size - nh) // 2, (size - nw) // 2
    out[top:top + nh, left:left + nw] = resized
    return out


def preprocess(path):
    bgr = cv2.imread(str(path))
    if bgr is None:
        raise FileNotFoundError(path)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    x = letterbox_rgb(rgb, SIZE, FILL).astype(np.float32) / 255.0
    x = (x - MEAN) / STD
    return np.transpose(x, (2, 0, 1))


def l2(x):
    return x / np.linalg.norm(x, axis=1, keepdims=True).clip(min=1e-12)


def load_batch(paths):
    return np.stack([preprocess(p) for p in paths]).astype(np.float32)


def encode(onnx_path, paths, batch=32):
    sess = ort.InferenceSession(onnx_path, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    assert sess.get_providers()[0] == "CUDAExecutionProvider", f"{onnx_path}: fell back to CPU"
    name = sess.get_inputs()[0].name
    outs = []
    for i in tqdm(range(0, len(paths), batch), desc=Path(onnx_path).stem, leave=False):
        outs.append(sess.run(None, {name: load_batch(paths[i:i + batch])})[0].astype(np.float32))
    del sess
    return l2(np.concatenate(outs))


cat_files = sorted(f for f in os.listdir(CATALOG) if Path(f).suffix.lower() in IMG_EXT)
cat_paths = [os.path.join(CATALOG, f) for f in cat_files]
cat_idx = {f: i for i, f in enumerate(cat_files)}


def load_manifest(qdir, man):
    rows = list(csv.DictReader(open(man, encoding="utf-8"), delimiter="\t"))
    pairs = []
    for r in rows:
        q = r.get("query_file") or r.get("query")
        c = r.get("catalog_file") or r.get("catalog") or r.get("gt")
        if q and c in cat_idx and os.path.exists(os.path.join(qdir, q)):
            pairs.append((os.path.join(qdir, q), cat_idx[c]))
    return pairs, len(rows)


dev = {}
for name, (qdir, man) in DEV_SETS.items():
    pairs, n_rows = load_manifest(qdir, man)
    dev[name] = pairs
    print(f"{name}: {len(pairs)}/{n_rows} scored (GT in catalog)")
print("catalog:", len(cat_files))
"""
    )
)

cells.append(md("## 4. Считаем эмбеддинги трёх моделей"))

cells.append(
    code(
        r"""
MODELS = {"fp32": local_src, "fp16": local_a, "fp16_opt": local_b}
EMB = {}
for tag, path in MODELS.items():
    EMB[tag] = {"catalog": encode(path, cat_paths)}
    for name, pairs in dev.items():
        EMB[tag][name] = encode(path, [p for p, _ in pairs])
    print("done", tag)
"""
    )
)

cells.append(md("## 5. Метрики и вердикт"))

cells.append(
    code(
        r"""
def retrieval(q, c, gts):
    sims = q @ c.T
    ranks, gaps = [], []
    for i, gt in enumerate(gts):
        order = np.argsort(-sims[i])
        ranks.append(int(np.where(order == gt)[0][0]) + 1)
        gaps.append(float(sims[i, order[0]] - sims[i, order[1]]))
    r = np.array(ranks)
    return {
        "R@1": float((r <= 1).mean()), "R@5": float((r <= 5).mean()),
        "MRR": float((1.0 / r).mean()), "mean_gap12": float(np.mean(gaps)),
        "n": len(r), "ranks": ranks,
    }


report = {"metrics": {}, "parity": {}, "verdict": {}}
for tag in MODELS:
    report["metrics"][tag] = {}
    for name, pairs in dev.items():
        report["metrics"][tag][name] = retrieval(EMB[tag][name], EMB[tag]["catalog"], [g for _, g in pairs])

for tag in ("fp16", "fp16_opt"):
    cos = (EMB[tag]["catalog"] * EMB["fp32"]["catalog"]).sum(1)
    report["parity"][tag] = {"cos_min": float(cos.min()), "cos_mean": float(cos.mean())}
    fails = []
    for name in dev:
        a, b = report["metrics"]["fp32"][name], report["metrics"][tag][name]
        for k in ("R@1", "R@5", "MRR"):
            if b[k] < a[k] - 1e-9:
                fails.append(f"{name} {k} {a[k]:.4f} -> {b[k]:.4f}")
        worse = [(dev[name][i][0].rsplit("/", 1)[-1], ra, rb)
                 for i, (ra, rb) in enumerate(zip(a["ranks"], b["ranks"])) if rb > ra]
        fails += [f"{name} rank down {q}: {ra} -> {rb}" for q, ra, rb in worse]
    report["verdict"][tag] = {"pass": not fails, "fails": fails}

print(f"{'model':10} {'set':6} {'R@1':>7} {'R@5':>7} {'MRR':>7} {'gap12':>7}  n")
for tag in MODELS:
    for name in dev:
        m = report["metrics"][tag][name]
        print(f"{tag:10} {name:6} {m['R@1']:7.4f} {m['R@5']:7.4f} {m['MRR']:7.4f} {m['mean_gap12']:7.4f}  {m['n']}")
print()
for tag in ("fp16", "fp16_opt"):
    p, v = report["parity"][tag], report["verdict"][tag]
    warn = "  (cos_min < 0.995 — подозрительно)" if p["cos_min"] < 0.995 else ""
    print(f"{tag}: cos vs fp32 min={p['cos_min']:.5f} mean={p['cos_mean']:.5f}{warn}")
    print(f"  VERDICT: {'PASS' if v['pass'] else 'FAIL → остаёмся на fp32'}")
    for f in v["fails"]:
        print("   -", f)
"""
    )
)

cells.append(md("## 6. Сохраняем прошедшие варианты на Drive"))

cells.append(
    code(
        r"""
for tag, local in (("fp16", local_a), ("fp16_opt", local_b)):
    if not report["verdict"][tag]["pass"]:
        print(f"skip {tag}: FAIL")
        continue
    shutil.copyfile(local, OUT[tag])
    m = dict(meta, tag=f"{meta.get('tag', SRC_TAG)}_{tag}", source_onnx=os.path.basename(SRC_ONNX),
             precision="fp16", graph_opt=(tag == "fp16_opt"), fp16_block_ops=FP16_BLOCK_OPS)
    with open(OUT[tag].replace(".onnx", "_preprocess.json"), "w") as f:
        json.dump(m, f, indent=2)
    print(f"saved {OUT[tag]} ({os.path.getsize(OUT[tag]) / 2**20:.0f} MiB)")

slim = {k: v for k, v in report.items()}
slim["metrics"] = {t: {s: {k: v for k, v in m.items() if k != "ranks"} for s, m in d.items()}
                   for t, d in report["metrics"].items()}
with open(f"{MODELS_PATH}/{SRC_TAG}_fp16_check.json", "w") as f:
    json.dump(slim, f, indent=2, ensure_ascii=False)
print("report ->", f"{MODELS_PATH}/{SRC_TAG}_fp16_check.json")
print("Скачай прошедшие *.onnx + *_preprocess.json → bin/")
"""
    )
)

cells.append(
    md(
        """
## 7. Финальная проверка локально (owner_eval 1 и 2, YOLO-кроп из прода)

Эталон fp32 (кроп): set1 26/27 top-1, set2 24/24 top-1, top-5 — 100%.

```bash
export LD_LIBRARY_PATH=$(ls -d $PWD/.venv/lib/python*/site-packages/nvidia/cu13/lib):$(ls -d $PWD/.venv/lib/python*/site-packages/nvidia/cudnn/lib):$LD_LIBRARY_PATH
for s in 1 2; do
  uv run python scripts/compare_dino_onnx.py \\
    --onnx bin/siglip2_wine_p1_epoch_3.onnx bin/siglip2_wine_p1_epoch_3_fp16.onnx bin/siglip2_wine_p1_epoch_3_fp16_opt.onnx \\
    --catalog data/train_dataset/embed_train_data/dataset/catalog/train \\
    --queries data/owner_eval/$s/queries --golden data/owner_eval/$s/predictions.golden.jsonl \\
    --preprocess-json bin/siglip2_wine_p1_epoch_3_preprocess.json \\
    --device cuda --batch 8 --crop-queries --topk 5 \\
    --out-json agent_docs/reports/fp16_siglip_owner_eval_$s.json
done
```

Переключение в проде — только если прошёл и Colab-гейт, и owner_eval: `dino_model_path` в `config/database.yaml`
(`embedding_dim` 1152 не меняется) + пересборка эмбеддингов каталога той же моделью.
"""
    )
)

nb = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"gpuType": "T4", "provenance": []},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}
OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"wrote {OUT}")
