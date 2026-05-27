# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (editable, with drag-and-drop support)
pip install -e ".[dnd]"

# Install without DnD
pip install -e .

# Run the app
python -m tasker

# Run tests
pip install -e ".[dev]"
pytest

# Run a single test
pytest tests/test_tasks.py::test_name
```

## Architecture

Tkinter desktop task planner. Tasks are plain `.txt` files in `tasks/` — no database. Attachments live in sibling folders (`TaskName/` next to `TaskName.txt`).

**Layers:**

- **Data** (`tasks.py`, `settings.py`, `attachments.py`) — file I/O, parsing, caching. `TaskRepository` caches parsed tasks by mtime.
- **UI** (`ui/`) — `main_window.py` is the App orchestrator (two-panel layout: task list + editor). `theme.py` provides light/dark palettes via mutable module-level globals (consumers must use `theme.BG`, not `from theme import BG`). `dnd.py` wraps optional tkinterdnd2.
- **Platform** (`platform_utils.py`) — Win11 DWM titlebar styling, PowerShell/explorer integration. All graceful no-ops on unsupported platforms.
- **Config** (`config.py`) — two path roots: `BUNDLE_DIR` (resources: icon, fonts) and `DATA_DIR` (user data: tasks, settings). In frozen .exe mode, `BUNDLE_DIR = sys._MEIPASS`, `DATA_DIR = %APPDATA%\Tasker`. In dev mode, both resolve to repo root via `Path(__file__).parents[2]`.

**Task file format:**
```
status: pending
project: C:\dev\myproject
created: 2026-05-19 11:44
completed:

Body text here.
```

Status values: `pending`, `deferred`, `done`. Setting status to `done` auto-fills `completed` timestamp.

## Key Design Decisions

- **Filename = title**: task file stem is the displayed title. Renaming a task renames the file and its attachments folder.
- **Optional DnD**: tkinterdnd2 is optional. `dnd.AVAILABLE` flag gates all drag-and-drop bindings; app works without it.
- **Bundled font**: `PlusJakartaSans-Variable.ttf` registered via Windows GDI (private, per-process). `fonts.py` must run before Tk root creation because Tcl caches fonts at init.
- **Theme switching**: requires manual re-apply to all widgets (no reactive binding). Theme persists in `settings.json`.
- **Single-threaded**: standard Tkinter event loop, all I/O synchronous.

## Build & Distribution

```bash
# Build .exe (output: dist/Tasker/)
pip install pyinstaller
pyinstaller tasker.spec --noconfirm

# Build installer (requires Inno Setup 6+)
# build.bat automates both steps: PyInstaller + Inno Setup
build.bat
```

`tasker.spec` — PyInstaller config (onedir, windowed, excludes tkinterdnd2).
`installer.iss` — Inno Setup script. Installs to Program Files (or LocalAppData\Programs without admin), creates desktop/start menu shortcuts, adds uninstaller.

## Language

The UI and all user-facing strings are in Russian.
