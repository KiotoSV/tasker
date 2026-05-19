"""Простой GUI-планнер. Задачи хранятся как .txt файлы в подпапке tasks/."""

import os
import re
import shutil
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _BaseTk = TkinterDnD.Tk
    _DND_AVAILABLE = True
except ImportError:
    _BaseTk = tk.Tk
    DND_FILES = None
    _DND_AVAILABLE = False


def _apply_dark_titlebar(window: tk.Tk) -> None:
    """Переключает шапку окна в тёмный режим на Windows 10/11."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()
        set_attr = ctypes.windll.dwmapi.DwmSetWindowAttribute
        value = ctypes.c_int(1)
        for attr in (20, 19):
            rv = set_attr(
                wintypes.HWND(hwnd),
                wintypes.DWORD(attr),
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
            if rv == 0:
                break
    except Exception:
        pass

TASKS_DIR = Path(__file__).parent / "tasks"
PROJECTS_ROOT = Path(r"C:\dev")
DATE_FMT = "%Y-%m-%d %H:%M"
FORBIDDEN_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

BG = "#0F1411"
SURFACE = "#161C18"
SURFACE_ALT = "#1B2320"
BORDER = "#26302A"
TEXT = "#E6EDE7"
MUTED = "#7E8E84"
ACCENT = "#22C55E"
ACCENT_HOVER = "#16A34A"
ACCENT_ACTIVE = "#15803D"
ACCENT_SOFT = "#14281B"
DANGER = "#F87171"
FONT_FAMILY = "Segoe UI"


def now_str() -> str:
    return datetime.now().strftime(DATE_FMT)


def sanitize_filename(title: str) -> str:
    cleaned = FORBIDDEN_CHARS.sub("_", title).strip().rstrip(".")
    return cleaned or "Без названия"


def unique_path(base_name: str, exclude: Path | None = None) -> Path:
    candidate = TASKS_DIR / f"{base_name}.txt"
    if not candidate.exists() or candidate == exclude:
        return candidate
    i = 2
    while True:
        candidate = TASKS_DIR / f"{base_name} ({i}).txt"
        if not candidate.exists() or candidate == exclude:
            return candidate
        i += 1


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
                status = "done" if value == "done" else "pending"
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


def launch_claude_in_powershell(project_path: Path) -> None:
    """Открывает новое окно PowerShell, делает cd в папку и запускает claude."""
    escaped = str(project_path).replace("'", "''")
    command = f"Set-Location -LiteralPath '{escaped}'; claude"
    if sys.platform == "win32":
        subprocess.Popen(
            ["powershell.exe", "-NoExit", "-Command", command],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    else:
        subprocess.Popen(["pwsh", "-NoExit", "-Command", command])


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


def open_in_system(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def reveal_in_explorer(path: Path) -> None:
    if sys.platform == "win32":
        full = str(path.resolve())
        subprocess.Popen(f'explorer /select,"{full}"')
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path.parent)])


def parse_dnd_paths(data: str) -> list[Path]:
    """Tkinterdnd2 даёт пути через пробел; пути с пробелами обёрнуты в {}."""
    parts: list[str] = []
    for match in re.finditer(r"\{([^}]+)\}|(\S+)", data):
        parts.append(match.group(1) or match.group(2))
    return [Path(p) for p in parts if p]


_PARSE_CACHE: dict[Path, tuple[float, dict]] = {}


def list_tasks() -> list[dict]:
    tasks = []
    seen: set[Path] = set()
    for path in TASKS_DIR.glob("*.txt"):
        seen.add(path)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        cached = _PARSE_CACHE.get(path)
        if cached and cached[0] == mtime:
            meta = dict(cached[1])
        else:
            meta = parse_task(path)
            _PARSE_CACHE[path] = (mtime, dict(meta))
        meta["path"] = path
        meta["title"] = path.stem
        tasks.append(meta)
    for stale in list(_PARSE_CACHE):
        if stale not in seen:
            _PARSE_CACHE.pop(stale, None)
    tasks.sort(key=lambda t: (t["created"], t["title"]), reverse=True)
    return tasks


class App(_BaseTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Планнер")
        self.geometry("1280x820")
        self.minsize(760, 480)
        icon_path = Path(__file__).parent / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(default=str(icon_path))
            except tk.TclError:
                pass

        self.filter_var = tk.StringVar(value="pending")
        self.search_var = tk.StringVar(value="")
        self.done_var = tk.BooleanVar(value=False)
        self.current_path: Path | None = None
        self.current_meta: dict | None = None
        self._current_projects: list[str] = []
        self.list_rows: list[dict] = []
        self.selected_path: str | None = None
        self.filter_radios: dict[str, ttk.Radiobutton] = {}
        self._row_wraplength = 240
        self._sash_initialized = False
        self._horizontal_required = 320
        self._toast: tk.Widget | None = None
        self._toast_timer: str | None = None

        self._apply_theme()
        self._build_ui()
        TASKS_DIR.mkdir(exist_ok=True)
        self.refresh_list()
        self._select_first_if_any()
        self.update_idletasks()
        _apply_dark_titlebar(self)
        self.bind("<Map>", lambda e: _apply_dark_titlebar(self), add="+")
        self._init_sash()
        self._paned.bind("<Map>", lambda e: self._init_sash())
        self._paned.bind("<Configure>", self._on_paned_configure)
        self.bind_all("<Control-s>", self._on_ctrl_s)
        self.bind_all("<Control-S>", self._on_ctrl_s)
        self.bind_all("<Control-KeyPress>", self._on_control_keypress)

    def _apply_theme(self) -> None:
        self.configure(bg=BG)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        base_font = (FONT_FAMILY, 10)
        label_font = (FONT_FAMILY, 10)
        title_font = (FONT_FAMILY, 11)

        style.configure(".", background=BG, foreground=TEXT, font=base_font)
        style.configure("TFrame", background=BG)
        style.configure("Surface.TFrame", background=SURFACE)
        style.configure("TLabel", background=BG, foreground=TEXT, font=label_font)
        style.configure("Surface.TLabel", background=SURFACE, foreground=TEXT)
        style.configure("Muted.TLabel", background=SURFACE, foreground=MUTED, font=(FONT_FAMILY, 9))
        style.configure("Section.TLabel", background=SURFACE, foreground=MUTED,
                        font=(FONT_FAMILY, 9, "bold"))
        style.configure("Heading.TLabel", background=BG, foreground=TEXT,
                        font=(FONT_FAMILY, 16, "bold"))
        style.configure("Accent.TLabel", background=BG, foreground=ACCENT,
                        font=(FONT_FAMILY, 10, "bold"))

        style.configure(
            "TEntry",
            fieldbackground=SURFACE,
            background=SURFACE,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            insertcolor=ACCENT,
            padding=8,
            font=title_font,
            relief="flat",
        )
        style.map(
            "TEntry",
            bordercolor=[("focus", ACCENT)],
            lightcolor=[("focus", ACCENT)],
            darkcolor=[("focus", ACCENT)],
        )

        style.configure(
            "Primary.TButton",
            background=ACCENT,
            foreground="#FFFFFF",
            bordercolor=ACCENT,
            focusthickness=0,
            padding=(14, 8),
            font=(FONT_FAMILY, 10, "bold"),
            relief="flat",
        )
        style.map(
            "Primary.TButton",
            background=[("active", ACCENT_HOVER), ("pressed", ACCENT_ACTIVE)],
            bordercolor=[("active", ACCENT_HOVER), ("pressed", ACCENT_ACTIVE)],
            foreground=[("disabled", "#E5E7EB")],
        )

        style.configure(
            "Subtle.TButton",
            background=SURFACE,
            foreground=TEXT,
            bordercolor=BORDER,
            focusthickness=0,
            padding=(10, 6),
            relief="flat",
            font=base_font,
        )
        style.map(
            "Subtle.TButton",
            background=[("active", SURFACE_ALT), ("disabled", SURFACE)],
            bordercolor=[("active", ACCENT), ("disabled", BORDER)],
            foreground=[("disabled", MUTED)],
        )

        style.configure(
            "Danger.TButton",
            background=BG,
            foreground=DANGER,
            bordercolor=BORDER,
            focusthickness=0,
            padding=(12, 7),
            relief="flat",
            font=base_font,
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#2A1818")],
            bordercolor=[("active", DANGER)],
        )

        style.configure(
            "Filter.TRadiobutton",
            background=BG,
            foreground=MUTED,
            indicatorrelief="flat",
            indicatordiameter=0,
            padding=(12, 6),
            font=(FONT_FAMILY, 9),
        )
        style.map(
            "Filter.TRadiobutton",
            background=[("selected", ACCENT_SOFT), ("active", SURFACE_ALT)],
            foreground=[("selected", ACCENT), ("active", TEXT)],
        )

        style.configure(
            "TCheckbutton",
            background=SURFACE,
            foreground=TEXT,
            focusthickness=0,
            font=base_font,
        )
        style.map(
            "TCheckbutton",
            background=[("active", SURFACE)],
            foreground=[("disabled", MUTED)],
        )

        style.configure(
            "Treeview",
            background=SURFACE,
            fieldbackground=SURFACE,
            foreground=TEXT,
            rowheight=34,
            borderwidth=0,
            relief="flat",
            font=base_font,
        )
        style.map(
            "Treeview",
            background=[("selected", ACCENT_SOFT)],
            foreground=[("selected", ACCENT)],
        )
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

        style.configure("TPanedwindow", background=BORDER)
        style.configure("Sash", sashthickness=6, gripcount=0)

        style.configure(
            "Vertical.TScrollbar",
            background=BG,
            troughcolor=BG,
            bordercolor=BG,
            arrowcolor=MUTED,
            lightcolor=BG,
            darkcolor=BG,
            relief="flat",
        )
        style.map(
            "Vertical.TScrollbar",
            background=[("active", ACCENT_SOFT)],
        )

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.grid(row=0, column=0, sticky="nsew")
        self._paned = paned

        left = ttk.Frame(paned, padding=(20, 20, 14, 20))
        left.rowconfigure(4, weight=1)
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text="Планнер", style="Heading.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 14)
        )

        toolbar = ttk.Frame(left)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        ttk.Button(
            toolbar, text="＋  Новая задача", style="Primary.TButton",
            command=self.new_task, cursor="hand2",
        ).pack(side="left")

        self.search_container = tk.Frame(
            left, bg=SURFACE, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=BORDER,
        )
        self.search_container.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.search_entry = tk.Entry(
            self.search_container,
            textvariable=self.search_var,
            bg=SURFACE, fg=TEXT, insertbackground=ACCENT,
            relief="flat", borderwidth=0, highlightthickness=0,
            font=(FONT_FAMILY, 10),
        )
        self.search_entry.pack(fill="x", padx=12, pady=8)
        self.search_placeholder = tk.Label(
            self.search_container,
            text="Поиск по названию",
            bg=SURFACE, fg=MUTED,
            font=(FONT_FAMILY, 10),
            cursor="hand2",
        )
        self.search_placeholder.place(in_=self.search_entry, relx=0, rely=0.5, x=2, anchor="w")
        self.search_placeholder.bind(
            "<Button-1>", lambda e: self.search_entry.focus_set()
        )
        self.search_entry.bind(
            "<FocusIn>",
            lambda e: self.search_container.configure(
                highlightbackground=ACCENT, highlightcolor=ACCENT,
            ),
        )
        self.search_entry.bind(
            "<FocusOut>",
            lambda e: self.search_container.configure(
                highlightbackground=BORDER, highlightcolor=BORDER,
            ),
        )
        self.search_entry.bind("<Escape>", lambda e: self._clear_search())
        self.search_var.trace_add("write", lambda *_: self._on_search_change())

        self.filter_container = ttk.Frame(left)
        self.filter_container.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        for label, value in (("Все", "all"), ("Активные", "pending"), ("Сделанные", "done")):
            radio = ttk.Radiobutton(
                self.filter_container, text=label, value=value,
                style="Filter.TRadiobutton",
                variable=self.filter_var, command=self.refresh_list,
                cursor="hand2",
            )
            self.filter_radios[value] = radio
        self._filter_vertical = False
        self._apply_filter_layout()
        self.filter_container.bind("<Configure>", self._on_filter_resize)

        list_card = tk.Frame(
            left, bg=SURFACE, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=BORDER,
        )
        list_card.grid(row=4, column=0, sticky="nsew")
        list_card.rowconfigure(0, weight=1)
        list_card.columnconfigure(0, weight=1)

        self.list_canvas = tk.Canvas(
            list_card, bg=SURFACE, highlightthickness=0, bd=0,
        )
        self.list_canvas.grid(row=0, column=0, sticky="nsew", padx=(2, 0), pady=2)
        list_scroll = ttk.Scrollbar(
            list_card, orient="vertical", command=self.list_canvas.yview,
        )
        list_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 2), pady=2)
        self.list_canvas.configure(yscrollcommand=list_scroll.set)

        self.list_inner = tk.Frame(self.list_canvas, bg=SURFACE)
        self._list_window = self.list_canvas.create_window(
            (0, 0), window=self.list_inner, anchor="nw",
        )
        self._scrollregion_pending = False
        self._wraplength_pending = False
        self.list_inner.bind(
            "<Configure>",
            lambda e: self._request_scrollregion_update(),
        )
        self.list_canvas.bind("<Configure>", self._on_list_canvas_resize)
        self.list_canvas.bind(
            "<Enter>",
            lambda e: self.list_canvas.bind_all("<MouseWheel>", self._on_list_wheel),
        )
        self.list_canvas.bind(
            "<Leave>",
            lambda e: self.list_canvas.unbind_all("<MouseWheel>"),
        )

        self._empty_label = tk.Label(
            self.list_inner, text="Задач нет",
            bg=SURFACE, fg=MUTED, font=(FONT_FAMILY, 10),
            padx=20, pady=24,
        )

        paned.add(left, weight=0)

        right_wrap = ttk.Frame(paned, padding=(6, 20, 20, 20))
        right_wrap.rowconfigure(0, weight=1)
        right_wrap.columnconfigure(0, weight=1)

        card = tk.Frame(
            right_wrap, bg=SURFACE, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=BORDER,
        )
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        inner = ttk.Frame(card, style="Surface.TFrame", padding=22)
        inner.grid(row=0, column=0, sticky="nsew")
        inner.columnconfigure(0, weight=1)
        inner.rowconfigure(6, weight=1)
        self._editor_inner = inner

        ttk.Label(inner, text="НАЗВАНИЕ", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        title_row = ttk.Frame(inner, style="Surface.TFrame")
        title_row.grid(row=1, column=0, sticky="ew", pady=(4, 12))
        title_row.columnconfigure(0, weight=1)
        self.title_entry = ttk.Entry(title_row)
        self.title_entry.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.status_check = ttk.Checkbutton(
            title_row, text="Выполнена", variable=self.done_var,
            cursor="hand2",
        )
        self.status_check.grid(row=0, column=1, sticky="e")

        project_header = ttk.Frame(inner, style="Surface.TFrame")
        project_header.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        project_header.columnconfigure(0, weight=1)
        ttk.Label(
            project_header, text="ПРОЕКТЫ", style="Section.TLabel",
        ).grid(row=0, column=0, sticky="w")
        self.project_add_button = ttk.Button(
            project_header, text="＋  Добавить проект",
            style="Subtle.TButton", command=self._add_project,
            cursor="hand2",
        )
        self.project_add_button.grid(row=0, column=1, sticky="e")

        self.project_card = tk.Frame(
            inner, bg=SURFACE, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=BORDER,
        )
        self.project_card.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        self.projects_frame = tk.Frame(self.project_card, bg=SURFACE)
        self.projects_frame.pack(fill="x", padx=10, pady=8)
        self._projects_empty_label = tk.Label(
            self.projects_frame,
            text="Нет проектов",
            bg=SURFACE, fg=MUTED, font=(FONT_FAMILY, 9),
            anchor="w",
        )
        self._project_rows: list[tk.Frame] = []

        self.dates_label = ttk.Label(
            inner, text="", style="Muted.TLabel", anchor="w",
        )
        self.dates_label.grid(row=4, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(inner, text="ОПИСАНИЕ", style="Section.TLabel").grid(
            row=5, column=0, sticky="w"
        )
        body_card = tk.Frame(
            inner, bg=SURFACE, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=BORDER,
        )
        body_card.grid(row=6, column=0, sticky="nsew", pady=(4, 14))
        body_card.rowconfigure(0, weight=1)
        body_card.columnconfigure(0, weight=1)
        self.body_text = tk.Text(
            body_card, wrap="word", undo=True,
            bg=SURFACE, fg=TEXT, insertbackground=ACCENT,
            relief="flat", borderwidth=0, highlightthickness=0,
            padx=10, pady=10, font=(FONT_FAMILY, 10),
            selectbackground=ACCENT_SOFT, selectforeground=ACCENT,
        )
        self.body_text.grid(row=0, column=0, sticky="nsew")
        body_scroll = ttk.Scrollbar(body_card, orient="vertical", command=self.body_text.yview)
        body_scroll.grid(row=0, column=1, sticky="ns")
        self.body_text.configure(yscrollcommand=body_scroll.set)

        attach_header = ttk.Frame(inner, style="Surface.TFrame")
        attach_header.grid(row=7, column=0, sticky="ew", pady=(0, 4))
        attach_header.columnconfigure(0, weight=1)
        ttk.Label(
            attach_header, text="ВЛОЖЕНИЯ", style="Section.TLabel",
        ).grid(row=0, column=0, sticky="w")
        self.attach_button = ttk.Button(
            attach_header, text="＋  Прикрепить",
            style="Subtle.TButton", command=self._attach_via_dialog,
            cursor="hand2",
        )
        self.attach_button.grid(row=0, column=1, sticky="e")

        self.attach_card = tk.Frame(
            inner, bg=SURFACE, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=BORDER,
        )
        self.attach_card.grid(row=8, column=0, sticky="ew", pady=(0, 14))
        self.attachments_frame = tk.Frame(self.attach_card, bg=SURFACE)
        self.attachments_frame.pack(fill="x", padx=10, pady=8)
        self._attach_empty_label = tk.Label(
            self.attachments_frame,
            text=("Нет вложений · перетащите файлы сюда"
                  if _DND_AVAILABLE else "Нет вложений"),
            bg=SURFACE, fg=MUTED, font=(FONT_FAMILY, 9),
            anchor="w",
        )
        self._attachment_rows: list[tk.Frame] = []

        actions = ttk.Frame(inner, style="Surface.TFrame")
        actions.grid(row=9, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        ttk.Button(
            actions, text="Удалить", style="Danger.TButton", command=self.delete_task,
            cursor="hand2",
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            actions, text="Сохранить", style="Primary.TButton", command=self.save_task,
            cursor="hand2",
        ).grid(row=0, column=1, sticky="e")

        paned.add(right_wrap, weight=1)

        if _DND_AVAILABLE:
            for widget in (self.attach_card, self.attachments_frame, self.body_text):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_files_dropped)

        self._set_editor_enabled(False)
        self._update_meta_label(None)
        self._refresh_attachments()
        self._refresh_projects()

    def _resolve_target_width(self) -> int:
        width = self._paned.winfo_width()
        if width < 100:
            width = self.winfo_width()
        if width < 100:
            try:
                geom = self.geometry().split("+", 1)[0]
                width = int(geom.split("x")[0])
            except (ValueError, IndexError):
                width = 1280
        return width

    def _init_sash(self) -> None:
        if self._sash_initialized:
            return
        width = self._resolve_target_width()
        target = max(220, int(width * 0.25))
        try:
            self._paned.sashpos(0, target)
        except tk.TclError as exc:
            print(f"[sash] sashpos failed: {exc}", flush=True)
            return
        try:
            actual = self._paned.sashpos(0)
        except tk.TclError:
            actual = -1
        print(f"[sash] requested {target} (width={width}), got {actual}", flush=True)
        if actual >= 100:
            self._sash_initialized = True

    def _on_paned_configure(self, event: tk.Event) -> None:
        if self._sash_initialized:
            return
        self._init_sash()

    def _apply_filter_layout(self) -> None:
        for w in self.filter_radios.values():
            w.pack_forget()
        if self._filter_vertical:
            for w in self.filter_radios.values():
                w.pack(side="top", anchor="w", pady=(0, 4))
        else:
            for w in self.filter_radios.values():
                w.pack(side="left", padx=(0, 4))

    def _measure_filter_required(self) -> int:
        """Return horizontal width needed to fit all filter buttons in one row."""
        if self._filter_vertical:
            return self._horizontal_required
        self.filter_container.update_idletasks()
        total = sum(w.winfo_reqwidth() for w in self.filter_radios.values())
        total += 4 * (len(self.filter_radios) - 1)
        total += 12
        return total

    def _on_filter_resize(self, event: tk.Event) -> None:
        if event.width <= 1:
            return
        if not self._filter_vertical:
            self._horizontal_required = self._measure_filter_required()
        threshold = self._horizontal_required
        should_vertical = event.width < threshold
        if should_vertical != self._filter_vertical:
            self._filter_vertical = should_vertical
            self._apply_filter_layout()

    def _reflow_filters_if_needed(self) -> None:
        if self._filter_vertical:
            return
        self._horizontal_required = self._measure_filter_required()
        current = self.filter_container.winfo_width()
        if current > 1 and current < self._horizontal_required:
            self._filter_vertical = True
            self._apply_filter_layout()

    def _on_search_change(self) -> None:
        if self.search_var.get():
            self.search_placeholder.place_forget()
        else:
            self.search_placeholder.place(
                in_=self.search_entry, relx=0, rely=0.5, x=2, anchor="w",
            )
        self.refresh_list()

    def _clear_search(self) -> None:
        self.search_var.set("")
        self.focus_set()

    def _on_ctrl_s(self, _event: tk.Event) -> str:
        if self.current_path is not None:
            self.save_task()
        return "break"

    def _on_control_keypress(self, event: tk.Event) -> str | None:
        """Ловит Ctrl+C/V/X/A/S на нелатинских раскладках.

        Tk матчит <Control-c> по keysym; на русской раскладке у физической
        клавиши C keysym нелатинский — стандартные биндинги не срабатывают.
        Здесь матчим по keycode (физическая клавиша). На латинской раскладке
        keysym совпадает с ожидаемой буквой — отдаём событие штатному
        обработчику класса виджета.
        """
        actions = {
            67: ("c", lambda w: w.event_generate("<<Copy>>")),
            86: ("v", lambda w: w.event_generate("<<Paste>>")),
            88: ("x", lambda w: w.event_generate("<<Cut>>")),
            65: ("a", self._select_all_in),
            83: ("s", lambda w: self._on_ctrl_s(event)),
        }
        info = actions.get(event.keycode)
        if info is None:
            return None
        expected, fn = info
        if event.keysym.lower() == expected:
            return None
        fn(event.widget)
        return "break"

    @staticmethod
    def _select_all_in(widget: tk.Widget) -> None:
        try:
            if isinstance(widget, tk.Text):
                widget.tag_add("sel", "1.0", "end-1c")
                widget.mark_set("insert", "end-1c")
            elif isinstance(widget, (tk.Entry, ttk.Entry)):
                widget.select_range(0, "end")
                widget.icursor("end")
        except tk.TclError:
            pass

    def _show_toast(self, message: str, kind: str = "success") -> None:
        if self._toast_timer is not None:
            try:
                self.after_cancel(self._toast_timer)
            except (tk.TclError, ValueError):
                pass
            self._toast_timer = None
        if self._toast is not None:
            try:
                self._toast.destroy()
            except tk.TclError:
                pass
            self._toast = None

        icons = {"success": "✓", "info": "•", "warn": "!"}
        icon_colors = {"success": ACCENT, "info": ACCENT, "warn": DANGER}
        icon = icons.get(kind, "•")
        icon_fg = icon_colors.get(kind, ACCENT)

        toast = tk.Frame(
            self, bg=SURFACE_ALT, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=BORDER,
        )
        icon_label = tk.Label(
            toast, text=icon, bg=SURFACE_ALT, fg=icon_fg,
            font=(FONT_FAMILY, 12, "bold"),
        )
        icon_label.pack(side="left", padx=(14, 8), pady=10)
        text_label = tk.Label(
            toast, text=message, bg=SURFACE_ALT, fg=TEXT,
            font=(FONT_FAMILY, 10),
        )
        text_label.pack(side="left", padx=(0, 16), pady=10)
        toast.place(relx=1.0, rely=0.0, x=-22, y=22, anchor="ne")
        toast.lift()
        self._toast = toast
        self._toast_timer = self.after(2200, self._hide_toast)

    def _hide_toast(self) -> None:
        self._toast_timer = None
        if self._toast is not None:
            try:
                self._toast.destroy()
            except tk.TclError:
                pass
            self._toast = None

    def _set_editor_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.title_entry.configure(state=state)
        self.body_text.configure(state=state)
        self.status_check.configure(state="normal" if enabled else "disabled")
        self.attach_button.configure(state=state)
        self.project_add_button.configure(state=state)

    def _refresh_attachments(self) -> None:
        for row in self._attachment_rows:
            row.destroy()
        self._attachment_rows.clear()
        self._attach_empty_label.pack_forget()

        items = list_attachments(self.current_path) if self.current_path else []
        if not items:
            self._attach_empty_label.pack(fill="x", pady=2)
            return

        for att in items:
            row = self._build_attachment_row(att)
            row.pack(fill="x", pady=2)
            self._attachment_rows.append(row)

    def _build_attachment_row(self, att_path: Path) -> tk.Frame:
        row = tk.Frame(self.attachments_frame, bg=SURFACE)
        row.columnconfigure(1, weight=1)

        icon = tk.Label(
            row, text="📎", bg=SURFACE, fg=MUTED,
            font=(FONT_FAMILY, 11),
        )
        icon.grid(row=0, column=0, sticky="w", padx=(0, 6))

        name = tk.Label(
            row, text=att_path.name, bg=SURFACE, fg=ACCENT,
            font=(FONT_FAMILY, 10), cursor="hand2", anchor="w",
        )
        name.grid(row=0, column=1, sticky="ew")
        name.bind("<Button-1>", lambda e, p=att_path: self._open_attachment(p))
        name.bind("<Button-3>", lambda e, p=att_path: self._reveal_attachment(p))
        name.bind("<Enter>", lambda e, lbl=name: lbl.configure(fg=ACCENT_HOVER))
        name.bind("<Leave>", lambda e, lbl=name: lbl.configure(fg=ACCENT))

        remove = tk.Label(
            row, text="×", bg=SURFACE, fg=MUTED,
            font=(FONT_FAMILY, 14), cursor="hand2", padx=6,
        )
        remove.grid(row=0, column=2, sticky="e")
        remove.bind("<Button-1>", lambda e, p=att_path: self._remove_attachment(p))
        remove.bind("<Enter>", lambda e, lbl=remove: lbl.configure(fg=DANGER))
        remove.bind("<Leave>", lambda e, lbl=remove: lbl.configure(fg=MUTED))

        return row

    def _attach_via_dialog(self) -> None:
        if self.current_path is None:
            return
        paths = filedialog.askopenfilenames(
            parent=self, title="Выберите файлы для прикрепления",
        )
        self._attach_paths([Path(p) for p in paths])

    def _on_files_dropped(self, event) -> None:
        if self.current_path is None:
            self._show_toast("Сначала выберите задачу", kind="warn")
            return
        self._attach_paths(parse_dnd_paths(event.data))

    def _attach_paths(self, sources: list[Path]) -> None:
        if self.current_path is None or not sources:
            return
        added = 0
        skipped = 0
        for src in sources:
            if not src.is_file():
                skipped += 1
                continue
            try:
                copy_attachment(self.current_path, src)
                added += 1
            except OSError as exc:
                messagebox.showerror("Ошибка прикрепления", f"{src.name}: {exc}")
        self._refresh_attachments()
        if added:
            word = self._plural_files(added)
            self._show_toast(f"Прикреплено: {added} {word}")
        if skipped and not added:
            self._show_toast("Папки не прикрепляются", kind="warn")

    @staticmethod
    def _plural_files(n: int) -> str:
        if n % 10 == 1 and n % 100 != 11:
            return "файл"
        if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
            return "файла"
        return "файлов"

    def _open_attachment(self, att_path: Path) -> None:
        if not att_path.exists():
            self._show_toast("Файл не найден", kind="warn")
            self._refresh_attachments()
            return
        try:
            open_in_system(att_path)
        except OSError as exc:
            messagebox.showerror("Не удалось открыть", str(exc))

    def _reveal_attachment(self, att_path: Path) -> None:
        if not att_path.exists():
            self._show_toast("Файл не найден", kind="warn")
            self._refresh_attachments()
            return
        try:
            reveal_in_explorer(att_path)
        except OSError as exc:
            messagebox.showerror("Не удалось открыть проводник", str(exc))

    def _remove_attachment(self, att_path: Path) -> None:
        if not messagebox.askyesno(
            "Удалить вложение", f"Удалить «{att_path.name}»?",
        ):
            return
        try:
            att_path.unlink()
        except OSError as exc:
            messagebox.showerror("Ошибка удаления", str(exc))
            return
        if self.current_path is not None:
            folder = attachments_dir(self.current_path)
            try:
                if folder.exists() and not any(folder.iterdir()):
                    folder.rmdir()
            except OSError:
                pass
        self._refresh_attachments()
        self._show_toast(f"Удалено: {att_path.name}")

    def _refresh_projects(self) -> None:
        for row in self._project_rows:
            row.destroy()
        self._project_rows.clear()
        self._projects_empty_label.pack_forget()

        if not self._current_projects:
            self._projects_empty_label.pack(fill="x", pady=2)
            return

        for project_path in self._current_projects:
            row = self._build_project_row(project_path)
            row.pack(fill="x", pady=2)
            self._project_rows.append(row)

    def _build_project_row(self, project_path: str) -> tk.Frame:
        path = Path(project_path)
        display = path.name or project_path

        row = tk.Frame(self.projects_frame, bg=SURFACE)
        row.columnconfigure(1, weight=1)

        icon = tk.Label(
            row, text="📁", bg=SURFACE, fg=MUTED,
            font=(FONT_FAMILY, 11),
        )
        icon.grid(row=0, column=0, sticky="w", padx=(0, 6))

        name = tk.Label(
            row, text=display, bg=SURFACE, fg=ACCENT,
            font=(FONT_FAMILY, 10), cursor="hand2", anchor="w",
        )
        name.grid(row=0, column=1, sticky="ew")
        name.bind("<Button-1>", lambda e, p=path: self._open_project_folder(p))
        name.bind("<Enter>", lambda e, lbl=name: lbl.configure(fg=ACCENT_HOVER))
        name.bind("<Leave>", lambda e, lbl=name: lbl.configure(fg=ACCENT))

        claude_btn = ttk.Button(
            row, text="claude", style="Subtle.TButton",
            command=lambda p=path: self._launch_claude(p),
            cursor="hand2",
        )
        claude_btn.grid(row=0, column=2, padx=(8, 4))

        remove = tk.Label(
            row, text="×", bg=SURFACE, fg=MUTED,
            font=(FONT_FAMILY, 14), cursor="hand2", padx=6,
        )
        remove.grid(row=0, column=3, sticky="e")
        remove.bind("<Button-1>", lambda e, p=project_path: self._remove_project(p))
        remove.bind("<Enter>", lambda e, lbl=remove: lbl.configure(fg=DANGER))
        remove.bind("<Leave>", lambda e, lbl=remove: lbl.configure(fg=MUTED))

        return row

    def _add_project(self) -> None:
        if self.current_path is None:
            return
        initial = str(PROJECTS_ROOT) if PROJECTS_ROOT.is_dir() else None
        folder = filedialog.askdirectory(
            parent=self, title="Выберите папку проекта",
            initialdir=initial, mustexist=True,
        )
        if not folder:
            return
        path_str = str(Path(folder))
        if path_str in self._current_projects:
            self._show_toast("Проект уже добавлен", kind="warn")
            return
        self._current_projects.append(path_str)
        self._refresh_projects()

    def _remove_project(self, project_path: str) -> None:
        if project_path not in self._current_projects:
            return
        self._current_projects.remove(project_path)
        self._refresh_projects()

    def _open_project_folder(self, path: Path) -> None:
        if not path.is_dir():
            self._show_toast("Папка не найдена", kind="warn")
            return
        try:
            open_in_system(path)
        except OSError as exc:
            messagebox.showerror("Не удалось открыть", str(exc))

    def _launch_claude(self, path: Path) -> None:
        if not path.is_dir():
            self._show_toast("Папка не найдена", kind="warn")
            return
        try:
            launch_claude_in_powershell(path)
        except OSError as exc:
            messagebox.showerror("Не удалось запустить claude", str(exc))
            return
        self._show_toast(f"claude · {path.name}")

    def _update_meta_label(self, meta: dict | None) -> None:
        if meta is None:
            self.dates_label.configure(text="Выберите задачу или создайте новую")
            return
        parts = [f"Создана  {meta['created']}"]
        if meta["completed"]:
            parts.append(f"Выполнена  {meta['completed']}")
        self.dates_label.configure(text="    ·    ".join(parts))

    def _on_list_canvas_resize(self, event: tk.Event) -> None:
        self.list_canvas.itemconfigure(self._list_window, width=event.width)
        new_wrap = max(120, event.width - 60)
        if new_wrap == self._row_wraplength:
            return
        self._row_wraplength = new_wrap
        if self._wraplength_pending:
            return
        self._wraplength_pending = True
        self.after_idle(self._apply_wraplength)

    def _apply_wraplength(self) -> None:
        self._wraplength_pending = False
        new_wrap = self._row_wraplength
        for r in self.list_rows:
            r["title"].configure(wraplength=new_wrap)

    def _request_scrollregion_update(self) -> None:
        if self._scrollregion_pending:
            return
        self._scrollregion_pending = True
        self.after_idle(self._apply_scrollregion)

    def _apply_scrollregion(self) -> None:
        self._scrollregion_pending = False
        bbox = self.list_canvas.bbox("all")
        if bbox:
            self.list_canvas.configure(scrollregion=bbox)

    def _on_list_wheel(self, event: tk.Event) -> None:
        delta = -1 if event.delta > 0 else 1
        self.list_canvas.yview_scroll(delta, "units")

    def _style_row(self, row_data: dict, state: str) -> None:
        is_done = row_data["is_done"]
        signature = (state, is_done)
        if row_data.get("_style_sig") == signature:
            return
        row_data["_style_sig"] = signature
        if state == "selected":
            bg = ACCENT_SOFT
            marker_fg = ACCENT
            title_fg = TEXT if not is_done else MUTED
        elif state == "hover":
            bg = SURFACE_ALT
            marker_fg = ACCENT if is_done else MUTED
            title_fg = MUTED if is_done else TEXT
        else:
            bg = SURFACE
            marker_fg = ACCENT if is_done else MUTED
            title_fg = MUTED if is_done else TEXT
        row_data["row"].configure(bg=bg)
        row_data["accent"].configure(bg=ACCENT if state == "selected" else bg)
        row_data["body"].configure(bg=bg)
        row_data["icon"].configure(bg=bg, fg=marker_fg)
        row_data["title"].configure(bg=bg, fg=title_fg)

    def _on_row_hover(self, path_str: str, entering: bool) -> None:
        if self.selected_path == path_str:
            return
        for r in self.list_rows:
            if r["path"] == path_str:
                self._style_row(r, "hover" if entering else "normal")
                break

    def _make_row(self) -> dict:
        row = tk.Frame(self.list_inner, bg=SURFACE, cursor="hand2")
        row.columnconfigure(1, weight=1)

        accent_bar = tk.Frame(row, bg=SURFACE, width=3, cursor="hand2")
        accent_bar.grid(row=0, column=0, sticky="ns")

        body = tk.Frame(row, bg=SURFACE, cursor="hand2")
        body.grid(row=0, column=1, sticky="ew")
        body.columnconfigure(1, weight=1)

        icon = tk.Label(
            body, bg=SURFACE, font=(FONT_FAMILY, 13),
            width=2, anchor="center", cursor="hand2",
        )
        icon.grid(row=0, column=0, sticky="n", padx=(10, 8), pady=(10, 10))

        title = tk.Label(
            body, bg=SURFACE,
            font=(FONT_FAMILY, 10),
            wraplength=self._row_wraplength,
            justify="left", anchor="w",
            cursor="hand2",
        )
        title.grid(row=0, column=1, sticky="ew", padx=(0, 14), pady=(10, 10))

        row_data: dict = {
            "row": row,
            "accent": accent_bar,
            "body": body,
            "icon": icon,
            "title": title,
            "path": "",
            "is_done": False,
        }

        for w in (row, body, icon, title, accent_bar):
            w.bind("<Button-1>", lambda e, rd=row_data: self._select_path(rd["path"]))
        row.bind("<Enter>", lambda e, rd=row_data: self._on_row_hover(rd["path"], True))
        row.bind("<Leave>", lambda e, rd=row_data: self._on_row_hover(rd["path"], False))

        return row_data

    def _update_row(self, row_data: dict, task: dict) -> None:
        is_done = task["status"] == "done"
        row_data["path"] = str(task["path"])
        row_data["is_done"] = is_done
        row_data["title"].configure(text=task["title"])
        row_data["icon"].configure(text="✓" if is_done else "○")
        state = "selected" if row_data["path"] == self.selected_path else "normal"
        self._style_row(row_data, state)

    def refresh_list(self) -> None:
        previous_selected = self.selected_path

        all_tasks = list_tasks()
        counts = {
            "all": len(all_tasks),
            "pending": sum(1 for t in all_tasks if t["status"] == "pending"),
            "done": sum(1 for t in all_tasks if t["status"] == "done"),
        }
        labels = {"all": "Все", "pending": "Активные", "done": "Сделанные"}
        for value, radio in self.filter_radios.items():
            radio.configure(text=f"  {labels[value]}  ·  {counts[value]}  ")
        self._reflow_filters_if_needed()

        flt = self.filter_var.get()
        query = self.search_var.get().strip().lower()
        visible = [
            t for t in all_tasks
            if (flt == "all" or t["status"] == flt)
            and (not query or query in t["title"].lower())
        ]
        needed = len(visible)
        existing = len(self.list_rows)

        for i in range(min(needed, existing)):
            self._update_row(self.list_rows[i], visible[i])

        for i in range(existing, needed):
            rd = self._make_row()
            rd["row"].pack(side="top", fill="x")
            self.list_rows.append(rd)
            self._update_row(rd, visible[i])

        while len(self.list_rows) > needed:
            rd = self.list_rows.pop()
            rd["row"].destroy()

        if needed == 0:
            self._empty_label.configure(
                text="Ничего не найдено" if query else "Задач нет"
            )
            self._empty_label.pack(fill="x")
        else:
            self._empty_label.pack_forget()

        self._request_scrollregion_update()

        paths = [r["path"] for r in self.list_rows]
        if previous_selected and previous_selected in paths:
            self._select_path(previous_selected, scroll=False)
        else:
            self.selected_path = None
            for rd in self.list_rows:
                self._style_row(rd, "normal")
            self._clear_editor()

    def _select_first_if_any(self) -> None:
        if self.list_rows:
            self._select_path(self.list_rows[0]["path"], scroll=True)

    def _select_path(self, path_str: str, scroll: bool = True) -> None:
        path = Path(path_str)
        if not path.exists():
            self.refresh_list()
            return

        previous = self.selected_path
        self.selected_path = path_str

        new_rd = None
        prev_rd = None
        for r in self.list_rows:
            if r["path"] == path_str:
                new_rd = r
            if previous is not None and r["path"] == previous:
                prev_rd = r
        if prev_rd is not None and prev_rd is not new_rd:
            self._style_row(prev_rd, "normal")
        if new_rd is not None:
            self._style_row(new_rd, "selected")
            if scroll:
                self._scroll_to_row(new_rd["row"])

        meta = parse_task(path)
        self.current_path = path
        self.current_meta = meta
        self._current_projects = list(meta.get("projects", []))
        self._set_editor_enabled(True)
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, path.stem)
        self.body_text.delete("1.0", "end")
        self.body_text.insert("1.0", meta["body"])
        self.done_var.set(meta["status"] == "done")
        self._update_meta_label(meta)
        self._refresh_attachments()
        self._refresh_projects()

    def _scroll_to_row(self, row_widget: tk.Frame) -> None:
        self.list_canvas.update_idletasks()
        bbox = self.list_canvas.bbox("all")
        if not bbox:
            return
        total_h = max(1, bbox[3] - bbox[1])
        try:
            y = row_widget.winfo_y()
        except tk.TclError:
            return
        canvas_h = self.list_canvas.winfo_height()
        view_top, view_bottom = self.list_canvas.yview()
        row_top = y / total_h
        row_bottom = (y + row_widget.winfo_height()) / total_h
        if row_top < view_top:
            self.list_canvas.yview_moveto(row_top)
        elif row_bottom > view_bottom:
            self.list_canvas.yview_moveto(
                max(0, row_bottom - canvas_h / total_h)
            )

    def _clear_editor(self) -> None:
        self.current_path = None
        self.current_meta = None
        self._current_projects = []
        self.title_entry.configure(state="normal")
        self.title_entry.delete(0, "end")
        self.body_text.configure(state="normal")
        self.body_text.delete("1.0", "end")
        self.done_var.set(False)
        self._update_meta_label(None)
        self._set_editor_enabled(False)
        self._refresh_attachments()
        self._refresh_projects()

    def new_task(self) -> None:
        TASKS_DIR.mkdir(exist_ok=True)
        path = unique_path("Новая задача")
        write_task(path, "pending", [], now_str(), "", "")
        if self.filter_var.get() == "done":
            self.filter_var.set("pending")
        self.refresh_list()
        self._select_path(str(path), scroll=True)
        self.title_entry.focus_set()
        self.title_entry.select_range(0, "end")
        self._show_toast("Создана новая задача")

    def save_task(self) -> None:
        if self.current_path is None or self.current_meta is None:
            return
        raw_title = self.title_entry.get().strip()
        if not raw_title:
            messagebox.showwarning("Пустое название", "Введите название задачи.")
            return
        new_name = sanitize_filename(raw_title)
        target = unique_path(new_name, exclude=self.current_path)

        new_status = "done" if self.done_var.get() else "pending"
        old_status = self.current_meta["status"]
        created = self.current_meta["created"]
        completed = self.current_meta["completed"]
        if new_status == "done" and old_status != "done":
            completed = now_str()
        elif new_status == "pending":
            completed = ""

        projects = list(self._current_projects)
        body = self.body_text.get("1.0", "end-1c")
        write_task(self.current_path, new_status, projects, created, completed, body)
        if target != self.current_path:
            old_attach = attachments_dir(self.current_path)
            new_attach = attachments_dir(target)
            if (old_attach.exists() and old_attach != new_attach
                    and new_attach.exists()):
                messagebox.showerror(
                    "Ошибка переименования",
                    f"Папка вложений «{new_attach.name}» уже существует.",
                )
                return
            try:
                self.current_path.rename(target)
            except OSError as exc:
                messagebox.showerror("Ошибка переименования", str(exc))
                return
            if old_attach.exists() and old_attach != new_attach:
                try:
                    old_attach.rename(new_attach)
                except OSError as exc:
                    messagebox.showerror("Ошибка переименования вложений", str(exc))
            self.current_path = target

        self.current_meta = {
            "status": new_status,
            "projects": projects,
            "created": created,
            "completed": completed,
            "body": body,
        }
        kept_path = str(self.current_path)
        self.selected_path = kept_path
        self.refresh_list()
        if self.selected_path == kept_path:
            self._update_meta_label(self.current_meta)
        else:
            self._select_path(kept_path, scroll=True)
        self._show_toast(f"Сохранено: {self.current_path.stem}")

    def delete_task(self) -> None:
        if self.current_path is None:
            return
        title = self.current_path.stem
        if not messagebox.askyesno(
            "Удалить задачу",
            f"Удалить «{title}»?",
        ):
            return
        folder = attachments_dir(self.current_path)
        try:
            self.current_path.unlink()
        except OSError as exc:
            messagebox.showerror("Ошибка удаления", str(exc))
            return
        if folder.exists():
            try:
                shutil.rmtree(folder)
            except OSError as exc:
                messagebox.showwarning(
                    "Не удалось удалить вложения",
                    f"Папка «{folder.name}» осталась: {exc}",
                )
        self.current_path = None
        self.current_meta = None
        self.refresh_list()
        self._show_toast(f"Удалено: {title}")


if __name__ == "__main__":
    App().mainloop()
