"""Catalog rebuild from a cleaned owner CSV (prepare + import resolution, no DB)."""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import cv2
import numpy as np
from PIL import Image

from db.import_catalog import (
    build_arg_parser,
    copy_static_assets,
    resolve_source_image,
)

_REPO = Path(__file__).resolve().parents[1]
_OWNER_HEADER = [
    "Название вина",
    "Категория",
    "Цвет",
    "Регион",
    "Сорт винограда",
    "Описание",
    "Винодельня",
    "Slug",
    "Название фото",
    "Ссылка на страницу",
    "Файл в wines_images",
]


def _load_prepare_clean() -> ModuleType:
    script_dir = _REPO / "scripts" / "catalog_prepare"
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    path = script_dir / "prepare_clean_csv.py"
    spec = importlib.util.spec_from_file_location("prepare_clean_csv_t", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _owner_row(slug: str, title: str, image: str) -> dict[str, str]:
    row = dict.fromkeys(_OWNER_HEADER, "")
    row.update(
        {
            "Название вина": title,
            "Категория": "Красное",
            "Винодельня": "Фанагория",
            "Сорт винограда": "Шираз",
            "Slug": slug,
            "Файл в wines_images": image,
        }
    )
    return row


def test_prepare_clean_csv_splits_ready_and_rejected(tmp_path: Path) -> None:
    images = tmp_path / "images"
    images.mkdir()
    Image.new("RGB", (40, 80), (200, 10, 10)).save(images / "ok.webp")
    src = tmp_path / "clean.csv"
    with src.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_OWNER_HEADER)
        writer.writeheader()
        writer.writerow(_owner_row("ok-slug", "Ok Wine", "ok.webp"))
        writer.writerow(_owner_row("no-img", "No Image", ""))
        writer.writerow(_owner_row("missing", "Missing File", "absent.webp"))
        writer.writerow(_owner_row("ok-slug", "Dup Slug", "ok.webp"))
        writer.writerow(_owner_row("", "No Slug", "ok.webp"))

    ready_path = tmp_path / "ready.csv"
    rejected_path = tmp_path / "rejected.csv"
    module = _load_prepare_clean()
    code = module.main(
        [
            "--input", str(src),
            "--images-dir", str(images),
            "--site-json", str(tmp_path / "no_site.json"),
            "--out-ready", str(ready_path),
            "--out-rejected", str(rejected_path),
        ]
    )
    assert code == 0

    with ready_path.open(encoding="utf-8") as handle:
        ready = list(csv.DictReader(handle))
    with rejected_path.open(encoding="utf-8") as handle:
        rejected = {r["title"]: r["reason"] for r in csv.DictReader(handle)}

    assert [r["slug"] for r in ready] == ["ok-slug"]
    assert ready[0]["image_source"] == "clean"
    assert ready[0]["source_image"] == "ok.webp"
    assert ready[0]["grape_variety"] == "Шираз"
    assert rejected == {
        "No Image": "missing_image_file",
        "Missing File": "image_missing_or_unreadable",
        "Dup Slug": "duplicate_slug",
        "No Slug": "missing_slug",
    }


def test_resolve_source_image_clean(tmp_path: Path) -> None:
    clean = tmp_path / "clean"
    clean.mkdir()
    (clean / "a.webp").write_bytes(b"x")
    row = {"source_image": "a.webp", "image_source": "clean"}
    kwargs = {"owner_images": tmp_path / "owner", "site_images": tmp_path / "site"}
    assert resolve_source_image(row, clean_images=clean, **kwargs) == clean / "a.webp"
    assert resolve_source_image(row, **kwargs) is None


def _load_verify() -> ModuleType:
    path = _REPO / "scripts" / "catalog_prepare" / "verify_catalog_assets.py"
    spec = importlib.util.spec_from_file_location("verify_catalog_assets_t", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_crop_match_rmse_own_vs_foreign() -> None:
    rng = np.random.default_rng(1)
    static = cv2.GaussianBlur(
        rng.integers(0, 256, (900, 400, 3), dtype=np.uint8), (5, 5), 0
    )
    other = cv2.GaussianBlur(
        rng.integers(0, 256, (900, 400, 3), dtype=np.uint8), (5, 5), 0
    )
    crop = static[313:613, 57:337].copy()
    verify = _load_verify()
    assert verify.crop_match_rmse(static, crop, 480) < 1.0
    assert verify.crop_match_rmse(other, crop, 480) > 8.0


def test_copy_static_assets_only_for_ok_crops(tmp_path: Path) -> None:
    clean, crops, static = tmp_path / "clean", tmp_path / "crops", tmp_path / "static"
    for d in (clean, crops, static):
        d.mkdir()
    for name in ("a", "b"):
        Image.new("RGB", (30, 60), (1, 2, 3)).save(clean / f"{name}.webp")
    Image.new("RGB", (10, 10)).save(crops / "a.webp")
    rows = [
        {"slug": s, "source_image": f"{s}.webp", "image_source": "clean"}
        for s in ("a", "b", "c")
    ]
    stats = copy_static_assets(
        rows,
        owner_images=tmp_path,
        site_images=tmp_path,
        clean_images=clean,
        crops_dir=crops,
        static_dir=static,
    )
    assert stats == {
        "seen": 3, "copied": 1, "skipped_missing_image": 1, "skipped_no_crop": 1
    }
    assert (static / "a.webp").read_bytes() == (clean / "a.webp").read_bytes()
    assert not (static / "b.webp").exists()


def test_import_csv_flag_repeatable() -> None:
    args = build_arg_parser().parse_args(["--csv", "a.csv", "--csv", "b.csv"])
    assert args.csv == [Path("a.csv"), Path("b.csv")]
    assert build_arg_parser().parse_args([]).csv is None
