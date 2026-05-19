"""Главное окно: компоновка панелей, делегирование событий, CRUD задач."""

import shutil
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from tasker.attachments import attachments_dir
from tasker.config import ICON_PATH, TASKS_DIR
from tasker.platform_utils import apply_dark_titlebar
from tasker.tasks import (
    TaskRepository,
    now_str,
    parse_task,
    sanitize_filename,
    write_task,
)
from tasker.ui.dnd import BaseTk
from tasker.ui.editor import EditorPanel
from tasker.ui.task_list import TaskListView
from tasker.ui.theme import apply_theme
from tasker.ui.widgets import (
    CrossLayoutShortcuts,
    FilterBar,
    SearchBox,
    ToastManager,
)


class App(BaseTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Планнер")
        self.geometry("1280x820")
        self.minsize(760, 480)
        if ICON_PATH.exists():
            try:
                self.iconbitmap(default=str(ICON_PATH))
            except tk.TclError:
                pass

        self.repo = TaskRepository(TASKS_DIR)
        self.filter_var = tk.StringVar(value="pending")
        self.search_var = tk.StringVar(value="")
        self._sash_initialized = False

        apply_theme(self)
        self._toast_mgr = ToastManager(self)
        self._build_ui()
        TASKS_DIR.mkdir(exist_ok=True)
        self.refresh_list()
        self._select_first_if_any()
        self.update_idletasks()
        apply_dark_titlebar(self)
        self.bind("<Map>", lambda e: apply_dark_titlebar(self), add="+")
        self._init_sash()
        self._paned.bind("<Map>", lambda e: self._init_sash())
        self._paned.bind("<Configure>", self._on_paned_configure)
        CrossLayoutShortcuts(self, self.save_task)

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

        self.search_box = SearchBox(
            left, variable=self.search_var, on_change=self.refresh_list,
            placeholder="Поиск по названию",
        )
        self.search_box.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        self.filter_bar = FilterBar(
            left, variable=self.filter_var, on_change=self.refresh_list,
        )
        self.filter_bar.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        self.task_list = TaskListView(left, on_select=self._select_path)
        self.task_list.grid(row=4, column=0, sticky="nsew")

        paned.add(left, weight=0)

        right_wrap = ttk.Frame(paned, padding=(6, 20, 20, 20))
        right_wrap.rowconfigure(0, weight=1)
        right_wrap.columnconfigure(0, weight=1)

        self.editor = EditorPanel(
            right_wrap,
            toast=self._toast_mgr,
            on_save=self.save_task,
            on_delete=self.delete_task,
        )
        self.editor.grid(row=0, column=0, sticky="nsew")

        paned.add(right_wrap, weight=1)

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
        except tk.TclError:
            return
        try:
            actual = self._paned.sashpos(0)
        except tk.TclError:
            actual = -1
        if actual >= 100:
            self._sash_initialized = True

    def _on_paned_configure(self, event: tk.Event) -> None:
        if self._sash_initialized:
            return
        self._init_sash()

    def refresh_list(self) -> None:
        previous_selected = self.task_list.selected_path

        all_tasks = self.repo.list_tasks()
        counts = {
            "all": len(all_tasks),
            "pending": sum(1 for t in all_tasks if t["status"] == "pending"),
            "deferred": sum(1 for t in all_tasks if t["status"] == "deferred"),
            "done": sum(1 for t in all_tasks if t["status"] == "done"),
        }
        self.filter_bar.set_counts(counts)

        flt = self.filter_var.get()
        query = self.search_var.get().strip().lower()
        visible = [
            t for t in all_tasks
            if (flt == "all" or t["status"] == flt)
            and (not query or query in t["title"].lower())
        ]
        self.task_list.set_empty_message(
            "Ничего не найдено" if query else "Задач нет"
        )
        self.task_list.render(visible)

        if previous_selected and previous_selected in self.task_list.row_paths:
            self._select_path(previous_selected, scroll=False)
        else:
            self.task_list.select(None)
            self.editor.clear()

    def _select_first_if_any(self) -> None:
        first = self.task_list.first_row_path
        if first is not None:
            self._select_path(first, scroll=True)

    def _select_path(self, path_str: str, scroll: bool = True) -> None:
        path = Path(path_str)
        if not path.exists():
            self.refresh_list()
            return
        self.task_list.select(path_str, scroll=scroll)
        self.editor.load(path, parse_task(path))

    def new_task(self) -> None:
        TASKS_DIR.mkdir(exist_ok=True)
        path = self.repo.unique_path("Новая задача")
        write_task(path, "pending", [], now_str(), "", "")
        if self.filter_var.get() not in ("all", "pending"):
            self.filter_var.set("pending")
        self.refresh_list()
        self._select_path(str(path), scroll=True)
        self.editor.focus_title(select_all=True)
        self._toast_mgr.show("Создана новая задача")

    def save_task(self) -> None:
        current_path = self.editor.current_path
        current_meta = self.editor.current_meta
        if current_path is None or current_meta is None:
            return
        raw_title = self.editor.title_text()
        if not raw_title:
            messagebox.showwarning("Пустое название", "Введите название задачи.")
            return
        new_name = sanitize_filename(raw_title)
        target = self.repo.unique_path(new_name, exclude=current_path)

        new_status = self.editor.current_status()
        old_status = current_meta["status"]
        created = current_meta["created"]
        completed = current_meta["completed"]
        if new_status == "done" and old_status != "done":
            completed = now_str()
        elif new_status != "done":
            completed = ""

        projects = self.editor.current_projects
        body = self.editor.body_text()
        write_task(current_path, new_status, projects, created, completed, body)
        if target != current_path:
            old_attach = attachments_dir(current_path)
            new_attach = attachments_dir(target)
            if (old_attach.exists() and old_attach != new_attach
                    and new_attach.exists()):
                messagebox.showerror(
                    "Ошибка переименования",
                    f"Папка вложений «{new_attach.name}» уже существует.",
                )
                return
            try:
                current_path.rename(target)
            except OSError as exc:
                messagebox.showerror("Ошибка переименования", str(exc))
                return
            if old_attach.exists() and old_attach != new_attach:
                try:
                    old_attach.rename(new_attach)
                except OSError as exc:
                    messagebox.showerror("Ошибка переименования вложений", str(exc))
            self.editor.update_path(target)
            current_path = target

        self.editor.update_meta({
            "status": new_status,
            "projects": projects,
            "created": created,
            "completed": completed,
            "body": body,
        })
        kept_path = str(current_path)
        self.task_list.select(kept_path)
        self.refresh_list()
        if self.task_list.selected_path == kept_path:
            self.editor.refresh_meta_label()
        else:
            self._select_path(kept_path, scroll=True)
        self._toast_mgr.show(f"Сохранено: {current_path.stem}")

    def delete_task(self) -> None:
        current_path = self.editor.current_path
        if current_path is None:
            return
        title = current_path.stem
        if not messagebox.askyesno(
            "Удалить задачу",
            f"Удалить «{title}»?",
        ):
            return
        folder = attachments_dir(current_path)
        try:
            current_path.unlink()
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
        self.editor.clear()
        self.refresh_list()
        self._toast_mgr.show(f"Удалено: {title}")
