"""Catalog rebuild from a cleaned owner CSV (prepare + import resolution, no DB)."""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from PIL import Image

from db.import_catalog import build_arg_parser, resolve_source_image

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


def test_import_csv_flag_repeatable() -> None:
    args = build_arg_parser().parse_args(["--csv", "a.csv", "--csv", "b.csv"])
    assert args.csv == [Path("a.csv"), Path("b.csv")]
    assert build_arg_parser().parse_args([]).csv is None
