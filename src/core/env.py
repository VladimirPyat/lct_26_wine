"""Окружение процесса: минимальный загрузчик ``.env`` и активный профиль конфигов."""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOTENV = _REPO_ROOT / ".env"
_PROFILES_DIR = _REPO_ROOT / "config" / "profiles"
_BASE_PROFILE = "dev"


def load_dotenv(path: Path = _DOTENV) -> None:
    """Подмешать ``KEY=VALUE`` из ``.env`` в окружение (уже заданные ключи важнее)."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def active_profile(profiles_dir: Path = _PROFILES_DIR) -> str:
    """Профиль из ``APP_ENV`` (env или ``.env``); ``dev`` — только базовые YAML.

    Любой другой профиль обязан иметь каталог ``config/profiles/<name>/``.
    """
    load_dotenv()
    name = os.environ.get("APP_ENV", _BASE_PROFILE).strip().lower() or _BASE_PROFILE
    if name != _BASE_PROFILE and not (profiles_dir / name).is_dir():
        msg = (
            f"APP_ENV={name!r}: no overlay directory {profiles_dir / name}; "
            f"expected {_BASE_PROFILE!r} or an existing profile"
        )
        raise ValueError(msg)
    return name


def profile_overlay_path(
    base_yaml: Path, profiles_dir: Path = _PROFILES_DIR
) -> Path | None:
    """Оверлей для базового YAML из ``config/`` при активном профиле, иначе ``None``.

    YAML вне ``config/`` (тесты, ``--config`` скриптов) не оверлеятся.
    """
    if base_yaml.resolve().parent != profiles_dir.parent.resolve():
        return None
    profile = active_profile(profiles_dir)
    if profile == _BASE_PROFILE:
        return None
    overlay = profiles_dir / profile / base_yaml.name
    return overlay if overlay.is_file() else None
