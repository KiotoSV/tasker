"""Простой JSON-IO для пользовательских настроек (тема и т.п.).
Ошибки чтения/записи проглатываются — некритичная настройка не должна
ронять приложение."""

import json
from pathlib import Path

from tasker import config


def load_settings() -> dict:
    try:
        return json.loads(config.SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(data: dict) -> None:
    try:
        config.SETTINGS_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def update_settings(patch: dict) -> None:
    """Merge-апдейт: сохраняет переданные ключи, остальные настройки не трогает."""
    data = load_settings()
    data.update(patch)
    save_settings(data)


def get_projects_root() -> Path:
    """Корневая папка для диалога выбора проекта. Берётся из settings.json
    (ключ `projects_root`), либо дефолт из config.DEFAULT_PROJECTS_ROOT."""
    raw = load_settings().get("projects_root")
    if isinstance(raw, str) and raw.strip():
        return Path(raw)
    return config.DEFAULT_PROJECTS_ROOT
