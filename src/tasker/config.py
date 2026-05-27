"""Пути, форматы и прочие константы, не относящиеся к UI."""

import os
import re
import sys
from pathlib import Path


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _bundle_dir() -> Path:
    """Ресурсы, вшитые в сборку (иконка, шрифты)."""
    if _is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def _data_dir() -> Path:
    """Пользовательские данные: задачи, настройки."""
    if _is_frozen():
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "Tasker"
    return Path(__file__).resolve().parents[2]


BUNDLE_DIR = _bundle_dir()
DATA_DIR = _data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)

TASKS_DIR = DATA_DIR / "tasks"
ICON_PATH = BUNDLE_DIR / "icon.ico"
SETTINGS_PATH = DATA_DIR / "settings.json"

DEFAULT_PROJECTS_ROOT = Path(r"C:\dev")

DATE_FMT = "%Y-%m-%d %H:%M"
FORBIDDEN_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
