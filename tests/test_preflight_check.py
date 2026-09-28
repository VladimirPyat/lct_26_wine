"""Tests for scripts/preflight_check.py (files only, no DB)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "preflight_check.py"
_spec = importlib.util.spec_from_file_location("preflight_check", _SCRIPT)
assert _spec is not None and _spec.loader is not None
preflight = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = preflight
_spec.loader.exec_module(preflight)


def _write_csv(path: Path, slugs: list[str]) -> None:
    rows = "".join(f"{s},{s}\n" for s in slugs)
    path.write_text("Slug,Название вина\n" + rows, encoding="utf-8")


def test_model_missing_fails_with_download_link(tmp_path: Path) -> None:
    report = preflight.Report()
    preflight.check_model(report, tmp_path / "yolo_detect_labels_2.onnx")
    assert report.errors == 1
    assert "not found" in report.lines[0]
    assert "drive.google.com" in report.lines[0]


def test_model_too_small_fails(tmp_path: Path) -> None:
    model = tmp_path / "siglip2_wine_p1_epoch_3_fp16.onnx"
    model.write_text("<html>quota exceeded</html>", encoding="utf-8")
    report = preflight.Report()
    preflight.check_model(report, model)
    assert report.errors == 1
    assert "broken download" in report.lines[0]


def test_model_ok(tmp_path: Path) -> None:
    model = tmp_path / "m.onnx"
    model.write_bytes(b"\0" * (preflight.MIN_MODEL_BYTES + 1))
    report = preflight.Report()
    preflight.check_model(report, model)
    assert report.errors == 0


def test_sources_ok_with_few_missing_photos(tmp_path: Path) -> None:
    slugs = [f"wine-{i}" for i in range(40)]
    csv_path = tmp_path / "wines.csv"
    _write_csv(csv_path, slugs)
    site = tmp_path / "site.json"
    site.write_text("[]", encoding="utf-8")
    images = tmp_path / "images"
    images.mkdir()
    for slug in slugs[1:]:
        (images / f"{slug}.webp").write_bytes(b"x")
    report = preflight.Report()
    preflight.check_catalog_sources(report, csv_path, site, images)
    assert report.errors == 0
    assert any("1 without photo" in line for line in report.lines)


def test_sources_fail_when_most_photos_missing(tmp_path: Path) -> None:
    csv_path = tmp_path / "wines.csv"
    _write_csv(csv_path, ["a", "b", "c"])
    images = tmp_path / "images"
    images.mkdir()
    (images / "a.webp").write_bytes(b"x")
    report = preflight.Report()
    preflight.check_catalog_sources(report, csv_path, tmp_path / "site.json", images)
    assert report.errors == 1
    assert report.warnings == 1


def test_sources_detect_nested_photo_folder(tmp_path: Path) -> None:
    csv_path = tmp_path / "wines.csv"
    _write_csv(csv_path, ["a"])
    nested = tmp_path / "images" / "images"
    nested.mkdir(parents=True)
    (nested / "a.webp").write_bytes(b"x")
    report = preflight.Report()
    preflight.check_catalog_sources(
        report, csv_path, tmp_path / "site.json", tmp_path / "images"
    )
    assert report.errors == 1
    assert any("move them one level up" in line for line in report.lines)
