"""Левая панель: вертикальный список задач на Canvas с переиспользованием
строк, hover/selected-стилями, скроллом колесом и автоматическим wraplength."""

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from tasker.ui import theme
from tasker.ui.theme import FONT_BODY, FONT_CAPTION


class TaskListView(tk.Frame):
    """Прокручиваемый список задач. Полностью владеет своей подсветкой;
    оркестратор сообщает ему данные через render() и текущую выделенную строку
    через select(). О клике по строке узнаёт через on_select(path_str)."""

    def __init__(
        self,
        master: tk.Misc,
        on_select: Callable[[str], None],
    ) -> None:
        super().__init__(
            master, bg=theme.BG, highlightthickness=1,
            highlightbackground=theme.BORDER, highlightcolor=theme.BORDER,
        )
        self._on_select = on_select
        self._rows: list[dict] = []
        self._selected_path: str | None = None
        self._row_wraplength = 240
        self._scrollregion_pending = False
        self._wraplength_pending = False
        self._empty_message = "Задач нет"

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, bg=theme.BG, highlightthickness=0, bd=0)
        self._canvas.grid(row=0, column=0, sticky="nsew", padx=(2, 0), pady=2)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        scroll.grid(row=0, column=1, sticky="ns", padx=(0, 2), pady=2)
        self._canvas.configure(yscrollcommand=scroll.set)

        self._inner = tk.Frame(self._canvas, bg=theme.BG)
        self._window = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw",
        )
        self._inner.bind(
            "<Configure>",
            lambda e: self._request_scrollregion_update(),
        )
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self._canvas.bind(
            "<Enter>",
            lambda e: self._canvas.bind_all("<MouseWheel>", self._on_wheel),
        )
        self._canvas.bind(
            "<Leave>",
            lambda e: self._canvas.unbind_all("<MouseWheel>"),
        )

        self._empty_label = tk.Label(
            self._inner, text=self._empty_message,
            bg=theme.BG, fg=theme.MUTED, font=FONT_CAPTION,
            padx=20, pady=24,
        )

    def render(self, items: list[dict]) -> None:
        """Рисует строки списка. Ожидает dict-и с полями path (Path), title (str),
        status (str). Имеющиеся строки переиспользуются."""
        needed = len(items)
        existing = len(self._rows)

        for i in range(min(needed, existing)):
            self._update_row(self._rows[i], items[i])
        for i in range(existing, needed):
            rd = self._make_row()
            rd["row"].pack(side="top", fill="x")
            self._rows.append(rd)
            self._update_row(rd, items[i])
        while len(self._rows) > needed:
            rd = self._rows.pop()
            rd["row"].destroy()

        if needed == 0:
            self._empty_label.configure(text=self._empty_message)
            self._empty_label.pack(fill="x")
        else:
            self._empty_label.pack_forget()

        self._request_scrollregion_update()

    def select(self, path_str: str | None, scroll: bool = True) -> None:
        previous = self._selected_path
        self._selected_path = path_str

        prev_rd = None
        new_rd = None
        for r in self._rows:
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
        elif path_str is None:
            for rd in self._rows:
                self._style_row(rd, "normal")

    def set_empty_message(self, message: str) -> None:
        self._empty_message = message

    def refresh_theme(self) -> None:
        """Перекрашивает все raw-tk виджеты под текущую палитру theme.*"""
        self.configure(
            bg=theme.BG,
            highlightbackground=theme.BORDER,
            highlightcolor=theme.BORDER,
        )
        self._canvas.configure(bg=theme.BG)
        self._inner.configure(bg=theme.BG)
        self._empty_label.configure(bg=theme.BG, fg=theme.MUTED)
        for rd in self._rows:
            rd["_style_sig"] = None  # сброс кэша, иначе ранний return пропустит реконфиг
            state = "selected" if rd["path"] == self._selected_path else "normal"
            self._style_row(rd, state)

    @property
    def selected_path(self) -> str | None:
        return self._selected_path

    @property
    def row_paths(self) -> list[str]:
        return [r["path"] for r in self._rows]

    @property
    def first_row_path(self) -> str | None:
        return self._rows[0]["path"] if self._rows else None

    def _on_canvas_resize(self, event: tk.Event) -> None:
        self._canvas.itemconfigure(self._window, width=event.width)
        new_wrap = max(140, event.width - 80)
        if new_wrap == self._row_wraplength:
            return
        self._row_wraplength = new_wrap
        if self._wraplength_pending:
            return
        self._wraplength_pending = True
        self.after_idle(self._apply_wraplength)

    def _apply_wraplength(self) -> None:
        self._wraplength_pending = False
        for r in self._rows:
            r["title"].configure(wraplength=self._row_wraplength)

    def _request_scrollregion_update(self) -> None:
        if self._scrollregion_pending:
            return
        self._scrollregion_pending = True
        self.after_idle(self._apply_scrollregion)

    def _apply_scrollregion(self) -> None:
        self._scrollregion_pending = False
        bbox = self._canvas.bbox("all")
        if not bbox:
            return
        self._canvas.configure(scrollregion=(0, 0, bbox[2], bbox[3]))

    def _on_wheel(self, event: tk.Event) -> None:
        bbox = self._canvas.bbox("all")
        if not bbox:
            return
        content_h = bbox[3] - bbox[1]
        canvas_h = self._canvas.winfo_height()
        if content_h <= canvas_h:
            return
        delta = -1 if event.delta > 0 else 1
        self._canvas.yview_scroll(delta, "units")

    def _style_row(self, row_data: dict, state: str) -> None:
        is_done = row_data["is_done"]
        is_deferred = row_data["is_deferred"]
        is_muted = is_done or is_deferred
        signature = (state, is_done, is_deferred)
        if row_data.get("_style_sig") == signature:
            return
        row_data["_style_sig"] = signature
        if state == "selected":
            bg = theme.ACCENT
            marker_fg = theme.TEXT
            title_fg = theme.MUTED if is_muted else theme.TEXT
        elif state == "hover":
            bg = theme.SURFACE_ALT
            marker_fg = theme.HIGHLIGHT if is_done else theme.MUTED
            title_fg = theme.MUTED if is_muted else theme.TEXT
        else:
            bg = theme.BG
            marker_fg = theme.HIGHLIGHT if is_done else theme.MUTED
            title_fg = theme.MUTED if is_muted else theme.TEXT
        row_data["row"].configure(bg=bg)
        row_data["accent"].configure(
            bg=theme.HIGHLIGHT if state == "selected" else bg,
        )
        row_data["body"].configure(bg=bg)
        row_data["icon"].configure(bg=bg, fg=marker_fg)
        row_data["title"].configure(bg=bg, fg=title_fg)

    def _on_row_hover(self, path_str: str, entering: bool) -> None:
        if self._selected_path == path_str:
            return
        for r in self._rows:
            if r["path"] == path_str:
                self._style_row(r, "hover" if entering else "normal")
                break

    def _make_row(self) -> dict:
        row = tk.Frame(self._inner, bg=theme.BG, cursor="hand2")
        row.columnconfigure(1, weight=1)

        accent_bar = tk.Frame(row, bg=theme.BG, width=3, cursor="hand2")
        accent_bar.grid(row=0, column=0, sticky="ns")

        body = tk.Frame(row, bg=theme.BG, cursor="hand2")
        body.grid(row=0, column=1, sticky="ew")
        body.columnconfigure(1, weight=1)

        icon = tk.Label(
            body, bg=theme.BG, font=(FONT_BODY[0], 10),
            width=2, anchor="center", cursor="hand2",
        )
        icon.grid(row=0, column=0, sticky="n", padx=(8, 6), pady=(8, 8))

        title = tk.Label(
            body, bg=theme.BG,
            font=(FONT_BODY[0], 10),
            wraplength=self._row_wraplength,
            justify="left", anchor="w",
            cursor="hand2",
        )
        title.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(8, 8))

        row_data: dict = {
            "row": row,
            "accent": accent_bar,
            "body": body,
            "icon": icon,
            "title": title,
            "path": "",
            "is_done": False,
            "is_deferred": False,
        }

        for w in (row, body, icon, title, accent_bar):
            w.bind("<Button-1>", lambda e, rd=row_data: self._on_select(rd["path"]))
        row.bind("<Enter>", lambda e, rd=row_data: self._on_row_hover(rd["path"], True))
        row.bind("<Leave>", lambda e, rd=row_data: self._on_row_hover(rd["path"], False))

        return row_data

    def _update_row(self, row_data: dict, task: dict) -> None:
        status = task["status"]
        is_done = status == "done"
        is_deferred = status == "deferred"
        row_data["path"] = str(task["path"])
        row_data["is_done"] = is_done
        row_data["is_deferred"] = is_deferred
        row_data["title"].configure(text=task["title"])
        if is_done:
            icon_text = "✓"
        elif is_deferred:
            icon_text = "◐"
        else:
            icon_text = "○"
        row_data["icon"].configure(text=icon_text)
        state = "selected" if row_data["path"] == self._selected_path else "normal"
        self._style_row(row_data, state)

    def _scroll_to_row(self, row_widget: tk.Frame) -> None:
        self._canvas.update_idletasks()
        bbox = self._canvas.bbox("all")
        if not bbox:
            return
        total_h = max(1, bbox[3] - bbox[1])
        try:
            y = row_widget.winfo_y()
        except tk.TclError:
            return
        canvas_h = self._canvas.winfo_height()
        view_top, view_bottom = self._canvas.yview()
        row_top = y / total_h
        row_bottom = (y + row_widget.winfo_height()) / total_h
        if row_top < view_top:
            self._canvas.yview_moveto(row_top)
        elif row_bottom > view_bottom:
            self._canvas.yview_moveto(
                max(0, row_bottom - canvas_h / total_h)
            )
