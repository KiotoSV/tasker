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
from tasker.settings import get_projects_root
from tasker.platform_utils import (
    launch_claude_in_powershell,
    open_in_system,
    reveal_in_explorer,
)
from tasker.ui.dnd import AVAILABLE as DND_AVAILABLE
from tasker.ui.dnd import DND_FILES
from tasker.ui import theme
from tasker.ui.theme import FONT_BODY, FONT_CAPTION, FONT_HEADING
from tasker.ui.widgets import DashedDivider, ToastManager


def _small_caps(text: str) -> str:
    """Имитация letter-spacing для секционных лейблов: вставляем
    тонкие пробелы (U+2009) между символами. Tkinter не поддерживает
    OpenType letter-spacing — это самый честный фоллбэк."""
    return " ".join(text)

_STATUS_LABELS = {
    "pending": "Активна",
    "deferred": "Отложена",
    "done": "Выполнена",
}
_LABEL_TO_STATUS = {v: k for k, v in _STATUS_LABELS.items()}


class _StatusSelector(tk.Frame):
    """Сегментированный селектор статуса: три letter-spaced pill-метки в ряд.
    Активная заполнена CORK с TEXT-цветом, неактивные — прозрачные с MUTED;
    при hover неактивная подсвечивается до TEXT. Заменяет ttk.Combobox —
    DESIGN.md требует видеть все альтернативы одновременно, а не выпадашку."""

    def __init__(
        self,
        master: tk.Misc,
        variable: tk.StringVar,
    ) -> None:
        super().__init__(master, bg=theme.BG)
        self._variable = variable
        self._enabled = True
        self._pills: dict[str, tk.Label] = {}
        for i, label in enumerate(_LABEL_TO_STATUS):
            pill = tk.Label(
                self, text=_small_caps(label.upper()),
                bg=theme.BG, fg=theme.MUTED, font=FONT_CAPTION,
                padx=12, pady=6, cursor="hand2",
            )
            pill.pack(side="left", padx=(0, 4 if i < 2 else 0))
            pill.bind("<Button-1>", lambda _e, lbl=label: self._on_click(lbl))
            pill.bind("<Enter>", lambda _e, lbl=label: self._on_hover(lbl, True))
            pill.bind("<Leave>", lambda _e, lbl=label: self._on_hover(lbl, False))
            self._pills[label] = pill
        variable.trace_add("write", lambda *_: self._refresh())
        self._refresh()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        cursor = "hand2" if enabled else "arrow"
        for pill in self._pills.values():
            pill.configure(cursor=cursor)
        self._refresh()

    def refresh_theme(self) -> None:
        self.configure(bg=theme.BG)
        self._refresh()

    def _on_click(self, label: str) -> None:
        if not self._enabled:
            return
        self._variable.set(label)

    def _on_hover(self, label: str, entering: bool) -> None:
        if not self._enabled:
            return
        if self._variable.get() == label:
            return
        self._pills[label].configure(
            fg=theme.TEXT if entering else theme.MUTED,
        )

    def _refresh(self) -> None:
        current = self._variable.get()
        for label, pill in self._pills.items():
            is_active = label == current
            if is_active and self._enabled:
                pill.configure(bg=theme.CORK, fg=theme.TEXT)
            elif is_active:
                pill.configure(bg=theme.BG, fg=theme.MUTED)
            else:
                pill.configure(bg=theme.BG, fg=theme.MUTED)


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
        super().__init__(master, bg=theme.BG, highlightthickness=1,
                         highlightbackground=theme.BORDER, highlightcolor=theme.BORDER)
        self._toast = toast
        self._on_save = on_save
        self._on_delete = on_delete

        self._current_path: Path | None = None
        self._current_meta: dict | None = None
        self._current_projects: list[str] = []
        self._status_var = tk.StringVar(value=_STATUS_LABELS["pending"])
        self._project_rows: list[tk.Frame] = []
        self._attachment_rows: list[tk.Frame] = []
        # Autohide-скроллбар: невидим по умолчанию, показывается при
        # прокрутке/наведении и прячется после _SCROLL_HIDE_DELAY мс простоя.
        self._scroll_hide_after: str | None = None
        self._scroll_hover = False
        self._scroll_visible = False

        self._build_ui()
        # Изначально стиль уже невидимый из theme.py; синхронизируем флаг,
        # чтобы _show_scroll() сработал при первой прокрутке.
        self._scroll_visible = False
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

    def refresh_theme(self) -> None:
        """Перекрашивает все raw-tk виджеты редактора под текущую палитру."""
        self.configure(
            bg=theme.BG,
            highlightbackground=theme.BORDER,
            highlightcolor=theme.BORDER,
        )
        self._canvas.configure(bg=theme.BG)
        # Стиль Autohide.Vertical.TScrollbar держит BG в большинстве слотов;
        # после set_theme() значения BG/MUTED меняются — переусанавливаем,
        # сохраняя текущий visible/hidden режим.
        if self._scroll_visible:
            ttk.Style().configure(
                "Autohide.Vertical.TScrollbar",
                background=theme.MUTED,
                lightcolor=theme.MUTED, darkcolor=theme.MUTED,
                troughcolor=theme.BG, bordercolor=theme.BG,
            )
        else:
            ttk.Style().configure(
                "Autohide.Vertical.TScrollbar",
                background=theme.BG,
                lightcolor=theme.BG, darkcolor=theme.BG,
                troughcolor=theme.BG, bordercolor=theme.BG,
            )
        for card in (self._project_card, self._attach_card, self._body_card):
            card.configure(
                bg=theme.BG,
                highlightbackground=theme.BORDER,
                highlightcolor=theme.BORDER,
            )
        self._projects_frame.configure(bg=theme.BG)
        self._attachments_frame.configure(bg=theme.BG)
        self._projects_empty_label.configure(bg=theme.BG, fg=theme.MUTED)
        self._attach_empty_label.configure(bg=theme.BG, fg=theme.MUTED)
        self._body_text.configure(
            bg=theme.BG, fg=theme.TEXT, insertbackground=theme.ACCENT,
            selectbackground=theme.CORK, selectforeground=theme.TEXT,
        )
        focused = self._title_entry == self.focus_get()
        self._title_underline.configure(
            bg=theme.ACCENT if focused else theme.BORDER_STRONG,
        )
        self._status_selector.refresh_theme()
        self._divider_top.refresh_theme()
        self._divider_bottom.refresh_theme()
        # Перерисовываем строки вложений и проектов — они захватывают
        # цвета в hover-биндингах через лямбды; пересоздание гарантирует
        # свежие theme.* lookups.
        self._refresh_attachments()
        self._refresh_projects()

    def focus_title(self, select_all: bool = False) -> None:
        self._title_entry.focus_set()
        if select_all:
            self._title_entry.select_range(0, "end")

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Канвас + autohide-скроллбар. Скроллбар занят grid'ом постоянно
        # (чтобы не дёргать раскладку), а его «видимость» — это переключение
        # цветов стиля между BG и MUTED.
        self._canvas = tk.Canvas(
            self, bg=theme.BG, highlightthickness=0, borderwidth=0,
        )
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._scroll = ttk.Scrollbar(
            self, orient="vertical",
            style="Autohide.Vertical.TScrollbar",
            command=self._on_scroll_drag,
        )
        self._scroll.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=self._on_yscroll)

        inner = ttk.Frame(self._canvas, style="Surface.TFrame", padding=(32, 22))
        self._inner = inner
        self._inner_window = self._canvas.create_window(
            (0, 0), window=inner, anchor="nw",
        )
        inner.columnconfigure(0, weight=1)
        inner.rowconfigure(9, weight=1, minsize=160)

        inner.bind(
            "<Configure>",
            lambda _e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._scroll.bind("<Enter>", lambda _e: self._on_scroll_hover(True))
        self._scroll.bind("<Leave>", lambda _e: self._on_scroll_hover(False))
        self.after_idle(self._attach_mousewheel)

        ttk.Label(
            inner, text=_small_caps("НАЗВАНИЕ"), style="Section.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 0))
        self._title_entry = ttk.Entry(
            inner, style="Headline.TEntry", font=FONT_HEADING,
        )
        self._title_entry.grid(row=1, column=0, sticky="ew")

        self._title_underline = tk.Frame(inner, bg=theme.BORDER_STRONG, height=1)
        self._title_underline.grid(row=2, column=0, sticky="ew", pady=(6, 12))
        self._title_entry.bind(
            "<FocusIn>",
            lambda _e: self._title_underline.configure(bg=theme.ACCENT),
        )
        self._title_entry.bind(
            "<FocusOut>",
            lambda _e: self._title_underline.configure(bg=theme.BORDER_STRONG),
        )

        self._status_selector = _StatusSelector(inner, self._status_var)
        self._status_selector.grid(row=3, column=0, sticky="w", pady=(0, 10))

        project_header = ttk.Frame(inner, style="Surface.TFrame")
        project_header.grid(row=4, column=0, sticky="ew", pady=(0, 2))
        project_header.columnconfigure(0, weight=1)
        ttk.Label(
            project_header, text=_small_caps("ПРОЕКТЫ"), style="Section.TLabel",
        ).grid(row=0, column=0, sticky="w")
        self._project_add_button = ttk.Button(
            project_header, text="＋  Добавить проект",
            style="Subtle.TButton", command=self._add_project,
            cursor="hand2",
        )
        self._project_add_button.grid(row=0, column=1, sticky="e")

        self._project_card = tk.Frame(
            inner, bg=theme.BG, highlightthickness=1,
            highlightbackground=theme.BORDER, highlightcolor=theme.BORDER,
        )
        self._project_card.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        self._projects_frame = tk.Frame(self._project_card, bg=theme.BG)
        self._projects_frame.pack(fill="x", padx=10, pady=6)
        self._projects_empty_label = tk.Label(
            self._projects_frame,
            text="Нет проектов",
            bg=theme.BG, fg=theme.MUTED, font=FONT_CAPTION,
            anchor="w",
        )

        self._dates_label = ttk.Label(
            inner, text="", style="Muted.TLabel", anchor="w",
        )
        self._dates_label.grid(row=6, column=0, sticky="ew", pady=(0, 8))

        self._divider_top = DashedDivider(inner)
        self._divider_top.grid(row=7, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(
            inner, text=_small_caps("ОПИСАНИЕ"), style="Section.TLabel",
        ).grid(row=8, column=0, sticky="w", pady=(0, 2))
        self._body_card = tk.Frame(
            inner, bg=theme.BG, highlightthickness=1,
            highlightbackground=theme.BORDER, highlightcolor=theme.BORDER,
        )
        self._body_card.grid(row=9, column=0, sticky="nsew", pady=(0, 12))
        self._body_card.rowconfigure(0, weight=1)
        self._body_card.columnconfigure(0, weight=1)
        self._body_text = tk.Text(
            self._body_card, wrap="word", undo=True, height=1,
            bg=theme.BG, fg=theme.TEXT, insertbackground=theme.ACCENT,
            relief="flat", borderwidth=0, highlightthickness=0,
            padx=10, pady=10, font=FONT_BODY,
            selectbackground=theme.CORK, selectforeground=theme.TEXT,
        )
        self._body_text.grid(row=0, column=0, sticky="nsew")
        body_scroll = ttk.Scrollbar(self._body_card, orient="vertical", command=self._body_text.yview)
        body_scroll.grid(row=0, column=1, sticky="ns")
        self._body_text.configure(yscrollcommand=body_scroll.set)

        attach_header = ttk.Frame(inner, style="Surface.TFrame")
        attach_header.grid(row=10, column=0, sticky="ew", pady=(0, 2))
        attach_header.columnconfigure(0, weight=1)
        ttk.Label(
            attach_header, text=_small_caps("ВЛОЖЕНИЯ"), style="Section.TLabel",
        ).grid(row=0, column=0, sticky="w")
        self._attach_button = ttk.Button(
            attach_header, text="＋  Прикрепить",
            style="Subtle.TButton", command=self._attach_via_dialog,
            cursor="hand2",
        )
        self._attach_button.grid(row=0, column=1, sticky="e")

        self._attach_card = tk.Frame(
            inner, bg=theme.BG, highlightthickness=1,
            highlightbackground=theme.BORDER, highlightcolor=theme.BORDER,
        )
        self._attach_card.grid(row=11, column=0, sticky="ew", pady=(0, 12))
        self._attachments_frame = tk.Frame(self._attach_card, bg=theme.BG)
        self._attachments_frame.pack(fill="x", padx=12, pady=10)
        self._attach_empty_label = tk.Label(
            self._attachments_frame,
            text=("Нет вложений · перетащите файлы сюда"
                  if DND_AVAILABLE else "Нет вложений"),
            bg=theme.BG, fg=theme.MUTED, font=FONT_CAPTION,
            anchor="w",
        )

        self._divider_bottom = DashedDivider(inner)
        self._divider_bottom.grid(row=12, column=0, sticky="ew", pady=(0, 12))

        actions = ttk.Frame(inner, style="Surface.TFrame")
        actions.grid(row=13, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        ttk.Button(
            actions, text="Удалить", style="Action.Danger.TButton", command=self._on_delete,
            cursor="hand2",
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            actions, text="Сохранить", style="Action.Primary.TButton", command=self._on_save,
            cursor="hand2",
        ).grid(row=0, column=1, sticky="e")

    _SCROLL_HIDE_DELAY = 400  # мс простоя до скрытия autohide-скроллбара

    def _on_canvas_configure(self, event: tk.Event) -> None:
        # Тянем ширину inner под канвас, чтобы колонки растягивались как ожидается.
        self._canvas.itemconfigure(self._inner_window, width=event.width)
        # Если содержимое помещается по высоте — фиксируем inner = высоте
        # канваса. Тогда weight=1 на строке 9 (Описание) съест остаток
        # вертикали ровно так же, как до обёртки в Canvas: описание не
        # «раздувается» до натуральной высоты body_text.
        # Если контент длиннее канваса — оставляем естественный размер, и
        # тогда срабатывает прокрутка.
        inner_req_h = self._inner.winfo_reqheight()
        target_h = max(event.height, inner_req_h)
        self._canvas.itemconfigure(self._inner_window, height=target_h)

    def _on_yscroll(self, lo: str, hi: str) -> None:
        self._scroll.set(lo, hi)
        # Если контент полностью помещается — скроллить нечего, прячем.
        try:
            f, l = float(lo), float(hi)
        except ValueError:
            f, l = 0.0, 1.0
        if f <= 0.0 and l >= 1.0:
            self._hide_scroll()
            return
        self._show_scroll()
        self._schedule_hide()

    def _on_scroll_drag(self, *args) -> None:
        self._canvas.yview(*args)
        self._show_scroll()
        self._schedule_hide()

    def _on_scroll_hover(self, entering: bool) -> None:
        self._scroll_hover = entering
        if entering:
            if self._scroll_hide_after is not None:
                self.after_cancel(self._scroll_hide_after)
                self._scroll_hide_after = None
            self._show_scroll()
        else:
            self._schedule_hide()

    def _show_scroll(self) -> None:
        if self._scroll_visible:
            return
        self._scroll_visible = True
        ttk.Style().configure(
            "Autohide.Vertical.TScrollbar",
            background=theme.MUTED,
            lightcolor=theme.MUTED,
            darkcolor=theme.MUTED,
        )

    def _hide_scroll(self) -> None:
        if not self._scroll_visible:
            return
        self._scroll_visible = False
        ttk.Style().configure(
            "Autohide.Vertical.TScrollbar",
            background=theme.BG,
            lightcolor=theme.BG,
            darkcolor=theme.BG,
        )

    def _schedule_hide(self) -> None:
        if self._scroll_hover:
            return
        if self._scroll_hide_after is not None:
            self.after_cancel(self._scroll_hide_after)
        self._scroll_hide_after = self.after(
            self._SCROLL_HIDE_DELAY, self._hide_scroll_tick,
        )

    def _hide_scroll_tick(self) -> None:
        self._scroll_hide_after = None
        if self._scroll_hover:
            return
        self._hide_scroll()

    def _attach_mousewheel(self) -> None:
        """Колесо мыши приходит виджету под курсором, поэтому слушаем на
        toplevel и сами решаем, скроллить ли наш канвас. Если курсор внутри
        редактора, но не над body_text (у Text свой class-binding), крутим
        канвас и подсвечиваем скроллбар на время прокрутки."""
        try:
            top = self.winfo_toplevel()
        except tk.TclError:
            return
        top.bind("<MouseWheel>", self._on_mousewheel, add="+")

    def _on_mousewheel(self, event: tk.Event) -> None:
        try:
            target = self.winfo_containing(event.x_root, event.y_root)
        except tk.TclError:
            return
        in_editor = False
        in_body = False
        cur = target
        while cur is not None:
            if cur is self._body_text:
                in_body = True
            if cur is self:
                in_editor = True
                break
            cur = getattr(cur, "master", None)
        if not in_editor or in_body:
            return
        self._canvas.yview_scroll(int(-event.delta / 120), "units")

    def _set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self._title_entry.configure(state=state)
        self._body_text.configure(state=state)
        self._status_selector.set_enabled(enabled)
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
        row = tk.Frame(self._attachments_frame, bg=theme.BG)
        row.columnconfigure(1, weight=1)

        icon = tk.Label(
            row, text="📎", bg=theme.BG, fg=theme.MUTED,
            font=(FONT_BODY[0], 11),
        )
        icon.grid(row=0, column=0, sticky="w", padx=(0, 6))

        name = tk.Label(
            row, text=att_path.name, bg=theme.BG, fg=theme.TEXT,
            font=(FONT_BODY[0], FONT_BODY[1], "underline"),
            cursor="hand2", anchor="w",
        )
        name.grid(row=0, column=1, sticky="ew")
        name.bind("<Button-1>", lambda e, p=att_path: self._open_attachment(p))
        name.bind("<Button-3>", lambda e, p=att_path: self._reveal_attachment(p))
        name.bind("<Enter>", lambda e, lbl=name: lbl.configure(fg=theme.ACCENT))
        name.bind("<Leave>", lambda e, lbl=name: lbl.configure(fg=theme.TEXT))

        remove = tk.Label(
            row, text="×", bg=theme.BG, fg=theme.MUTED,
            font=(FONT_BODY[0], 14), cursor="hand2", padx=6,
        )
        remove.grid(row=0, column=2, sticky="e")
        remove.bind("<Button-1>", lambda e, p=att_path: self._remove_attachment(p))
        remove.bind("<Enter>", lambda e, lbl=remove: lbl.configure(fg=theme.DANGER))
        remove.bind("<Leave>", lambda e, lbl=remove: lbl.configure(fg=theme.MUTED))

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

        row = tk.Frame(self._projects_frame, bg=theme.BG)
        row.columnconfigure(1, weight=1)

        icon = tk.Label(
            row, text="📁", bg=theme.BG, fg=theme.MUTED,
            font=(FONT_BODY[0], 11),
        )
        icon.grid(row=0, column=0, sticky="w", padx=(0, 6))

        name = tk.Label(
            row, text=display, bg=theme.BG, fg=theme.TEXT,
            font=(FONT_BODY[0], FONT_BODY[1], "underline"),
            cursor="hand2", anchor="w",
        )
        name.grid(row=0, column=1, sticky="ew")
        name.bind("<Button-1>", lambda e, p=path: self._open_project_folder(p))
        name.bind("<Enter>", lambda e, lbl=name: lbl.configure(fg=theme.ACCENT))
        name.bind("<Leave>", lambda e, lbl=name: lbl.configure(fg=theme.TEXT))

        claude_btn = ttk.Button(
            row, text="claude", style="Subtle.TButton",
            command=lambda p=path: self._launch_claude(p),
            cursor="hand2",
        )
        claude_btn.grid(row=0, column=2, padx=(8, 4))

        remove = tk.Label(
            row, text="×", bg=theme.BG, fg=theme.MUTED,
            font=(FONT_BODY[0], 14), cursor="hand2", padx=6,
        )
        remove.grid(row=0, column=3, sticky="e")
        remove.bind("<Button-1>", lambda e, p=project_path: self._remove_project(p))
        remove.bind("<Enter>", lambda e, lbl=remove: lbl.configure(fg=theme.DANGER))
        remove.bind("<Leave>", lambda e, lbl=remove: lbl.configure(fg=theme.MUTED))

        return row

    def _add_project(self) -> None:
        if self._current_path is None:
            return
        projects_root = get_projects_root()
        initial = str(projects_root) if projects_root.is_dir() else None
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
