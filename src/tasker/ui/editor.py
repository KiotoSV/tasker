"""Правая панель: форма редактирования одной задачи.

Владеет состоянием отображаемой задачи (current_path, current_meta,
current_projects) и виджетами полей. Файловую работу (rename, write_task)
не делает — это ответственность оркестратора. Сообщает наружу через
on_save / on_delete колбэки."""

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from tasker.attachments import (
    attachments_dir,
    copy_attachment,
    list_attachments,
    parse_dnd_paths,
)
from tasker.config import PROJECTS_ROOT
from tasker.platform_utils import (
    launch_claude_in_powershell,
    open_in_system,
    reveal_in_explorer,
)
from tasker.ui.dnd import AVAILABLE as DND_AVAILABLE
from tasker.ui.dnd import DND_FILES
from tasker.ui.theme import (
    ACCENT,
    ACCENT_HOVER,
    ACCENT_SOFT,
    BORDER,
    DANGER,
    FONT_FAMILY,
    MUTED,
    SURFACE,
    TEXT,
)
from tasker.ui.widgets import ToastManager

_STATUS_LABELS = {
    "pending": "Активна",
    "deferred": "Отложена",
    "done": "Выполнена",
}
_LABEL_TO_STATUS = {v: k for k, v in _STATUS_LABELS.items()}


def _plural_files(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "файл"
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return "файла"
    return "файлов"


class EditorPanel(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        *,
        toast: ToastManager,
        on_save: Callable[[], None],
        on_delete: Callable[[], None],
    ) -> None:
        super().__init__(master, bg=SURFACE, highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=BORDER)
        self._toast = toast
        self._on_save = on_save
        self._on_delete = on_delete

        self._current_path: Path | None = None
        self._current_meta: dict | None = None
        self._current_projects: list[str] = []
        self._status_var = tk.StringVar(value=_STATUS_LABELS["pending"])
        self._project_rows: list[tk.Frame] = []
        self._attachment_rows: list[tk.Frame] = []

        self._build_ui()
        self._set_enabled(False)
        self._update_meta_label(None)
        self._refresh_attachments()
        self._refresh_projects()
        if DND_AVAILABLE:
            for widget in (self._attach_card, self._attachments_frame, self._body_text):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_files_dropped)

    @property
    def current_path(self) -> Path | None:
        return self._current_path

    @property
    def current_meta(self) -> dict | None:
        return self._current_meta

    @property
    def current_projects(self) -> list[str]:
        return list(self._current_projects)

    def title_text(self) -> str:
        return self._title_entry.get().strip()

    def body_text(self) -> str:
        return self._body_text.get("1.0", "end-1c")

    def current_status(self) -> str:
        return _LABEL_TO_STATUS.get(self._status_var.get(), "pending")

    def load(self, path: Path, meta: dict) -> None:
        self._current_path = path
        self._current_meta = meta
        self._current_projects = list(meta.get("projects", []))
        self._set_enabled(True)
        self._title_entry.delete(0, "end")
        self._title_entry.insert(0, path.stem)
        self._body_text.delete("1.0", "end")
        self._body_text.insert("1.0", meta["body"])
        self._status_var.set(_STATUS_LABELS.get(meta["status"], _STATUS_LABELS["pending"]))
        self._update_meta_label(meta)
        self._refresh_attachments()
        self._refresh_projects()

    def clear(self) -> None:
        self._current_path = None
        self._current_meta = None
        self._current_projects = []
        self._title_entry.configure(state="normal")
        self._title_entry.delete(0, "end")
        self._body_text.configure(state="normal")
        self._body_text.delete("1.0", "end")
        self._status_var.set(_STATUS_LABELS["pending"])
        self._update_meta_label(None)
        self._set_enabled(False)
        self._refresh_attachments()
        self._refresh_projects()

    def update_path(self, path: Path) -> None:
        self._current_path = path
        self._title_entry.delete(0, "end")
        self._title_entry.insert(0, path.stem)

    def update_meta(self, meta: dict) -> None:
        self._current_meta = meta
        self._update_meta_label(meta)

    def refresh_meta_label(self) -> None:
        self._update_meta_label(self._current_meta)

    def focus_title(self, select_all: bool = False) -> None:
        self._title_entry.focus_set()
        if select_all:
            self._title_entry.select_range(0, "end")

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        inner = ttk.Frame(self, style="Surface.TFrame", padding=22)
        inner.grid(row=0, column=0, sticky="nsew")
        inner.columnconfigure(0, weight=1)
        inner.rowconfigure(6, weight=1)

        ttk.Label(inner, text="НАЗВАНИЕ", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        title_row = ttk.Frame(inner, style="Surface.TFrame")
        title_row.grid(row=1, column=0, sticky="ew", pady=(4, 12))
        title_row.columnconfigure(0, weight=1)
        self._title_entry = ttk.Entry(title_row)
        self._title_entry.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self._status_combo = ttk.Combobox(
            title_row, textvariable=self._status_var, state="readonly",
            values=list(_LABEL_TO_STATUS), width=12, cursor="hand2",
        )
        self._status_combo.grid(row=0, column=1, sticky="e")

        project_header = ttk.Frame(inner, style="Surface.TFrame")
        project_header.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        project_header.columnconfigure(0, weight=1)
        ttk.Label(
            project_header, text="ПРОЕКТЫ", style="Section.TLabel",
        ).grid(row=0, column=0, sticky="w")
        self._project_add_button = ttk.Button(
            project_header, text="＋  Добавить проект",
            style="Subtle.TButton", command=self._add_project,
            cursor="hand2",
        )
        self._project_add_button.grid(row=0, column=1, sticky="e")

        self._project_card = tk.Frame(
            inner, bg=SURFACE, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=BORDER,
        )
        self._project_card.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        self._projects_frame = tk.Frame(self._project_card, bg=SURFACE)
        self._projects_frame.pack(fill="x", padx=10, pady=8)
        self._projects_empty_label = tk.Label(
            self._projects_frame,
            text="Нет проектов",
            bg=SURFACE, fg=MUTED, font=(FONT_FAMILY, 9),
            anchor="w",
        )

        self._dates_label = ttk.Label(
            inner, text="", style="Muted.TLabel", anchor="w",
        )
        self._dates_label.grid(row=4, column=0, sticky="ew", pady=(0, 12))

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
        self._body_text = tk.Text(
            body_card, wrap="word", undo=True,
            bg=SURFACE, fg=TEXT, insertbackground=ACCENT,
            relief="flat", borderwidth=0, highlightthickness=0,
            padx=10, pady=10, font=(FONT_FAMILY, 10),
            selectbackground=ACCENT_SOFT, selectforeground=ACCENT,
        )
        self._body_text.grid(row=0, column=0, sticky="nsew")
        body_scroll = ttk.Scrollbar(body_card, orient="vertical", command=self._body_text.yview)
        body_scroll.grid(row=0, column=1, sticky="ns")
        self._body_text.configure(yscrollcommand=body_scroll.set)

        attach_header = ttk.Frame(inner, style="Surface.TFrame")
        attach_header.grid(row=7, column=0, sticky="ew", pady=(0, 4))
        attach_header.columnconfigure(0, weight=1)
        ttk.Label(
            attach_header, text="ВЛОЖЕНИЯ", style="Section.TLabel",
        ).grid(row=0, column=0, sticky="w")
        self._attach_button = ttk.Button(
            attach_header, text="＋  Прикрепить",
            style="Subtle.TButton", command=self._attach_via_dialog,
            cursor="hand2",
        )
        self._attach_button.grid(row=0, column=1, sticky="e")

        self._attach_card = tk.Frame(
            inner, bg=SURFACE, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=BORDER,
        )
        self._attach_card.grid(row=8, column=0, sticky="ew", pady=(0, 14))
        self._attachments_frame = tk.Frame(self._attach_card, bg=SURFACE)
        self._attachments_frame.pack(fill="x", padx=10, pady=8)
        self._attach_empty_label = tk.Label(
            self._attachments_frame,
            text=("Нет вложений · перетащите файлы сюда"
                  if DND_AVAILABLE else "Нет вложений"),
            bg=SURFACE, fg=MUTED, font=(FONT_FAMILY, 9),
            anchor="w",
        )

        actions = ttk.Frame(inner, style="Surface.TFrame")
        actions.grid(row=9, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        ttk.Button(
            actions, text="Удалить", style="Danger.TButton", command=self._on_delete,
            cursor="hand2",
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            actions, text="Сохранить", style="Primary.TButton", command=self._on_save,
            cursor="hand2",
        ).grid(row=0, column=1, sticky="e")

    def _set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self._title_entry.configure(state=state)
        self._body_text.configure(state=state)
        self._status_combo.configure(state="readonly" if enabled else "disabled")
        self._attach_button.configure(state=state)
        self._project_add_button.configure(state=state)

    def _update_meta_label(self, meta: dict | None) -> None:
        if meta is None:
            self._dates_label.configure(text="Выберите задачу или создайте новую")
            return
        parts = [f"Создана  {meta['created']}"]
        if meta["completed"]:
            parts.append(f"Выполнена  {meta['completed']}")
        self._dates_label.configure(text="    ·    ".join(parts))

    def _refresh_attachments(self) -> None:
        for row in self._attachment_rows:
            row.destroy()
        self._attachment_rows.clear()
        self._attach_empty_label.pack_forget()

        items = list_attachments(self._current_path) if self._current_path else []
        if not items:
            self._attach_empty_label.pack(fill="x", pady=2)
            return

        for att in items:
            row = self._build_attachment_row(att)
            row.pack(fill="x", pady=2)
            self._attachment_rows.append(row)

    def _build_attachment_row(self, att_path: Path) -> tk.Frame:
        row = tk.Frame(self._attachments_frame, bg=SURFACE)
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
        if self._current_path is None:
            return
        paths = filedialog.askopenfilenames(
            parent=self, title="Выберите файлы для прикрепления",
        )
        self._attach_paths([Path(p) for p in paths])

    def _on_files_dropped(self, event) -> None:
        if self._current_path is None:
            self._toast.show("Сначала выберите задачу", kind="warn")
            return
        self._attach_paths(parse_dnd_paths(event.data))

    def _attach_paths(self, sources: list[Path]) -> None:
        if self._current_path is None or not sources:
            return
        added = 0
        skipped = 0
        for src in sources:
            if not src.is_file():
                skipped += 1
                continue
            try:
                copy_attachment(self._current_path, src)
                added += 1
            except OSError as exc:
                messagebox.showerror("Ошибка прикрепления", f"{src.name}: {exc}")
        self._refresh_attachments()
        if added:
            self._toast.show(f"Прикреплено: {added} {_plural_files(added)}")
        if skipped and not added:
            self._toast.show("Папки не прикрепляются", kind="warn")

    def _open_attachment(self, att_path: Path) -> None:
        if not att_path.exists():
            self._toast.show("Файл не найден", kind="warn")
            self._refresh_attachments()
            return
        try:
            open_in_system(att_path)
        except OSError as exc:
            messagebox.showerror("Не удалось открыть", str(exc))

    def _reveal_attachment(self, att_path: Path) -> None:
        if not att_path.exists():
            self._toast.show("Файл не найден", kind="warn")
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
        if self._current_path is not None:
            folder = attachments_dir(self._current_path)
            try:
                if folder.exists() and not any(folder.iterdir()):
                    folder.rmdir()
            except OSError:
                pass
        self._refresh_attachments()
        self._toast.show(f"Удалено: {att_path.name}")

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

        row = tk.Frame(self._projects_frame, bg=SURFACE)
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
        if self._current_path is None:
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
            self._toast.show("Проект уже добавлен", kind="warn")
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
            self._toast.show("Папка не найдена", kind="warn")
            return
        try:
            open_in_system(path)
        except OSError as exc:
            messagebox.showerror("Не удалось открыть", str(exc))

    def _launch_claude(self, path: Path) -> None:
        if not path.is_dir():
            self._toast.show("Папка не найдена", kind="warn")
            return
        try:
            launch_claude_in_powershell(path)
        except OSError as exc:
            messagebox.showerror("Не удалось запустить claude", str(exc))
            return
        self._toast.show(f"claude · {path.name}")
