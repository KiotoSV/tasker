"""Простой JSON-IO для пользовательских настроек (тема и т.п.).
Ошибки чтения/записи проглатываются — некритичная настройка не должна
ронять приложение."""

import json

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
