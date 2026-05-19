"""Папки вложений и копирование файлов. Не знает про UI."""

import re
import shutil
from pathlib import Path


def attachments_dir(task_path: Path) -> Path:
    return task_path.parent / task_path.stem


def list_attachments(task_path: Path) -> list[Path]:
    folder = attachments_dir(task_path)
    if not folder.is_dir():
        return []
    return sorted(
        (p for p in folder.iterdir() if p.is_file()),
        key=lambda p: p.name.lower(),
    )


def _unique_attachment_path(folder: Path, name: str) -> Path:
    target = folder / name
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    i = 2
    while True:
        target = folder / f"{stem} ({i}){suffix}"
        if not target.exists():
            return target
        i += 1


def copy_attachment(task_path: Path, source: Path) -> Path:
    folder = attachments_dir(task_path)
    folder.mkdir(exist_ok=True)
    dest = _unique_attachment_path(folder, source.name)
    shutil.copy2(source, dest)
    return dest


def parse_dnd_paths(data: str) -> list[Path]:
    """Tkinterdnd2 даёт пути через пробел; пути с пробелами обёрнуты в {}."""
    parts: list[str] = []
    for match in re.finditer(r"\{([^}]+)\}|(\S+)", data):
        parts.append(match.group(1) or match.group(2))
    return [Path(p) for p in parts if p]
