"""Пути, форматы и прочие константы, не относящиеся к UI."""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TASKS_DIR = PROJECT_ROOT / "tasks"
ICON_PATH = PROJECT_ROOT / "icon.ico"
SETTINGS_PATH = PROJECT_ROOT / "settings.json"

DEFAULT_PROJECTS_ROOT = Path(r"C:\dev")

DATE_FMT = "%Y-%m-%d %H:%M"
FORBIDDEN_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
