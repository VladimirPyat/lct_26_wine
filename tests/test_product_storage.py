"""PROD-API A — хранилище запросов: retention, доступ к фото, feedback JSONL."""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import yaml

from core.product import catalog_service as catalog_mod
from core.product.catalog_service import CatalogProductService
from core.product.schemas import FeedbackIn
from core.product.service import SearchNotFoundError
from core.product.storage import cleanup_expired, photo_path, result_path
from product_helpers import fake_card, make_result, make_settings, store_result

REPO_ROOT = Path(__file__).resolve().parents[1]
DAY = 86_400.0


def _touch(path: Path, age_days: float, now: float) -> Path:
    path.write_bytes(b"x")
    ts = now - age_days * DAY
    os.utime(path, (ts, ts))
    return path


@pytest.fixture
def aged_store(tmp_path: Path) -> tuple[Path, float, dict[str, Path]]:
    """Хранилище: старые / свежие файлы поиска + чужой старый файл."""
    qdir = tmp_path / "search_queries"
    qdir.mkdir()
    now = time.time()
    old_id, new_id = uuid.uuid4().hex, uuid.uuid4().hex
    files = {
        "old_jpg": _touch(qdir / f"{old_id}.jpg", 11, now),
        "old_json": _touch(qdir / f"{old_id}.json", 11, now),
        "new_jpg": _touch(qdir / f"{new_id}.jpg", 9, now),
        "new_json": _touch(qdir / f"{new_id}.json", 0.1, now),
        "foreign_old": _touch(qdir / "README.txt", 30, now),
    }
    return qdir, now, files


# --- retention -----------------------------------------------------------


def test_retention_deletes_old_keeps_new(aged_store) -> None:
    """[TEST-ID] PA-A7 удаляет файлы старше N дней, свежие и чужие остаются."""
    qdir, now, files = aged_store
    removed = cleanup_expired(qdir, 10, now=now)
    assert sorted(removed) == sorted([files["old_jpg"], files["old_json"]])
    assert not files["old_jpg"].exists()
    assert not files["old_json"].exists()
    assert files["new_jpg"].exists()
    assert files["new_json"].exists()
    assert files["foreign_old"].exists()


def test_retention_dry_run_deletes_nothing(aged_store) -> None:
    """[TEST-ID] PA-A7b dry_run возвращает список, ничего не удаляя."""
    qdir, now, files = aged_store
    listed = cleanup_expired(qdir, 10, dry_run=True, now=now)
    assert sorted(listed) == sorted([files["old_jpg"], files["old_json"]])
    assert all(p.exists() for p in files.values())


def test_retention_missing_dir(tmp_path: Path) -> None:
    """[TEST-ID] PA-A7c нет каталога → пустой список, без ошибки."""
    assert cleanup_expired(tmp_path / "nope", 10) == []


def _load_cleanup_script() -> ModuleType:
    path = REPO_ROOT / "scripts" / "cleanup_search_queries.py"
    spec = importlib.util.spec_from_file_location("cleanup_search_queries", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _script_config(tmp_path: Path, qdir: Path) -> Path:
    base = yaml.safe_load(
        (REPO_ROOT / "config" / "product.yaml").read_text(encoding="utf-8")
    )
    base["storage"]["queries_dir"] = str(qdir)
    cfg = tmp_path / "product_test.yaml"
    cfg.write_text(yaml.safe_dump(base, allow_unicode=True), encoding="utf-8")
    return cfg


def test_cleanup_script_dry_run_and_real(
    aged_store, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """[TEST-ID] PA-A7d cleanup_search_queries.py: --dry-run ничего не удаляет."""
    qdir, _now, files = aged_store
    script = _load_cleanup_script()
    cfg = _script_config(tmp_path, qdir)

    assert script.main(["--config", str(cfg), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "would remove 2 file(s)" in out
    assert all(p.exists() for p in files.values())

    assert script.main(["--config", str(cfg)]) == 0
    assert "removed 2 file(s)" in capsys.readouterr().out
    assert not files["old_jpg"].exists()
    assert files["new_jpg"].exists()
    assert files["foreign_old"].exists()


def test_cleanup_script_negative_days(aged_store, tmp_path: Path) -> None:
    """[TEST-ID] PA-A7e --days < 0 → код 2, ничего не удалено."""
    qdir, _now, files = aged_store
    script = _load_cleanup_script()
    cfg = _script_config(tmp_path, qdir)
    assert script.main(["--config", str(cfg), "--days", "-1"]) == 2
    assert all(p.exists() for p in files.values())


# --- photo path safety ---------------------------------------------------


@pytest.mark.parametrize(
    "bad_id",
    [
        "../../etc/passwd",
        "..",
        "",
        "not-a-hex-id",
        "Z" * 32,
        "ABCDEF0123456789ABCDEF0123456789",  # upper-case hex is not uuid4().hex
        "0123456789abcdef0123456789abcde",  # 31 chars
        "0123456789abcdef0123456789abcdef0",  # 33 chars
        "0123456789abcdef0123456789abcdef/../x",
        "*",
    ],
)
def test_query_photo_path_rejects_bad_ids(tmp_path: Path, bad_id: str) -> None:
    """[TEST-ID] PA-A8 обход путей / не-hex → None."""
    qdir = tmp_path / "q"
    qdir.mkdir()
    (qdir / f"{uuid.uuid4().hex}.jpg").write_bytes(b"x")
    assert photo_path(qdir, bad_id) is None
    assert result_path(qdir, bad_id) is None


def test_query_photo_path_unknown_and_known(tmp_path: Path) -> None:
    """[TEST-ID] PA-A8b неизвестный id → None; известный → путь к фото, не к JSON."""
    qdir = tmp_path / "q"
    qdir.mkdir()
    known = uuid.uuid4().hex
    (qdir / f"{known}.json").write_text("{}", encoding="utf-8")
    assert photo_path(qdir, known) is None  # only JSON, no photo
    photo = qdir / f"{known}.png"
    photo.write_bytes(b"x")
    assert photo_path(qdir, known) == photo
    assert photo_path(qdir, uuid.uuid4().hex) is None
    assert photo_path(tmp_path / "missing_dir", known) is None


def test_query_photo_path_symlink_outside_rejected(tmp_path: Path) -> None:
    """[TEST-ID] PA-A8c симлинк {id}.jpg наружу хранилища → None."""
    qdir = tmp_path / "q"
    qdir.mkdir()
    outside = tmp_path / "secret.jpg"
    outside.write_bytes(b"x")
    sid = uuid.uuid4().hex
    (qdir / f"{sid}.jpg").symlink_to(outside)
    assert photo_path(qdir, sid) is None


# --- feedback ------------------------------------------------------------


@pytest.fixture
def offline_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> CatalogProductService:
    """Реальный CatalogProductService без БД: справочники не строятся."""
    monkeypatch.setattr(
        catalog_mod, "session_scope", lambda _factory: contextlib.nullcontext(None)
    )
    monkeypatch.setattr(
        CatalogProductService, "_build_dictionaries", lambda self, session: None
    )
    runtime = SimpleNamespace(repo_root=tmp_path, session_factory=None)
    return CatalogProductService(runtime, make_settings(tmp_path))  # type: ignore[arg-type]


def test_feedback_jsonl_schema(
    offline_service: CatalogProductService, tmp_path: Path
) -> None:
    """[TEST-ID] PA-A9 схема строки feedback JSONL (контракт §4.5)."""
    winner = fake_card("winner-slug")
    result = make_result(status="found", winner=winner)
    store_result(tmp_path / "search_queries", result)

    offline_service.record_feedback(
        FeedbackIn(search_id=result.search_id, verdict="match")
    )
    offline_service.record_feedback(
        FeedbackIn(search_id=result.search_id, slug="other-slug", verdict="mismatch")
    )

    lines = (
        (tmp_path / "search_feedback.jsonl").read_text(encoding="utf-8").splitlines()
    )
    assert len(lines) == 2
    first, second = (json.loads(line) for line in lines)
    expected_keys = {
        "ts",
        "search_id",
        "slug",
        "verdict",
        "status",
        "confidence_level",
        "winner_slug",
    }
    assert set(first) == expected_keys
    assert set(second) == expected_keys
    datetime.fromisoformat(first["ts"])
    assert first["search_id"] == result.search_id
    assert first["slug"] == "winner-slug"  # defaults to winner
    assert first["verdict"] == "match"
    assert first["status"] == "found"
    assert first["confidence_level"] == "high"
    assert first["winner_slug"] == "winner-slug"
    assert second["slug"] == "other-slug"
    assert second["verdict"] == "mismatch"


def test_feedback_not_found_winner_none(
    offline_service: CatalogProductService, tmp_path: Path
) -> None:
    """[TEST-ID] PA-A9b not_found: winner_slug / slug = null."""
    result = make_result(status="not_found")
    store_result(tmp_path / "search_queries", result)
    offline_service.record_feedback(
        FeedbackIn(search_id=result.search_id, verdict="mismatch")
    )
    record = json.loads(
        (tmp_path / "search_feedback.jsonl").read_text(encoding="utf-8")
    )
    assert record["winner_slug"] is None
    assert record["slug"] is None
    assert record["status"] == "not_found"


@pytest.mark.parametrize("search_id", [uuid.uuid4().hex, "../../etc/passwd", "x"])
def test_feedback_unknown_search(
    offline_service: CatalogProductService, tmp_path: Path, search_id: str
) -> None:
    """[TEST-ID] PA-A9c неизвестный поиск → SearchNotFoundError, файл не создаётся."""
    with pytest.raises(SearchNotFoundError):
        offline_service.record_feedback(
            FeedbackIn(search_id=search_id, verdict="match")
        )
    assert not (tmp_path / "search_feedback.jsonl").exists()


def test_get_search_roundtrip(
    offline_service: CatalogProductService, tmp_path: Path
) -> None:
    """[TEST-ID] PA-A9d get_search читает сохранённый JSON; неизвестный → None."""
    result = make_result(status="found", winner=fake_card())
    store_result(tmp_path / "search_queries", result)
    assert offline_service.get_search(result.search_id) == result
    assert offline_service.get_search(uuid.uuid4().hex) is None
    assert offline_service.get_search("../x") is None


def test_service_startup_retention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """[TEST-ID] PA-A7f при создании сервиса удаляются файлы старше retention_days."""
    qdir = tmp_path / "search_queries"
    qdir.mkdir()
    now = time.time()
    old = _touch(qdir / f"{uuid.uuid4().hex}.jpg", 11, now)
    new = _touch(qdir / f"{uuid.uuid4().hex}.jpg", 1, now)
    monkeypatch.setattr(
        catalog_mod, "session_scope", lambda _factory: contextlib.nullcontext(None)
    )
    monkeypatch.setattr(
        CatalogProductService, "_build_dictionaries", lambda self, session: None
    )
    runtime = SimpleNamespace(repo_root=tmp_path, session_factory=None)
    CatalogProductService(runtime, make_settings(tmp_path))  # type: ignore[arg-type]
    assert not old.exists()
    assert new.exists()
