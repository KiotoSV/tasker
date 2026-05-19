"""Чтение, запись и индекс задач на файловой системе.

Каждая задача — это .txt файл вида:

    status: pending
    project: <путь>          # 0..N строк
    created: 2026-05-18 11:44
    completed:
    <пустая строка>
    <тело произвольной формы>
"""

from datetime import datetime
from pathlib import Path

from tasker.config import DATE_FMT, FORBIDDEN_CHARS


def now_str() -> str:
    return datetime.now().strftime(DATE_FMT)


def sanitize_filename(title: str) -> str:
    cleaned = FORBIDDEN_CHARS.sub("_", title).strip().rstrip(".")
    return cleaned or "Без названия"


def parse_task(path: Path) -> dict:
    status, created, completed = "pending", now_str(), ""
    projects: list[str] = []
    body_lines: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {"status": status, "projects": projects, "created": created,
                "completed": completed, "body": ""}

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line == "":
            i += 1
            break
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key == "status":
                status = value if value in ("done", "deferred") else "pending"
            elif key == "created":
                created = value or created
            elif key == "completed":
                completed = value
            elif key == "project":
                if value and value not in projects:
                    projects.append(value)
        i += 1
    body_lines = lines[i:]
    return {
        "status": status,
        "projects": projects,
        "created": created,
        "completed": completed,
        "body": "\n".join(body_lines),
    }


def write_task(path: Path, status: str, projects: list[str], created: str,
               completed: str, body: str) -> None:
    project_lines = "".join(f"project: {p}\n" for p in projects)
    content = (
        f"status: {status}\n"
        f"{project_lines}"
        f"created: {created}\n"
        f"completed: {completed}\n"
        f"\n"
        f"{body}"
    )
    path.write_text(content, encoding="utf-8")


class TaskRepository:
    """Индекс задач в указанной директории с кэшем парсинга по mtime."""

    def __init__(self, tasks_dir: Path) -> None:
        self.tasks_dir = tasks_dir
        self._cache: dict[Path, tuple[float, dict]] = {}

    def unique_path(self, base_name: str, exclude: Path | None = None) -> Path:
        candidate = self.tasks_dir / f"{base_name}.txt"
        if not candidate.exists() or candidate == exclude:
            return candidate
        i = 2
        while True:
            candidate = self.tasks_dir / f"{base_name} ({i}).txt"
            if not candidate.exists() or candidate == exclude:
                return candidate
            i += 1

    def list_tasks(self) -> list[dict]:
        tasks = []
        seen: set[Path] = set()
        for path in self.tasks_dir.glob("*.txt"):
            seen.add(path)
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            cached = self._cache.get(path)
            if cached and cached[0] == mtime:
                meta = dict(cached[1])
            else:
                meta = parse_task(path)
                self._cache[path] = (mtime, dict(meta))
            meta["path"] = path
            meta["title"] = path.stem
            tasks.append(meta)
        for stale in list(self._cache):
            if stale not in seen:
                self._cache.pop(stale, None)
        tasks.sort(key=lambda t: (t["created"], t["title"]), reverse=True)
        return tasks
