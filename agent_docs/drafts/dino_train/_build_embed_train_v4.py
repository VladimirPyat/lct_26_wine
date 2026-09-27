#!/usr/bin/env python3
"""Build embed_train_v4.ipynb next to this script (DINOv2-large capacity A/B)."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).with_name("embed_train_v4.ipynb")


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
# Embed train v4 — DINOv2-**large** on **Colab T4** (short P1 → Phase3 stability)

Google Drive: `ЛЦТ26/2_embed_train_data` (same dataset as v3).  
Artifacts: **`_models_v4_large` / `_index_v4_large` / `_logs_v4_large`** — does not overwrite v3 base M1.

## Goal (this run)
Not the absolute R@5 ceiling first. Primary question:

> After a short Phase1 warmup on **Large**, does Phase3 (margin) **still drop** Dev-A R@5 like on base — or does Large hold?

Secondary (later): push Phase1 to 8 ep / compare to base M1 0.852 if stability looks good.

## T4 defaults
- `batch_size=32` (28 catalog + 4 market), `encode_batch_size=32`
- `phase1_epochs=6` (early read at ep3–4 vs `BASE_P1_R5`; final P1 pick = best of 6)
- Grad checkpointing already on. If OOM: set `batch_size=16` / `catalog_in_batch=14` / `market_in_batch=2` / `encode_batch_size=16`.

## Protocol
1. `PHASE=1`, `STOP_AFTER_PHASE1=True` → train 6 ep, pick best_adapter.
2. Compare curve to base@same epoch (ep3 base was already **0.741** > P2/P3 finals — useful early signal, not a substitute for ep6 best).
3. Then `PHASE=3`, `STOP_AFTER_PHASE1=False` → margin from **this** Large best (skip Phase2 hard-CE; it hurt base).
4. Success for *this* experiment: Phase3 best ≥ Large P1 best (no drop), or drop ≪ base’s −1…−2 hits.

**Customer:** top-5 from embeddings. Phase2 stays archive-only.
"""
    )
)

cells.append(md("## 0. Setup"))

cells.append(
    code(
        """
# Установка зависимостей (Colab)
# peft новых версий требует torchao>=0.16; в Colab часто лежит 0.10 → без upgrade падает get_peft_model
!pip install -q -U transformers peft accelerate albumentations tqdm
!pip install -q -U "torchao>=0.16.0"
print("deps ok")
"""
    )
)

cells.append(
    code(
        r"""
from google.colab import drive
drive.mount("/content/drive")

import os
import csv
import sys
from pathlib import Path

# ============================================================
# ЕДИНСТВЕННЫЙ путь, который обычно нужно менять:
# ============================================================
BASE_PATH = "/content/drive/MyDrive/ЛЦТ26/2_embed_train_data"
# Локально для проверки можно так:
# BASE_PATH = "/work/lct_vine_final/data/train_dataset/embed_train_data"

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}

# Все остальные пути — только от BASE_PATH
# Dev queries = YOLO label crops (same as API); "queries" = raw phone photos
DEV_QUERIES_SUBDIR = "queries_crop"

PATHS = {
    "BASE_PATH": BASE_PATH,
    "dataset": f"{BASE_PATH}/dataset",
    "catalog_train": f"{BASE_PATH}/dataset/catalog/train",   # train + индекс
    "catalog_val": f"{BASE_PATH}/dataset/catalog/val",
    "market_train_anchor": f"{BASE_PATH}/dataset/market/train/anchor",
    "market_train_pos": f"{BASE_PATH}/dataset/market/train/positives",
    "market_val_anchor": f"{BASE_PATH}/dataset/market/val/anchor",
    "market_val_pos": f"{BASE_PATH}/dataset/market/val/positives",
    "dev_a": f"{BASE_PATH}/dev_a",
    "dev_a_queries": f"{BASE_PATH}/dev_a/{DEV_QUERIES_SUBDIR}",
    "dev_a_manifest": f"{BASE_PATH}/dev_a/manifest.tsv",
    "dev_b": f"{BASE_PATH}/dev_b",
    "dev_b_queries": f"{BASE_PATH}/dev_b/{DEV_QUERIES_SUBDIR}",
    "dev_b_manifest": f"{BASE_PATH}/dev_b/manifest.tsv",
    "near_groups": f"{BASE_PATH}/near/near_groups.csv",  # optional until Phase 2
    # v4 large: isolated dirs so v3 base M1 / logs stay untouched
    "models": f"{BASE_PATH}/_models_v4_large",
    "index": f"{BASE_PATH}/_index_v4_large",
    "logs": f"{BASE_PATH}/_logs_v4_large",
}

# aliases used later in notebook
DATASET_PATH = PATHS["dataset"]
OWNER_CATALOG = PATHS["catalog_train"]  # index source
DEV_A = PATHS["dev_a"]
DEV_B = PATHS["dev_b"]
NEAR_GROUPS = PATHS["near_groups"]
MODELS_PATH = PATHS["models"]
INDEX_PATH = PATHS["index"]
LOGS_PATH = PATHS["logs"]

for p in (MODELS_PATH, INDEX_PATH, LOGS_PATH, PATHS["catalog_val"]):
    os.makedirs(p, exist_ok=True)


def list_images(directory):
    d = Path(directory)
    if not d.is_dir():
        return []
    return sorted(
        p for p in d.rglob("*")
        if p.is_file() and p.suffix.lower() in IMG_EXT
    )


def count_images(directory):
    return len(list_images(directory))


def market_pair_stats(anchor_dir, pos_dir):
    anchors = list_images(anchor_dir)
    pos_dir = Path(pos_dir)
    paired, missing = 0, []
    for a in anchors:
        hits = list(pos_dir.glob(a.stem + ".*"))
        if hits:
            paired += 1
        else:
            missing.append(a.name)
    return len(anchors), paired, missing


def check_manifest(manifest_path, queries_dir, catalog_dir):
    # Return (n_rows, miss_query, miss_catalog, bad_rows).
    man = Path(manifest_path)
    if not man.is_file():
        return 0, -1, -1, ["MISSING_MANIFEST"]
    qdir, cdir = Path(queries_dir), Path(catalog_dir)
    rows = list(csv.DictReader(man.open(encoding="utf-8"), delimiter="\t"))
    miss_q, miss_c, bad = 0, 0, []
    for r in rows:
        q = r.get("query_file") or r.get("query")
        c = r.get("catalog_file") or r.get("catalog") or r.get("gt")
        if not q or not (qdir / q).exists():
            miss_q += 1
            bad.append(f"query:{q}")
        if not c or not (cdir / c).exists():
            miss_c += 1
            bad.append(f"catalog:{c}")
    return len(rows), miss_q, miss_c, bad[:10]


def assert_layout(require_near: bool = False, require_catalog_val: bool = False):
    # Hard preflight: raise SystemExit if critical paths/data missing.
    print("=" * 72)
    print("PATH CHECKLIST  (меняй только BASE_PATH)")
    print("=" * 72)
    print(f"BASE_PATH = {BASE_PATH}")
    print()
    print("Derived paths:")
    for k, v in PATHS.items():
        if k == "BASE_PATH":
            continue
        print(f"  {k:22s} {v}")
    print()

    errors = []
    warnings = []
    report = []

    # --- existence ---
    required_dirs = [
        "dataset", "catalog_train",
        "market_train_anchor", "market_train_pos",
        "market_val_anchor", "market_val_pos",
        "dev_a_queries", "dev_b_queries",
        "models", "index", "logs",
    ]
    for key in required_dirs:
        ok = Path(PATHS[key]).is_dir()
        report.append((key, "DIR", "OK" if ok else "MISSING", PATHS[key]))
        if not ok:
            errors.append(f"missing dir: {PATHS[key]}")

    for key in ("dev_a_manifest", "dev_b_manifest"):
        ok = Path(PATHS[key]).is_file()
        report.append((key, "FILE", "OK" if ok else "MISSING", PATHS[key]))
        if not ok:
            errors.append(f"missing file: {PATHS[key]}")

    near_ok = Path(PATHS["near_groups"]).is_file()
    report.append(("near_groups", "FILE", "OK" if near_ok else "optional", PATHS["near_groups"]))
    if require_near and not near_ok:
        errors.append(f"near_groups required but missing: {PATHS['near_groups']}")
    elif not near_ok:
        warnings.append("near_groups.csv отсутствует — ок для Phase 1, нужен для Phase 2")

    # --- counts ---
    n_train = count_images(PATHS["catalog_train"])
    n_cval = count_images(PATHS["catalog_val"])
    n_ma, n_paired, miss_pos = market_pair_stats(PATHS["market_train_anchor"], PATHS["market_train_pos"])
    n_mva, n_mvp_paired, miss_vpos = market_pair_stats(PATHS["market_val_anchor"], PATHS["market_val_pos"])
    n_deva = count_images(PATHS["dev_a_queries"])
    n_devb = count_images(PATHS["dev_b_queries"])

    report.append(("catalog_train imgs", "CNT", str(n_train), "index + train"))
    report.append(("catalog_val imgs", "CNT", str(n_cval), "может быть 0"))
    report.append(("market_train pairs", "CNT", f"{n_paired}/{n_ma}", "anchor with positive"))
    report.append(("market_val pairs", "CNT", f"{n_mvp_paired}/{n_mva}", ""))
    report.append(("dev_a queries", "CNT", str(n_deva), ""))
    report.append(("dev_b queries", "CNT", str(n_devb), ""))

    if n_train < 100:
        errors.append(
            f"catalog/train слишком мало изображений: {n_train}. "
            "На Drive должны быть РЕАЛЬНЫЕ файлы (~2000 webp), не symlink. "
            "Перезалей папку dataset/catalog/train с локальной машины "
            "(после: uv run python scripts/prepare_embed_train_data.py --only-catalog)."
        )
    if n_ma == 0:
        errors.append("market/train/anchor пуст — скопируй market со старого Drive")
    if n_paired != n_ma:
        errors.append(f"market train: unpaired anchors {len(miss_pos)} e.g. {miss_pos[:3]}")
    if n_mva and n_mvp_paired != n_mva:
        errors.append(f"market val: unpaired anchors {len(miss_vpos)} e.g. {miss_vpos[:3]}")
    if n_cval == 0 and not require_catalog_val:
        warnings.append("catalog/val пуст — val loss будет только по market/val (это ок)")
    if require_catalog_val and n_cval == 0:
        errors.append("catalog/val пуст")

    # catalog/val should look like catalog (not phone dumps) — soft warn on 2026* names
    phoneish = [p.name for p in list_images(PATHS["catalog_val"]) if p.stem[:4].isdigit()]
    if phoneish:
        warnings.append(
            f"catalog/val содержит {len(phoneish)} файлов с именами как телефонные "
            f"(напр. {phoneish[0]}) — для catalog self-pairs это плохо; лучше пустой val"
        )

    # --- manifests resolve against catalog/train ---
    for label, man, qdir in (
        ("dev_a", PATHS["dev_a_manifest"], PATHS["dev_a_queries"]),
        ("dev_b", PATHS["dev_b_manifest"], PATHS["dev_b_queries"]),
    ):
        n_rows, mq, mc, bad = check_manifest(man, qdir, PATHS["catalog_train"])
        report.append((f"{label} manifest", "CHK", f"rows={n_rows} miss_q={mq} miss_c={mc}", ""))
        if n_rows <= 0:
            errors.append(f"{label}: пустой/битый manifest")
        if mq and mq > 0:
            errors.append(f"{label}: {mq} query из manifest нет в queries/  {bad}")
        if mc and mc > 0:
            errors.append(f"{label}: {mc} catalog_file из manifest нет в catalog/train  {bad}")

    # broken symlinks in catalog/train
    broken = []
    for p in Path(PATHS["catalog_train"]).iterdir():
        if p.is_symlink() and not p.exists():
            broken.append(p.name)
    report.append(("catalog_train symlinks", "CHK", f"broken={len(broken)}", ""))
    if broken:
        errors.append(f"broken symlinks in catalog/train: {broken[:5]}")

    print(f"{'key':28s} {'type':4s} {'status':28s} note")
    print("-" * 72)
    for key, typ, status, note in report:
        print(f"{key:28s} {typ:4s} {status:28s} {note}")

    print()
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  - {e}")
        print()
        raise SystemExit("❌ Layout check FAILED — исправь пути/данные до обучения")
    print("✅ Layout check PASSED — можно идти дальше")
    return {
        "n_catalog_train": n_train,
        "n_catalog_val": n_cval,
        "n_market_train": n_paired,
        "n_market_val": n_mvp_paired,
        "n_dev_a": n_deva,
        "n_dev_b": n_devb,
        "has_near": near_ok,
    }


# Phase 1: near не обязателен. Phase 2: поставь require_near=True
layout_stats = assert_layout(require_near=False, require_catalog_val=False)
print("layout_stats:", layout_stats)
"""
    )
)


cells.append(
    code(
        """
import torch
from datetime import datetime

# === RUN CONTROL (v4 large @ T4) ===
# 1) PHASE=1 short warmup → 2) PHASE=3 margin stability (skip Phase2)
PHASE = 1
STOP_AFTER_PHASE1 = True
RESUME = False            # True = continue last checkpoint of current PHASE
ATTEMPT_ID = "A"          # Phase3 only: "A" | "B" | "C"

# Base Phase1 Dev-A R@5 reference (v3 Colab SSOT) — compare same epoch
BASE_P1_R5 = {
    1: 0.5556,
    2: 0.7037,
    3: 0.7407,
    4: 0.7037,
    5: 0.7407,
    6: 0.7778,
    7: 0.8148,
    8: 0.8519,
}
BASE_M1_R5 = 0.8519  # absolute ceiling target (optional later); not a Phase3 blocker

# Перед Phase 3:
# layout_stats = assert_layout(require_near=True)

CONFIG = {
    "model_name": "facebook/dinov2-large",
    "image_size": 224,
    "dataset_root": DATASET_PATH,
    "owner_catalog": OWNER_CATALOG,  # = catalog/train
    "dev_a": DEV_A,
    "dev_b": DEV_B,
    "near_groups": NEAR_GROUPS,
    # T4: 32 pairs (64 imgs/step). OOM → 16 / 14+2 / encode 16
    "batch_size": 32,
    "catalog_in_batch": 28,
    "market_in_batch": 4,
    "encode_batch_size": 32,
    "eval_every_epoch": True,
    "eval_topk": 5,
    "phase1_epochs": 6,
    "phase2_epochs": 6,
    "phase3_soft_cap": 12,
    "phase3_pool_block": 4,
    "phase3_topk_hard": 10,
    "phase3_semi_hard": 0.95,
    "phase3_lr": 1e-5,
    "learning_rate": 1e-4,
    "weight_decay": 1e-4,
    "temperature": 0.07,
    "lora_r": 8,
    "lora_alpha": 16,
    "lora_dropout": 0.1,
    "target_modules": ["qkv", "proj", "fc1", "fc2"],
    "models_path": MODELS_PATH,
    "index_path": INDEX_PATH,
    "logs_path": LOGS_PATH,
    "phone_style": {
        "rotate": (-15, 15),
        "scale": (0.95, 1.05),
        "translate_percent": (-0.05, 0.05),
        "perspective_scale": (0.03, 0.11),
        "gaussian_blur": (3, 5),
        "motion_blur": 5,
        "brightness_limit": 0.15,
        "contrast_limit": 0.15,
        "isonoise_color_shift": (0.01, 0.03),
        "isonoise_intensity": (0.1, 0.3),
    },
    "light_aug": {
        "rotate": (-5, 5),
        "brightness": 0.05,
        "contrast": 0.05,
        "saturation": 0.02,
        "hue": 0.02,
    },
}

CONFIG["device"] = "cuda" if torch.cuda.is_available() else "cpu"
assert CONFIG["catalog_in_batch"] + CONFIG["market_in_batch"] == CONFIG["batch_size"], (
    "catalog_in_batch + market_in_batch must equal batch_size"
)
print(f"device={CONFIG['device']}  model={CONFIG['model_name']}")
print(f"PHASE={PHASE}  ATTEMPT={ATTEMPT_ID}  STOP_AFTER_PHASE1={STOP_AFTER_PHASE1}")
print(
    f"batch={CONFIG['batch_size']} (cat={CONFIG['catalog_in_batch']}+mkt={CONFIG['market_in_batch']})  "
    f"encode_bs={CONFIG['encode_batch_size']}  P1_epochs={CONFIG['phase1_epochs']}"
)
print(f"artifacts: models={MODELS_PATH}")
print(f"           index={INDEX_PATH}")
print(f"           logs={LOGS_PATH}")
print(f"paths: catalog_train={OWNER_CATALOG}")
print(f"       market={DATASET_PATH}/market")
print(f"       near={NEAR_GROUPS}")
print(f"       dev_a={DEV_A}  dev_b={DEV_B}")
print(f"refs: base@ep3={BASE_P1_R5[3]}  base M1={BASE_M1_R5} (ceiling later)")
"""
    )
)

cells.append(
    md(
        """
## 1. Augmentations + Dataset (Phase 1 pairs)

Раскладка `dataset/` как в v1:
- `catalog/train|val` — clean crops
- `market/train|val/{anchor,positives}` — phone↔catalog пары
"""
    )
)

cells.append(
    code(
        """
import albumentations as A
import cv2
import numpy as np
from PIL import Image, ImageOps
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from transformers import AutoImageProcessor

processor = AutoImageProcessor.from_pretrained(CONFIG["model_name"])

def get_phone_style_aug():
    cfg = CONFIG["phone_style"]
    return A.Compose([
        A.Affine(rotate=cfg["rotate"], scale=cfg["scale"],
                 translate_percent=cfg["translate_percent"], fit_output=True, p=0.8),
        A.Perspective(scale=cfg["perspective_scale"], p=0.6),
        A.GaussianBlur(blur_limit=cfg["gaussian_blur"], p=0.4),
        A.MotionBlur(blur_limit=cfg["motion_blur"], p=0.3),
        A.RandomBrightnessContrast(brightness_limit=cfg["brightness_limit"],
                                   contrast_limit=cfg["contrast_limit"], p=0.6),
        A.ISONoise(color_shift=cfg["isonoise_color_shift"],
                   intensity=cfg["isonoise_intensity"], p=0.4),
        A.LongestMaxSize(max_size=CONFIG["image_size"], p=1.0),
        A.PadIfNeeded(min_height=CONFIG["image_size"], min_width=CONFIG["image_size"],
                      border_mode=cv2.BORDER_CONSTANT, fill=(123, 116, 103)),
    ])

def get_light_aug():
    cfg = CONFIG["light_aug"]
    return A.Compose([
        A.Affine(rotate=cfg["rotate"], p=0.3),
        A.ColorJitter(brightness=cfg["brightness"], contrast=cfg["contrast"],
                      saturation=cfg["saturation"], hue=cfg["hue"], p=0.3),
        A.LongestMaxSize(max_size=CONFIG["image_size"], p=1.0),
        A.PadIfNeeded(min_height=CONFIG["image_size"], min_width=CONFIG["image_size"],
                      border_mode=cv2.BORDER_CONSTANT, fill=(123, 116, 103)),
    ], p=0.3)

def get_eval_preprocess():
    return A.Compose([
        A.LongestMaxSize(max_size=CONFIG["image_size"], p=1.0),
        A.PadIfNeeded(min_height=CONFIG["image_size"], min_width=CONFIG["image_size"],
                      border_mode=cv2.BORDER_CONSTANT, fill=(123, 116, 103)),
    ])

phone_aug = get_phone_style_aug()
light_aug = get_light_aug()
eval_tf = get_eval_preprocess()

def load_rgb(path):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return np.array(img)

def to_tensor(img_np, aug):
    out = aug(image=img_np)["image"]
    pil = Image.fromarray(out)
    return processor(images=pil, return_tensors="pt")["pixel_values"].squeeze(0)

class PairDataset(Dataset):
    def __init__(self, root, split="train"):
        self.root = Path(root)
        self.split = split
        cat = self.root / "catalog" / split
        self.catalog = sorted({
            *cat.rglob("*.webp"), *cat.rglob("*.jpg"),
            *cat.rglob("*.jpeg"), *cat.rglob("*.png"),
        }) if cat.is_dir() else []
        anchor_dir = self.root / "market" / split / "anchor"
        pos_dir = self.root / "market" / split / "positives"
        self.market_pairs = []
        if anchor_dir.is_dir() and pos_dir.is_dir():
            for a in sorted(anchor_dir.iterdir()):
                if a.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                    continue
                hits = list(pos_dir.glob(a.stem + ".*"))
                if hits:
                    self.market_pairs.append((a, hits[0]))
        self.items = [("catalog", p) for p in self.catalog]
        self.items += [("market", i) for i in range(len(self.market_pairs))]
        print(f"[{split}] catalog={len(self.catalog)} market_pairs={len(self.market_pairs)}")

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        kind, ref = self.items[idx]
        if kind == "catalog":
            img = load_rgb(ref)
            # 4th value = gallery filename (for near / hard-neg in Phase 2)
            return to_tensor(img, phone_aug), to_tensor(img, eval_tf), 0, ref.name
        a, p = self.market_pairs[ref]
        return to_tensor(load_rgb(a), light_aug), to_tensor(load_rgb(p), eval_tf), 1, p.name

train_ds = PairDataset(CONFIG["dataset_root"], "train")
val_ds = PairDataset(CONFIG["dataset_root"], "val")

num_catalog = sum(1 for k, _ in train_ds.items if k == "catalog")
num_market = len(train_ds) - num_catalog
weights = []
for kind, _ in train_ds.items:
    if kind == "catalog":
        weights.append((CONFIG["catalog_in_batch"] / CONFIG["batch_size"]) / max(num_catalog, 1))
    else:
        weights.append((CONFIG["market_in_batch"] / CONFIG["batch_size"]) / max(num_market, 1))

sampler = WeightedRandomSampler(weights, num_samples=len(train_ds), replacement=True)
# T4: keep workers low (host RAM). Raise to 2 if stable.
_nw = 1
train_loader = DataLoader(
    train_ds, batch_size=CONFIG["batch_size"], sampler=sampler, num_workers=_nw, pin_memory=True
)
val_loader = DataLoader(
    val_ds, batch_size=CONFIG["batch_size"], shuffle=False, num_workers=_nw, pin_memory=True
)
print(f"dataloaders ready  num_workers={_nw}")
"""
    )
)

cells.append(md("## 2. Model (DINOv2 + LoRA) + checkpoints"))

cells.append(
    code(
        """
from transformers import AutoModel
from peft import LoraConfig, get_peft_model, PeftModel
import torch.nn.functional as F
import json

print(f"Loading {CONFIG['model_name']}...")
model = AutoModel.from_pretrained(CONFIG["model_name"])
model.gradient_checkpointing_enable()

lora_config = LoraConfig(
    r=CONFIG["lora_r"],
    lora_alpha=CONFIG["lora_alpha"],
    lora_dropout=CONFIG["lora_dropout"],
    target_modules=CONFIG["target_modules"],
    bias="none",
    modules_to_save=["pooler"],
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
model = model.to(CONFIG["device"])

optimizer = torch.optim.AdamW(
    model.parameters(), lr=CONFIG["learning_rate"], weight_decay=CONFIG["weight_decay"]
)
scaler = torch.cuda.amp.GradScaler(enabled=(CONFIG["device"] == "cuda"))

def phase_dir(phase: int) -> str:
    return os.path.join(CONFIG["models_path"], f"phase{phase}")

def save_checkpoint(phase, epoch, metrics, is_best=False, tag=None):
    # Save under epoch_N, best_adapter, or an explicit tag (e.g. best_of_phase)
    root = phase_dir(phase)
    os.makedirs(root, exist_ok=True)
    if tag:
        save_dir = os.path.join(root, tag)
    else:
        save_dir = os.path.join(root, "best_adapter" if is_best else f"epoch_{epoch}")
    os.makedirs(save_dir, exist_ok=True)
    model.save_pretrained(save_dir)
    meta = {
        "phase": phase,
        "epoch": epoch,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat(),
        "is_best": is_best,
        "tag": tag or ("best_adapter" if is_best else f"epoch_{epoch}"),
    }
    with open(os.path.join(save_dir, "training_metadata.json"), "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"saved {save_dir}")
    return save_dir

def get_latest_checkpoint(phase: int):
    root = phase_dir(phase)
    if not os.path.isdir(root):
        return None
    epochs = []
    for name in os.listdir(root):
        if name.startswith("epoch_"):
            try:
                epochs.append((int(name.split("_")[1]), os.path.join(root, name)))
            except ValueError:
                pass
    if not epochs:
        best = os.path.join(root, "best_adapter")
        return best if os.path.isdir(best) else None
    epochs.sort(reverse=True)
    return epochs[0][1]

def load_checkpoint(path):
    print(f"load {path}")
    base = AutoModel.from_pretrained(CONFIG["model_name"])
    # CRITICAL: default is_trainable=False freezes LoRA → loss has no grad_fn
    m = PeftModel.from_pretrained(base, path, is_trainable=True)
    m.gradient_checkpointing_enable()
    # Required for LoRA + gradient checkpointing (input embeddings must require grad)
    if hasattr(m, "enable_input_require_grads"):
        m.enable_input_require_grads()
    m = m.to(CONFIG["device"])
    m.train()
    n_train = sum(p.requires_grad for p in m.parameters())
    n_total = sum(1 for _ in m.parameters())
    print(f"trainable tensors: {n_train}/{n_total}")
    assert n_train > 0, "loaded adapter is frozen — pass is_trainable=True"
    with open(os.path.join(path, "training_metadata.json")) as f:
        meta = json.load(f)
    return m, meta

print("model ready")
"""
    )
)

cells.append(
    md(
        """
## 3. Batched catalog index + retrieval

Батч **128** на GPU (fp16). Узкое место обычно **чтение с Drive** → грузим картинки
в батч **параллельно** (ThreadPool), forward на CUDA.

Кэш: `_index/phase{P}/epoch_{E}/catalog.pt`.  
Ячейка Dev-A/B ниже с `force=True` — **разовая**.  
В train-loop эпохи тоже `force=True` (нужен свежий R@5) — поэтому encode должен быть быстрым;
если всё ещё >2–3 мин/эпоху — один раз скопируй `dataset/catalog/train` на локальный диск Colab
(`!cp -r … /content/catalog_train` и поменяй `OWNER_CATALOG`).
"""
    )
)

cells.append(
    code(
        """
from tqdm import tqdm
import csv
from concurrent.futures import ThreadPoolExecutor

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}

def list_images(folder):
    folder = Path(folder)
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in IMG_EXT)

def _prep_one(path):
    return to_tensor(load_rgb(path), eval_tf)

@torch.no_grad()
def encode_paths(model, paths, batch_size=None, desc="encode", num_workers=8):
    # Batched GPU encode; parallel CPU load/preprocess (Drive-friendly).
    batch_size = batch_size or CONFIG["encode_batch_size"]
    model.eval()
    embs = []
    n_workers = min(num_workers, batch_size, 16)
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        for i in tqdm(range(0, len(paths), batch_size), desc=desc):
            chunk = paths[i : i + batch_size]
            tensors = list(pool.map(_prep_one, chunk))
            x = torch.stack(tensors).to(CONFIG["device"], non_blocking=True)
            with torch.cuda.amp.autocast(enabled=(CONFIG["device"] == "cuda"), dtype=torch.float16):
                z = model(pixel_values=x).pooler_output
                z = F.normalize(z.float(), dim=1)
            embs.append(z.cpu())
    return torch.cat(embs, dim=0) if embs else torch.empty(0, model.config.hidden_size)

def build_or_load_catalog_index(model, phase, epoch, force=False):
    out_dir = Path(CONFIG["index_path"]) / f"phase{phase}" / f"epoch_{epoch}"
    out_dir.mkdir(parents=True, exist_ok=True)
    emb_path = out_dir / "catalog.pt"
    ids_path = out_dir / "ids.json"
    paths = list_images(CONFIG["owner_catalog"])
    assert paths, f"owner_catalog empty: {CONFIG['owner_catalog']}"
    if emb_path.is_file() and ids_path.is_file() and not force:
        embs = torch.load(emb_path, map_location="cpu")
        ids = json.loads(ids_path.read_text(encoding="utf-8"))
        print(f"reuse index {emb_path} shape={tuple(embs.shape)}")
        return embs, ids, paths
    print(f"building index n={len(paths)} batch={CONFIG['encode_batch_size']}")
    embs = encode_paths(model, paths, desc=f"catalog e{epoch}")
    ids = [p.name for p in paths]
    torch.save(embs, emb_path)
    ids_path.write_text(json.dumps(ids, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "meta.json").write_text(
        json.dumps({"n": len(ids), "dim": int(embs.shape[1]), "epoch": str(epoch), "phase": phase}),
        encoding="utf-8",
    )
    print(f"index -> {emb_path} {tuple(embs.shape)}")
    return embs, ids, paths

def load_dev_manifest(dev_root):
    root = Path(dev_root)
    man = root / "manifest.tsv"
    rows = []
    if man.is_file():
        with man.open(encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\\t"):
                q = row.get("query_file") or row.get("query") or row.get("file")
                c = row.get("catalog_file") or row.get("catalog") or row.get("gt")
                rows.append((q, c))
    else:
        qdir = root / DEV_QUERIES_SUBDIR if (root / DEV_QUERIES_SUBDIR).is_dir() else root
        for qpath in list_images(qdir):
            rows.append((qpath.name, qpath.name))
    return rows

@torch.no_grad()
def evaluate_retrieval(model, phase, epoch, dev_root, catalog_embs, catalog_ids, topk=5):
    pairs = load_dev_manifest(dev_root)
    id_to_idx = {name: i for i, name in enumerate(catalog_ids)}
    q_root = Path(dev_root)
    q_dir = q_root / DEV_QUERIES_SUBDIR

    q_paths, gt_names = [], []
    for q_name, gt_name in pairs:
        qp = q_dir / q_name
        if not qp.is_file():
            hits = list(q_dir.glob(Path(q_name).stem + ".*"))
            if not hits:
                continue
            qp = hits[0]
        if gt_name not in id_to_idx:
            continue
        q_paths.append(qp)
        gt_names.append(gt_name)

    if not q_paths:
        print("no eval pairs matched catalog ids")
        return {"R@1": 0.0, "R@5": 0.0, "MRR": 0.0, "n": 0}

    q_embs = encode_paths(model, q_paths, desc=f"queries e{epoch}")
    sims = q_embs @ catalog_embs.T
    ranks, hit1, hitk, details = [], 0, 0, []
    for i, gt_name in enumerate(gt_names):
        gt_idx = id_to_idx[gt_name]
        scores = sims[i]
        order = torch.argsort(scores, descending=True)
        rank = int((order == gt_idx).nonzero(as_tuple=True)[0].item()) + 1
        ranks.append(rank)
        hit1 += int(rank == 1)
        hitk += int(rank <= topk)
        details.append({
            "query": q_paths[i].name,
            "gt": gt_name,
            "rank": rank,
            "score_gt": float(scores[gt_idx]),
            "score_top1": float(scores[order[0]]),
            "top": "|".join(catalog_ids[j] for j in order[:topk].tolist()),
        })

    n = len(ranks)
    metrics = {
        "R@1": hit1 / n,
        f"R@{topk}": hitk / n,
        "MRR": float(np.mean([1.0 / r for r in ranks])),
        "median_rank": float(np.median(ranks)),
        "n": n,
    }
    out_csv = Path(CONFIG["logs_path"]) / f"phase{phase}_epoch{epoch}_retrieval.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(details[0].keys()))
        w.writeheader()
        w.writerows(details)
    print(
        f"retrieval n={n} R@1={metrics['R@1']:.3f} R@{topk}={metrics[f'R@{topk}']:.3f} "
        f"MRR={metrics['MRR']:.3f} med_rank={metrics['median_rank']:.1f}"
    )
    print(f"csv -> {out_csv}")
    return metrics

print("index/eval helpers ready")
"""
    )
)

cells.append(
    md(
        """
## 4. Losses

- Phase 1: symmetric InfoNCE (как v1).
- Phase 2: тот же цикл + near_groups на Drive; hard-FAR miner — следующий итерационный шаг после ручной проверки Phase 1.
"""
    )
)

cells.append(
    code(
        """
def info_nce(z_q, z_g, temperature=None):
    temperature = temperature or CONFIG["temperature"]
    z_q = F.normalize(z_q, dim=1)
    z_g = F.normalize(z_g, dim=1)
    logits = (z_q @ z_g.T) / temperature
    labels = torch.arange(logits.shape[0], device=logits.device)
    return 0.5 * (F.cross_entropy(logits, labels) + F.cross_entropy(logits.T, labels))

def load_near_group_map(path):
    if not path or not os.path.isfile(path):
        return {}
    m = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("kind") == "cluster":
                m[row["file"]] = row["group_id"]
    print(f"near map entries={len(m)} from {path}")
    return m

@torch.no_grad()
def validate_loss(model, loader):
    model.eval()
    total, n = 0.0, 0
    for batch in loader:
        queries, galleries = batch[0], batch[1]
        queries = queries.to(CONFIG["device"])
        galleries = galleries.to(CONFIG["device"])
        with torch.cuda.amp.autocast(enabled=(CONFIG["device"] == "cuda"), dtype=torch.float16):
            loss = info_nce(
                model(pixel_values=queries).pooler_output,
                model(pixel_values=galleries).pooler_output,
            )
        total += float(loss.item())
        n += 1
        if n >= 20:
            break
    return total / max(n, 1)

print("losses ready")
"""
    )
)

cells.append(
    md(
        """
## 5. Phase 1 — training loop

После каждой эпохи: checkpoint → **batched** index → retrieval Dev-A → best по **R@5**.
"""
    )
)

cells.append(
    code(
        """
import time

if PHASE != 1:
    print(f"Skip Phase 1 train (PHASE={PHASE})")
else:
    start_epoch = 0
    best_r5 = -1.0
    training_log = []

    if RESUME:
        latest = get_latest_checkpoint(1)
        if latest:
            model, meta = load_checkpoint(latest)
            start_epoch = int(meta.get("epoch", 0))
            best_r5 = float(meta.get("metrics", {}).get("R@5", -1))
            optimizer = torch.optim.AdamW(
                model.parameters(), lr=CONFIG["learning_rate"], weight_decay=CONFIG["weight_decay"]
            )
            print(f"resume phase1 from epoch {start_epoch}, best R@5={best_r5:.3f}")

    print("=" * 60)
    print(f"PHASE 1 TRAIN  epochs {start_epoch+1}..{CONFIG['phase1_epochs']}")
    print("=" * 60)

    for epoch in range(start_epoch, CONFIG["phase1_epochs"]):
        model.train()
        running, nb = 0.0, 0
        t0 = time.time()
        pbar = tqdm(train_loader, desc=f"P1 ep {epoch+1}/{CONFIG['phase1_epochs']}")
        for batch in pbar:
            queries, galleries = batch[0], batch[1]
            queries = queries.to(CONFIG["device"], non_blocking=True)
            galleries = galleries.to(CONFIG["device"], non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=(CONFIG["device"] == "cuda"), dtype=torch.float16):
                loss = info_nce(
                    model(pixel_values=queries).pooler_output,
                    model(pixel_values=galleries).pooler_output,
                )
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            running += float(loss.item())
            nb += 1
            pbar.set_postfix(loss=f"{running/nb:.4f}")

        train_loss = running / max(nb, 1)
        val_loss = validate_loss(model, val_loader)
        metrics = {"train_loss": train_loss, "val_loss": val_loss, "time_sec": time.time() - t0}

        if CONFIG["eval_every_epoch"]:
            cat_embs, cat_ids, _ = build_or_load_catalog_index(model, phase=1, epoch=epoch + 1, force=True)
            ret = evaluate_retrieval(
                model, 1, epoch + 1, CONFIG["dev_a"], cat_embs, cat_ids, topk=CONFIG["eval_topk"]
            )
            metrics.update(ret)
        else:
            metrics["R@5"] = -1.0

        is_best = metrics.get("R@5", -1) > best_r5
        if is_best:
            best_r5 = metrics["R@5"]
        save_checkpoint(1, epoch + 1, metrics, is_best=False)
        if is_best:
            save_checkpoint(1, epoch + 1, metrics, is_best=True)

        training_log.append({"epoch": epoch + 1, **metrics, "is_best": is_best})
        Path(LOGS_PATH, "phase1_log.json").write_text(
            json.dumps(training_log, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        r5 = float(metrics.get("R@5", float("nan")))
        base_same = BASE_P1_R5.get(epoch + 1)
        delta = (r5 - base_same) if base_same is not None else float("nan")
        print(
            f"P1 epoch {epoch+1}: loss={train_loss:.4f} val={val_loss:.4f} "
            f"R@5={r5:.3f} best={is_best} | vs base@ep={base_same} Δ={delta:+.3f}"
        )
        if epoch + 1 in (3, 4) and base_same is not None:
            if r5 + 1e-9 < base_same - 0.05:
                print(
                    "  NOTE: Large trailing base by >5pp at this epoch — "
                    "still finish planned P1 epochs; Phase3 optional if best looks sane."
                )
            elif r5 + 1e-9 >= base_same:
                print(
                    "  NOTE: Large ≥ base at same epoch — good early signal; "
                    "finish P1 then try Phase3 for drop-test."
                )

    print("Phase 1 done. best R@5=", best_r5, "| base M1=", BASE_M1_R5, "| base@ep6=", BASE_P1_R5.get(6))
    print(
        "Next: §5.1 gate cell → then PHASE=3 / STOP_AFTER_PHASE1=False "
        "(skip Phase2). Absolute ceiling vs 0.852 can wait."
    )
    if best_r5 + 1e-9 >= BASE_P1_R5.get(CONFIG["phase1_epochs"], 0):
        print("P1 vs base@same horizon: Large ≥ base — proceed to Phase3 drop-test.")
    else:
        print(
            "P1 vs base@same horizon: Large < base — Phase3 still OK for drop-test, "
            "but do not read a Phase3 failure as 'Large lacks capacity'."
        )
"""
    )
)

cells.append(
    md(
        """
## 5.1 After Phase1 — then Phase3 drop-test

1. Note Large best R@5 (of 6 ep) and Δ vs `BASE_P1_R5[ep]` / base@ep6=0.778 / base M1=0.852.
2. Deep misses: `2039dd8a`, `7bf0507b` in `_logs_v4_large/`.
3. **Go to Phase3** (skip Phase2): set `PHASE=3`, `STOP_AFTER_PHASE1=False`, re-run control cell + §7.
4. Drop-test pass: Phase3 best ≥ Large P1 best (no hit loss). Fail: same −1/−2 hit pattern as base.

Ceiling vs 0.852 = later run (`phase1_epochs=8`) if drop-test is interesting.
"""
    )
)

cells.append(
    code(
        """
best1 = os.path.join(phase_dir(1), "best_adapter")
assert os.path.isdir(best1), f"missing {best1}"
model, meta = load_checkpoint(best1)
ep = int(meta.get("epoch", 0))
r5 = float(meta.get("metrics", {}).get("R@5", -1))
cat_embs, cat_ids, _ = build_or_load_catalog_index(model, phase=1, epoch=f"best_{ep}", force=True)

print("Dev-A:")
ret_a = evaluate_retrieval(model, 1, f"bestA_{ep}", CONFIG["dev_a"], cat_embs, cat_ids, topk=CONFIG["eval_topk"])
print("Dev-B:")
ret_b = evaluate_retrieval(model, 1, f"bestB_{ep}", CONFIG["dev_b"], cat_embs, cat_ids, topk=CONFIG["eval_topk"])

print("--- after short P1 ---")
print(f"Large best ep={ep} R@5={r5:.4f}  base@ep{ep}={BASE_P1_R5.get(ep)}  base M1={BASE_M1_R5:.4f}")
print(f"Dev-A re-eval R@5={ret_a.get('R@5')}  Dev-B R@5={ret_b.get('R@5')}")
print("→ Next: PHASE=3, STOP_AFTER_PHASE1=False (skip Phase2). Drop-test vs this Large P1 best.")
if r5 + 1e-9 < BASE_M1_R5:
    print("(R@5 still below base M1 0.852 — expected with 6 ep; not a Phase3 blocker.)")

if STOP_AFTER_PHASE1:
    print("\\nSTOP_AFTER_PHASE1=True — pause; change PHASE then continue.")
else:
    print("STOP_AFTER_PHASE1=False — continue if PHASE=3 cell enabled.")
"""
    )
)

cells.append(
    md(
        """
## 6. Phase 2 — hard-FAR negatives (near graph)

Старт с `phase1/best_adapter`. Нужен `near/near_groups.csv`.

Алгоритм:
1. Берём индекс M1 (или пересобираем).
2. Для каждого catalog SKU — top-30 соседей **минус** same near-group → hard-FAR pool.
3. Loss = InfoNCE(q, g) + 0.5 * hard-pair CE (положительный g vs hard-neg h).
"""
    )
)

cells.append(
    code(
        """
import random

if PHASE != 2:
    print(f"Skip Phase 2 (PHASE={PHASE}). Set PHASE=2 to run.")
else:
    assert not STOP_AFTER_PHASE1, "Set STOP_AFTER_PHASE1=False before Phase 2"
    near_map = load_near_group_map(CONFIG["near_groups"])
    assert near_map, f"near_groups empty/missing: {CONFIG['near_groups']}"
    print(f"near groups loaded: {len(near_map)} files with cluster group")

    best1 = os.path.join(phase_dir(1), "best_adapter")
    model, meta = load_checkpoint(best1)
    ep1 = int(meta.get("epoch", 0))

    # --- build hard-FAR pools from Phase-1 index ---
    cat_embs, cat_ids, cat_paths = build_or_load_catalog_index(
        model, phase=1, epoch=f"best_{ep1}", force=False
    )
    if cat_embs is None or cat_embs.numel() == 0:
        cat_embs, cat_ids, cat_paths = build_or_load_catalog_index(
            model, phase=1, epoch=f"best_{ep1}", force=True
        )
    id_to_idx = {n: i for i, n in enumerate(cat_ids)}
    id_to_path = {p.name: p for p in cat_paths}

    TOPK_HARD = 30
    hard_pools = {}  # filename -> list[filename]
    sims = cat_embs @ cat_embs.T
    for i, name in enumerate(cat_ids):
        g_i = near_map.get(name)
        order = torch.argsort(sims[i], descending=True)
        pool = []
        for j in order.tolist():
            if j == i:
                continue
            other = cat_ids[j]
            g_j = near_map.get(other)
            # exclude same near-group (and self); allow if either has no group
            if g_i and g_j and g_i == g_j:
                continue
            pool.append(other)
            if len(pool) >= TOPK_HARD:
                break
        hard_pools[name] = pool
    n_with = sum(1 for v in hard_pools.values() if v)
    print(f"hard-FAR pools: {n_with}/{len(hard_pools)} non-empty (topk={TOPK_HARD})")

    # encode_paths leaves model.eval(); restore train + input grads after index
    model.train()
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()
    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=CONFIG["learning_rate"] * 0.5,
        weight_decay=CONFIG["weight_decay"],
    )
    scaler = torch.cuda.amp.GradScaler(enabled=(CONFIG["device"] == "cuda"))

    def sample_hard_batch(names):
        paths = []
        mask = []
        for name in names:
            pool = hard_pools.get(name) or []
            if not pool:
                # fallback: random other catalog file
                alt = random.choice(cat_ids)
                while alt == name and len(cat_ids) > 1:
                    alt = random.choice(cat_ids)
                paths.append(id_to_path[alt])
                mask.append(0.0)  # don't train hard loss if no real pool
            else:
                paths.append(id_to_path[random.choice(pool)])
                mask.append(1.0)
        return paths, torch.tensor(mask, device=CONFIG["device"])

    def hard_pair_loss(z_q, z_g, z_h, mask, temperature=None):
        temperature = temperature or CONFIG["temperature"]
        z_q = F.normalize(z_q, dim=1)
        z_g = F.normalize(z_g, dim=1)
        z_h = F.normalize(z_h, dim=1)
        pos = (z_q * z_g).sum(dim=1, keepdim=True)
        neg = (z_q * z_h).sum(dim=1, keepdim=True)
        logits = torch.cat([pos, neg], dim=1) / temperature
        labels = torch.zeros(logits.size(0), dtype=torch.long, device=logits.device)
        per = F.cross_entropy(logits, labels, reduction="none")
        m = mask.to(per.dtype)
        if float(m.sum().item()) < 1.0:
            # keep graph connected for GradScaler/backward
            return z_q.sum() * 0.0
        return (per * m).sum() / m.sum()

    start_epoch = 0
    # best WITHIN this phase → phase2/best_adapter (even if worse than M1).
    # Global pick M1 vs M2 is a separate step after training.
    best_r5 = -1.0
    best_epoch = None
    baseline_r5 = float(meta.get("metrics", {}).get("R@5", -1.0))
    print(f"Phase2 start from M1 epoch={ep1} baseline R@5={baseline_r5:.4f} (info only)")
    training_log = []
    if RESUME:
        latest = get_latest_checkpoint(2)
        if latest:
            model, meta = load_checkpoint(latest)
            start_epoch = int(meta.get("epoch", 0))
            best_r5 = float(meta.get("metrics", {}).get("R@5", -1))
            best_epoch = start_epoch if best_r5 >= 0 else None
            model.train()
            if hasattr(model, "enable_input_require_grads"):
                model.enable_input_require_grads()
            optimizer = torch.optim.AdamW(
                filter(lambda p: p.requires_grad, model.parameters()),
                lr=CONFIG["learning_rate"] * 0.5,
                weight_decay=CONFIG["weight_decay"],
            )
            print(f"resume phase2 from epoch {start_epoch}, best_of_phase R@5={best_r5:.3f}")

    HARD_LOSS_W = 0.5
    print("=" * 60)
    print(f"PHASE 2 TRAIN  epochs {start_epoch+1}..{CONFIG['phase2_epochs']}  hard_w={HARD_LOSS_W}")
    print(f"  best_adapter = best WITHIN phase2; compare to M1 only after train")
    print("=" * 60)

    for epoch in range(start_epoch, CONFIG["phase2_epochs"]):
        model.train()
        running, running_h, nb = 0.0, 0.0, 0
        t0 = time.time()
        pbar = tqdm(train_loader, desc=f"P2 ep {epoch+1}/{CONFIG['phase2_epochs']}")
        for batch in pbar:
            queries, galleries, types, names = batch[0], batch[1], batch[2], batch[3]
            queries = queries.to(CONFIG["device"], non_blocking=True)
            galleries = galleries.to(CONFIG["device"], non_blocking=True)
            hard_paths, hard_mask = sample_hard_batch(list(names))
            hard_tensors = torch.stack(
                [to_tensor(load_rgb(p), eval_tf) for p in hard_paths]
            ).to(CONFIG["device"], non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=(CONFIG["device"] == "cuda"), dtype=torch.float16):
                z_q = model(pixel_values=queries).pooler_output
                z_g = model(pixel_values=galleries).pooler_output
                z_h = model(pixel_values=hard_tensors).pooler_output
                loss_main = info_nce(z_q, z_g)
                loss_h = hard_pair_loss(z_q, z_g, z_h, hard_mask)
                loss = loss_main + HARD_LOSS_W * loss_h
            if not loss.requires_grad:
                raise RuntimeError(
                    "loss has no grad — adapter frozen? "
                    "reload with PeftModel.from_pretrained(..., is_trainable=True)"
                )
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            running += float(loss_main.item())
            running_h += float(loss_h.item())
            nb += 1
            pbar.set_postfix(nce=f"{running/nb:.4f}", hard=f"{running_h/nb:.4f}")

        train_loss = running / max(nb, 1)
        val_loss = validate_loss(model, val_loader)
        metrics = {
            "train_loss": train_loss,
            "hard_loss": running_h / max(nb, 1),
            "val_loss": val_loss,
            "time_sec": time.time() - t0,
            "baseline_r5": baseline_r5,
        }
        cat_embs, cat_ids, _ = build_or_load_catalog_index(model, phase=2, epoch=epoch + 1, force=True)
        ret = evaluate_retrieval(
            model, 2, epoch + 1, CONFIG["dev_a"], cat_embs, cat_ids, topk=CONFIG["eval_topk"]
        )
        metrics.update(ret)
        r5 = float(metrics.get("R@5", -1))

        # always keep epoch_N
        save_checkpoint(2, epoch + 1, metrics, is_best=False)

        # best WITHIN phase → best_adapter (+ alias best_of_phase)
        is_best_of_phase = r5 > best_r5
        beats_baseline = r5 > baseline_r5
        if is_best_of_phase:
            best_r5 = r5
            best_epoch = epoch + 1
            save_checkpoint(
                2, epoch + 1,
                {**metrics, "is_best": True, "is_best_of_phase": True, "beats_baseline": beats_baseline},
                is_best=True,
            )
            save_checkpoint(
                2, epoch + 1,
                {**metrics, "is_best_of_phase": True, "beats_baseline": beats_baseline},
                tag="best_of_phase",
            )
            print(
                f"  → phase2 best_adapter updated ep={best_epoch} R@5={best_r5:.4f} "
                f"(vs M1 {baseline_r5:.4f}: {'UP' if beats_baseline else 'DOWN/TIED'})"
            )

        # refresh hard pools
        sims = cat_embs @ cat_embs.T
        for i, name in enumerate(cat_ids):
            g_i = near_map.get(name)
            order = torch.argsort(sims[i], descending=True)
            pool = []
            for j in order.tolist():
                if j == i:
                    continue
                other = cat_ids[j]
                g_j = near_map.get(other)
                if g_i and g_j and g_i == g_j:
                    continue
                pool.append(other)
                if len(pool) >= TOPK_HARD:
                    break
            hard_pools[name] = pool

        training_log.append({
            "epoch": epoch + 1,
            **metrics,
            "is_best_of_phase": is_best_of_phase,
            "beats_baseline": beats_baseline,
        })
        Path(LOGS_PATH, "phase2_log.json").write_text(
            json.dumps(training_log, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(
            f"P2 epoch {epoch+1}: R@5={r5:.3f} R@1={metrics.get('R@1', float('nan')):.3f} "
            f"best_of_phase={is_best_of_phase} vs_M1={'UP' if beats_baseline else 'DOWN'}"
        )

    print("Phase 2 done. best_of_phase R@5=", best_r5, "ep=", best_epoch)
    print("M1 baseline R@5=", baseline_r5, "| global pick: compare phase1/best vs phase2/best manually")
"""
    )
)

cells.append(
    md(
        """
## 7. Phase 3b — InfoNCE + hierarchical margin (from **Large** short-P1 best)

**Drop-test after §5.1.** Skip Phase2.  
**Start:** `_models_v4_large/phase1/best_adapter`. Baseline = this Large P1 best (from metadata).  
Pass = Phase3 does not lose hits vs that baseline.

**Start:** `phase1/best_adapter` only. No hard-CE.

**Attempts** (`ATTEMPT_ID`): fixed margin sets — change ID and re-run from M1 (do not continue failed attempt weights).

| ID | m_near | m_sw | m_far | λ |
|----|--------|------|-------|---|
| A | 0.04 | 0.11 | 0.18 | 0.15 |
| B | 0.03 | 0.08 | 0.14 | 0.10 |
| C | 0.05 | 0.12 | 0.22 | 0.20 |

**Schedule:** pool block = 4 epochs (same N2 ids); if R@5 rises → remine and continue up to soft-cap 12; if first block flat vs M1 → stop and try next attempt.

Need on Drive: `near/near_groups.csv` (from `scripts/build_margin_tiers.py --scan`).
"""
    )
)

cells.append(
    code(
        r'''
import random
import time

MARGIN_SETS = {
    "A": {"m_near": 0.04, "m_sw": 0.11, "m_far": 0.18, "lam": 0.15},
    "B": {"m_near": 0.03, "m_sw": 0.08, "m_far": 0.14, "lam": 0.10},
    "C": {"m_near": 0.05, "m_sw": 0.12, "m_far": 0.22, "lam": 0.20},
}

if PHASE != 3:
    print(f"Skip Phase 3 (PHASE={PHASE}). Set PHASE=3 to run.")
else:
    assert ATTEMPT_ID in MARGIN_SETS, f"ATTEMPT_ID must be one of {list(MARGIN_SETS)}"
    margins = MARGIN_SETS[ATTEMPT_ID]
    POOL_BLOCK = int(CONFIG["phase3_pool_block"])
    SOFT_CAP = int(CONFIG["phase3_soft_cap"])
    TOPK_HARD = int(CONFIG["phase3_topk_hard"])
    SEMI_HARD = float(CONFIG["phase3_semi_hard"])
    LR3 = float(CONFIG["phase3_lr"])

    def load_near_meta(path):
        """file -> {group_id, winery, kind}; group lists for sampling."""
        file_meta = {}
        by_group = {}
        by_winery = {}
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                fn = row["file"]
                file_meta[fn] = {
                    "group_id": row["group_id"],
                    "winery": row["winery"],
                    "kind": row.get("kind", ""),
                }
                by_group.setdefault(row["group_id"], []).append(fn)
                by_winery.setdefault(row["winery"], []).append(fn)
        near_mates = {}
        sw_mates = {}
        for fn, meta in file_meta.items():
            gid, winery, kind = meta["group_id"], meta["winery"], meta["kind"]
            gfiles = by_group.get(gid, [])
            if kind == "cluster" and len(gfiles) > 1:
                near_mates[fn] = [x for x in gfiles if x != fn]
            else:
                near_mates[fn] = []
            sw_mates[fn] = [
                x for x in by_winery.get(winery, [])
                if x != fn and file_meta[x]["group_id"] != gid
            ]
        print(
            f"near_meta files={len(file_meta)} "
            f"with_near={sum(1 for v in near_mates.values() if v)} "
            f"with_sw={sum(1 for v in sw_mates.values() if v)}"
        )
        return file_meta, near_mates, sw_mates

    file_meta, near_mates, sw_mates = load_near_meta(CONFIG["near_groups"])
    assert file_meta, f"near_groups empty/missing: {CONFIG['near_groups']}"

    best1 = os.path.join(phase_dir(1), "best_adapter")
    model, meta = load_checkpoint(best1)
    ep1 = int(meta.get("epoch", 0))
    baseline_r5 = float(meta.get("metrics", {}).get("R@5", -1.0))
    print(f"Phase3b attempt={ATTEMPT_ID} margins={margins}")
    print(f"Start M1 epoch={ep1} baseline R@5={baseline_r5:.4f}")

    # --- index for first mine: M1 (frozen snapshot for block 1) ---
    cat_embs, cat_ids, cat_paths = build_or_load_catalog_index(
        model, phase=1, epoch=f"best_{ep1}", force=False
    )
    if cat_embs is None or cat_embs.numel() == 0:
        cat_embs, cat_ids, cat_paths = build_or_load_catalog_index(
            model, phase=1, epoch=f"best_{ep1}", force=True
        )
    id_to_path = {p.name: p for p in cat_paths}
    cat_id_set = set(cat_ids)

    def mine_far_pools(embs, ids):
        """N2: top-K cosine, exclude near + same-winery, semi-hard vs self-sim."""
        pools = {}
        sims = embs @ embs.T
        for i, name in enumerate(ids):
            meta_i = file_meta.get(name, {})
            gid_i = meta_i.get("group_id")
            win_i = meta_i.get("winery")
            self_sim = float(sims[i, i].item())
            order = torch.argsort(sims[i], descending=True)
            pool = []
            for j in order.tolist():
                if j == i:
                    continue
                other = ids[j]
                s = float(sims[i, j].item())
                if s >= SEMI_HARD * self_sim:
                    continue
                mo = file_meta.get(other, {})
                if gid_i and mo.get("group_id") == gid_i:
                    continue
                if win_i and mo.get("winery") == win_i:
                    continue
                pool.append(other)
                if len(pool) >= TOPK_HARD:
                    break
            pools[name] = pool
        n_ok = sum(1 for v in pools.values() if v)
        print(f"far pools: {n_ok}/{len(pools)} non-empty topk={TOPK_HARD}")
        return pools

    far_pools = mine_far_pools(cat_embs, cat_ids)

    model.train()
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()
    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LR3,
        weight_decay=CONFIG["weight_decay"],
    )
    scaler = torch.cuda.amp.GradScaler(enabled=(CONFIG["device"] == "cuda"))

    def _pick_path(name, pool):
        if not pool:
            return None, 0.0
        choice = random.choice(pool)
        p = id_to_path.get(choice)
        if p is None:
            return None, 0.0
        return p, 1.0

    def sample_tier_batch(names):
        near_paths, near_m = [], []
        sw_paths, sw_m = [], []
        far_paths, far_m = [], []
        for name in names:
            # fallback path = gallery itself (masked out) so stack always works
            fallback = id_to_path.get(name) or cat_paths[0]
            pn, mn = _pick_path(name, near_mates.get(name, []))
            near_paths.append(pn or fallback)
            near_m.append(mn)
            ps, ms = _pick_path(name, sw_mates.get(name, []))
            sw_paths.append(ps or fallback)
            sw_m.append(ms)
            pf, mf = _pick_path(name, far_pools.get(name, []))
            far_paths.append(pf or fallback)
            far_m.append(mf)
        def stack(paths):
            return torch.stack([to_tensor(load_rgb(p), eval_tf) for p in paths]).to(
                CONFIG["device"], non_blocking=True
            )
        return (
            stack(near_paths),
            torch.tensor(near_m, device=CONFIG["device"]),
            stack(sw_paths),
            torch.tensor(sw_m, device=CONFIG["device"]),
            stack(far_paths),
            torch.tensor(far_m, device=CONFIG["device"]),
        )

    def hinge_tier(z_q, z_g, z_neg, mask, m):
        z_q = F.normalize(z_q, dim=1)
        z_g = F.normalize(z_g, dim=1)
        z_neg = F.normalize(z_neg, dim=1)
        sim_pos = (z_q * z_g).sum(dim=1)
        sim_neg = (z_q * z_neg).sum(dim=1)
        per = torch.relu(sim_neg - sim_pos + m)
        mk = mask.to(per.dtype)
        if float(mk.sum().item()) < 1.0:
            return z_q.sum() * 0.0, 0.0, 0.0
        loss = (per * mk).sum() / mk.sum()
        active = float(((per > 0) & (mk > 0)).sum().item()) / max(float(mk.sum().item()), 1.0)
        mean_gap = float(((sim_pos - sim_neg) * mk).sum().item() / max(float(mk.sum().item()), 1.0))
        return loss, active, mean_gap

    start_epoch = 0
    best_r5 = -1.0
    best_epoch = None
    r5_history = []
    best_at_block_start = baseline_r5
    training_log = []

    if RESUME:
        latest = get_latest_checkpoint(3)
        if latest:
            model, meta_r = load_checkpoint(latest)
            start_epoch = int(meta_r.get("epoch", 0))
            best_r5 = float(meta_r.get("metrics", {}).get("R@5", -1))
            best_epoch = start_epoch if best_r5 >= 0 else None
            model.train()
            if hasattr(model, "enable_input_require_grads"):
                model.enable_input_require_grads()
            optimizer = torch.optim.AdamW(
                filter(lambda p: p.requires_grad, model.parameters()),
                lr=LR3,
                weight_decay=CONFIG["weight_decay"],
            )
            print(f"resume phase3 from epoch {start_epoch}, best_of_phase R@5={best_r5:.3f}")

    print("=" * 60)
    print(
        f"PHASE 3b TRAIN attempt={ATTEMPT_ID} epochs {start_epoch+1}..{SOFT_CAP} "
        f"block={POOL_BLOCK} lr={LR3} lam={margins['lam']}"
    )
    print("=" * 60)

    stop_reason = None
    for epoch in range(start_epoch, SOFT_CAP):
        model.train()
        running_nce, running_h, nb = 0.0, 0.0, 0
        sum_act_n, sum_act_s, sum_act_f = 0.0, 0.0, 0.0
        sum_gap_f = 0.0
        t0 = time.time()
        pbar = tqdm(train_loader, desc=f"P3 {ATTEMPT_ID} ep {epoch+1}/{SOFT_CAP}")
        for batch in pbar:
            queries, galleries, types, names = batch[0], batch[1], batch[2], batch[3]
            names = list(names)
            queries = queries.to(CONFIG["device"], non_blocking=True)
            galleries = galleries.to(CONFIG["device"], non_blocking=True)
            zn, mn, zs, ms, zf, mf = sample_tier_batch(names)

            optimizer.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=(CONFIG["device"] == "cuda"), dtype=torch.float16):
                z_q = model(pixel_values=queries).pooler_output
                z_g = model(pixel_values=galleries).pooler_output
                z_near = model(pixel_values=zn).pooler_output
                z_sw = model(pixel_values=zs).pooler_output
                z_far = model(pixel_values=zf).pooler_output
                loss_nce = info_nce(z_q, z_g)
                h_n, a_n, _ = hinge_tier(z_q, z_g, z_near, mn, margins["m_near"])
                h_s, a_s, _ = hinge_tier(z_q, z_g, z_sw, ms, margins["m_sw"])
                h_f, a_f, gap_f = hinge_tier(z_q, z_g, z_far, mf, margins["m_far"])
                loss_h = h_n + h_s + h_f
                loss = loss_nce + margins["lam"] * loss_h
            if not loss.requires_grad:
                raise RuntimeError(
                    "loss has no grad — adapter frozen? "
                    "reload with PeftModel.from_pretrained(..., is_trainable=True)"
                )
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            running_nce += float(loss_nce.item())
            running_h += float(loss_h.item())
            sum_act_n += a_n
            sum_act_s += a_s
            sum_act_f += a_f
            sum_gap_f += gap_f
            nb += 1
            pbar.set_postfix(nce=f"{running_nce/nb:.4f}", h=f"{running_h/nb:.4f}")

        train_nce = running_nce / max(nb, 1)
        train_h = running_h / max(nb, 1)
        val_loss = validate_loss(model, val_loader)
        metrics = {
            "attempt": ATTEMPT_ID,
            "margins": margins,
            "train_nce": train_nce,
            "train_hinge": train_h,
            "hinge_active_near": sum_act_n / max(nb, 1),
            "hinge_active_sw": sum_act_s / max(nb, 1),
            "hinge_active_far": sum_act_f / max(nb, 1),
            "mean_gap_far": sum_gap_f / max(nb, 1),
            "val_loss": val_loss,
            "time_sec": time.time() - t0,
            "baseline_r5": baseline_r5,
        }
        cat_embs, cat_ids, cat_paths = build_or_load_catalog_index(
            model, phase=3, epoch=epoch + 1, force=True
        )
        id_to_path = {p.name: p for p in cat_paths}
        ret = evaluate_retrieval(
            model, 3, epoch + 1, CONFIG["dev_a"], cat_embs, cat_ids, topk=CONFIG["eval_topk"]
        )
        metrics.update(ret)
        r5 = float(metrics.get("R@5", -1))
        r5_history.append(r5)

        save_checkpoint(3, epoch + 1, metrics, is_best=False)
        is_best_of_phase = r5 > best_r5
        beats_baseline = r5 > baseline_r5
        if is_best_of_phase:
            best_r5 = r5
            best_epoch = epoch + 1
            save_checkpoint(
                3, epoch + 1,
                {
                    **metrics,
                    "is_best": True,
                    "is_best_of_phase": True,
                    "beats_baseline": beats_baseline,
                    "attempt": ATTEMPT_ID,
                },
                is_best=True,
            )
            save_checkpoint(
                3, epoch + 1,
                {**metrics, "is_best_of_phase": True, "beats_baseline": beats_baseline},
                tag=f"best_of_phase_{ATTEMPT_ID}",
            )
            print(
                f"  → phase3 best_adapter ep={best_epoch} R@5={best_r5:.4f} "
                f"(vs M1 {baseline_r5:.4f}: {'UP' if beats_baseline else 'DOWN/TIED'})"
            )

        training_log.append({
            "epoch": epoch + 1,
            **{k: v for k, v in metrics.items() if k != "margins"},
            "margins": margins,
            "is_best_of_phase": is_best_of_phase,
            "beats_baseline": beats_baseline,
        })
        Path(LOGS_PATH, f"phase3_attempt{ATTEMPT_ID}_log.json").write_text(
            json.dumps(training_log, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(
            f"P3 {ATTEMPT_ID} ep{epoch+1}: R@5={r5:.3f} R@1={metrics.get('R@1', float('nan')):.3f} "
            f"hinge_act far={metrics['hinge_active_far']:.2f} gap_far={metrics['mean_gap_far']:.3f}"
        )

        # end of pool block?
        if (epoch + 1) % POOL_BLOCK == 0:
            block_r5 = r5_history[-POOL_BLOCK:]
            block_best = max(block_r5)
            print(
                f"  block end ep{epoch+1}: block_best={block_best:.4f} "
                f"best_of_phase={best_r5:.4f} baseline={baseline_r5:.4f}"
            )
            if (epoch + 1) == POOL_BLOCK:
                # first block: must show growth vs M1 or within-block rise
                if block_best <= baseline_r5 and block_r5[-1] <= block_r5[0] + 1e-9:
                    stop_reason = "first_block_flat"
                    print("  STOP: first block flat vs M1 — try next ATTEMPT_ID from M1")
                    break
            else:
                if block_best <= best_at_block_start + 1e-9:
                    stop_reason = "plateau"
                    print("  STOP: plateau after remine block")
                    break
            # continue: remine from current index
            best_at_block_start = best_r5
            far_pools = mine_far_pools(cat_embs, cat_ids)
            print("  remine far pools for next block")

    print(
        f"Phase 3b done attempt={ATTEMPT_ID} best_of_phase R@5={best_r5} ep={best_epoch} "
        f"stop={stop_reason or 'soft_cap_or_end'}"
    )
    print(f"M1 baseline R@5={baseline_r5} | global pick: compare phase1/best vs phase3/best")
'''
    )
)

cells.append(
    md(
        """
## 8. Export ONNX (Large Phase1 / optional Phase3)

В Colab: merge LoRA → ONNX.  
Выход: `pooler_output` **`[B,1024]`** (DINOv2-large), не 768 как у base.  
Production `DinoOnnxEncoder` для base **не** подхватит — отдельный артефакт / адаптер.

Файлы: `_models_v4_large/dinov2_large_wine_phase1.onnx` (и phase3 если был).
"""
    )
)

cells.append(
    code(
        """
EXPORT = True  # False чтобы пропустить
EXPORT_ADAPTERS = [
    ("phase1", os.path.join(phase_dir(1), "best_adapter")),
    ("phase3", os.path.join(phase_dir(3), "best_adapter")),
    ("phase3_attempt", os.path.join(phase_dir(3), f"best_of_phase_{ATTEMPT_ID}")),
]

class WrapPooler(torch.nn.Module):
    # Raw pooler_output — dim = model.config.hidden_size (1024 for large)
    def __init__(self, m):
        super().__init__()
        self.m = m
    def forward(self, pixel_values):
        return self.m(pixel_values=pixel_values).pooler_output

if not EXPORT:
    print("EXPORT=False — skip")
else:
    dummy = torch.randn(1, 3, CONFIG["image_size"], CONFIG["image_size"])
    exported = []
    for tag, adapter in EXPORT_ADAPTERS:
        if not os.path.isdir(adapter):
            print(f"skip {tag}: missing {adapter}")
            continue
        meta_path = os.path.join(adapter, "training_metadata.json")
        meta_ex = {}
        if os.path.isfile(meta_path):
            with open(meta_path) as f:
                meta_ex = json.load(f)
        print(
            f"export {tag} from {adapter} | "
            f"epoch={meta_ex.get('epoch')} "
            f"R@5={meta_ex.get('metrics', {}).get('R@5')} "
            f"tag={meta_ex.get('tag')}"
        )
        base = AutoModel.from_pretrained(CONFIG["model_name"])
        m = PeftModel.from_pretrained(base, adapter)
        merged = m.merge_and_unload().cpu().eval()
        out_dir = os.path.join(MODELS_PATH, f"merged_{tag}")
        os.makedirs(out_dir, exist_ok=True)
        merged.save_pretrained(out_dir)
        processor.save_pretrained(out_dir)

        onnx_path = os.path.join(MODELS_PATH, f"dinov2_large_wine_{tag}.onnx")
        torch.onnx.export(
            WrapPooler(merged),
            dummy,
            onnx_path,
            input_names=["pixel_values"],
            output_names=["pooler_output"],
            opset_version=17,
            dynamo=False,  # legacy path; avoids onnxscript on Colab
            dynamic_axes={"pixel_values": {0: "B"}, "pooler_output": {0: "B"}},
        )
        sz = os.path.getsize(onnx_path) / (1024 * 1024)
        print(f"ONNX -> {onnx_path}  ({sz:.1f} MB)  hidden={merged.config.hidden_size}")
        exported.append(onnx_path)
        del base, m, merged
        torch.cuda.empty_cache() if CONFIG["device"] == "cuda" else None

    print("done:", exported)
    print("Скачай с Drive, например:")
    print("  bin/dinov2_large_wine_phase1.onnx")
"""
    )
)

cells.append(
    md(
        """
## Drive layout (v4 large @ T4)

```
2_embed_train_data/
  dataset/…  dev_a/…  near/…     # shared with v3
  _models_v4_large/phase{1,3}/
  _index_v4_large/
  _logs_v4_large/
```

Defaults: `PHASE=1`, `phase1_epochs=6`, `batch_size=32`, then `PHASE=3` drop-test (skip Phase2).

OOM on T4: `batch_size=16`, `catalog_in_batch=14`, `market_in_batch=2`, `encode_batch_size=16`.
"""
    )
)

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.0"},
        "colab": {"provenance": [], "gpuType": "T4"},
    },
    "cells": cells,
}

OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"wrote {OUT} cells={len(cells)} bytes={OUT.stat().st_size}")
