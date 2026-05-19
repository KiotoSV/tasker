"""Мелкие переиспользуемые UI-компоненты: Toast, FilterBar, SearchBox,
обработчик Ctrl-шорткатов на любых раскладках."""

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from tasker.ui.theme import (
    ACCENT,
    ACCENT_SOFT,
    BG,
    BORDER,
    DANGER,
    FONT_FAMILY,
    MUTED,
    SURFACE,
    SURFACE_ALT,
    TEXT,
)


class ToastManager:
    """Краткое уведомление в правом верхнем углу окна, автоматически гаснет."""

    _ICONS = {"success": "✓", "info": "•", "warn": "!"}
    _ICON_COLORS = {"success": ACCENT, "info": ACCENT, "warn": DANGER}

    def __init__(self, root: tk.Misc, duration_ms: int = 2200) -> None:
        self._root = root
        self._duration_ms = duration_ms
        self._toast: tk.Widget | None = None
        self._timer: str | None = None

    def show(self, message: str, kind: str = "success") -> None:
        self._cancel_timer()
        self._destroy_current()

        icon = self._ICONS.get(kind, "•")
        icon_fg = self._ICON_COLORS.get(kind, ACCENT)

        toast = tk.Frame(
            self._root, bg=SURFACE_ALT, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=BORDER,
        )
        tk.Label(
            toast, text=icon, bg=SURFACE_ALT, fg=icon_fg,
            font=(FONT_FAMILY, 12, "bold"),
        ).pack(side="left", padx=(14, 8), pady=10)
        tk.Label(
            toast, text=message, bg=SURFACE_ALT, fg=TEXT,
            font=(FONT_FAMILY, 10),
        ).pack(side="left", padx=(0, 16), pady=10)
        toast.place(relx=1.0, rely=0.0, x=-22, y=22, anchor="ne")
        toast.lift()
        self._toast = toast
        self._timer = self._root.after(self._duration_ms, self._hide)

    def _hide(self) -> None:
        self._timer = None
        self._destroy_current()

    def _cancel_timer(self) -> None:
        if self._timer is None:
            return
        try:
            self._root.after_cancel(self._timer)
        except tk.TclError:
            pass
        self._timer = None

    def _destroy_current(self) -> None:
        if self._toast is None:
            return
        try:
            self._toast.destroy()
        except tk.TclError:
            pass
        self._toast = None


class FilterBar(ttk.Frame):
    """Группа радиокнопок «Все / Активные / Сделанные» с авто-переключением
    между горизонтальной и вертикальной раскладкой при узкой ширине."""

    _OPTIONS = (
        ("Все", "all"),
        ("Активные", "pending"),
        ("Отложенные", "deferred"),
        ("Сделанные", "done"),
    )

    def __init__(
        self,
        master: tk.Misc,
        variable: tk.StringVar,
        on_change: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._variable = variable
        self._on_change = on_change
        self._radios: dict[str, ttk.Radiobutton] = {}
        self._vertical = False
        self._horizontal_required = 320

        for label, value in self._OPTIONS:
            self._radios[value] = ttk.Radiobutton(
                self, text=label, value=value,
                style="Filter.TRadiobutton",
                variable=variable, command=on_change,
                cursor="hand2",
            )
        self._apply_layout()
        self.bind("<Configure>", self._on_resize)

    def set_counts(self, counts: dict[str, int]) -> None:
        labels = {value: label for label, value in self._OPTIONS}
        for value, radio in self._radios.items():
            radio.configure(text=f"  {labels[value]}  ·  {counts.get(value, 0)}  ")
        self.reflow_if_needed()

    def reflow_if_needed(self) -> None:
        if self._vertical:
            return
        self._horizontal_required = self._measure_required()
        current = self.winfo_width()
        if current > 1 and current < self._horizontal_required:
            self._vertical = True
            self._apply_layout()

    def _apply_layout(self) -> None:
        for w in self._radios.values():
            w.pack_forget()
        if self._vertical:
            for w in self._radios.values():
                w.pack(side="top", anchor="w", pady=(0, 4))
        else:
            for w in self._radios.values():
                w.pack(side="left", padx=(0, 4))

    def _measure_required(self) -> int:
        if self._vertical:
            return self._horizontal_required
        self.update_idletasks()
        total = sum(w.winfo_reqwidth() for w in self._radios.values())
        total += 4 * (len(self._radios) - 1)
        total += 12
        return total

    def _on_resize(self, event: tk.Event) -> None:
        if event.width <= 1:
            return
        if not self._vertical:
            self._horizontal_required = self._measure_required()
        should_vertical = event.width < self._horizontal_required
        if should_vertical != self._vertical:
            self._vertical = should_vertical
            self._apply_layout()


class SearchBox(tk.Frame):
    """Поле поиска с placeholder, подсветкой фокуса и Escape-очисткой."""

    def __init__(
        self,
        master: tk.Misc,
        variable: tk.StringVar,
        on_change: Callable[[], None],
        placeholder: str = "Поиск",
    ) -> None:
        super().__init__(
            master, bg=SURFACE, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=BORDER,
        )
        self._variable = variable
        self._on_change = on_change

        self._entry = tk.Entry(
            self,
            textvariable=variable,
            bg=SURFACE, fg=TEXT, insertbackground=ACCENT,
            relief="flat", borderwidth=0, highlightthickness=0,
            font=(FONT_FAMILY, 10),
        )
        self._entry.pack(fill="x", padx=12, pady=8)

        self._placeholder = tk.Label(
            self, text=placeholder,
            bg=SURFACE, fg=MUTED,
            font=(FONT_FAMILY, 10),
            cursor="hand2",
        )
        self._placeholder.place(in_=self._entry, relx=0, rely=0.5, x=2, anchor="w")
        self._placeholder.bind("<Button-1>", lambda e: self._entry.focus_set())

        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._entry.bind("<Escape>", lambda e: self.clear())
        variable.trace_add("write", lambda *_: self._on_text_change())

    def clear(self) -> None:
        self._variable.set("")
        self._entry.master.focus_set()

    def _on_text_change(self) -> None:
        if self._variable.get():
            self._placeholder.place_forget()
        else:
            self._placeholder.place(
                in_=self._entry, relx=0, rely=0.5, x=2, anchor="w",
            )
        self._on_change()

    def _on_focus_in(self, _event: tk.Event) -> None:
        self.configure(highlightbackground=ACCENT, highlightcolor=ACCENT)

    def _on_focus_out(self, _event: tk.Event) -> None:
        self.configure(highlightbackground=BORDER, highlightcolor=BORDER)


def select_all_in(widget: tk.Widget) -> None:
    try:
        if isinstance(widget, tk.Text):
            widget.tag_add("sel", "1.0", "end-1c")
            widget.mark_set("insert", "end-1c")
        elif isinstance(widget, (tk.Entry, ttk.Entry)):
            widget.select_range(0, "end")
            widget.icursor("end")
    except tk.TclError:
        pass


class CrossLayoutShortcuts:
    """Ловит Ctrl+C/V/X/A/S на нелатинских раскладках.

    Tk матчит <Control-c> по keysym; на русской раскладке у физической
    клавиши C keysym нелатинский — стандартные биндинги не срабатывают.
    Здесь матчим по keycode (физическая клавиша). На латинской раскладке
    keysym совпадает с ожидаемой буквой — отдаём событие штатному
    обработчику класса виджета.
    """

    _ACTIONS_BY_KEYCODE = {
        67: ("c", lambda w: w.event_generate("<<Copy>>")),
        86: ("v", lambda w: w.event_generate("<<Paste>>")),
        88: ("x", lambda w: w.event_generate("<<Cut>>")),
        65: ("a", select_all_in),
    }

    def __init__(self, root: tk.Misc, on_save: Callable[[], None]) -> None:
        self._on_save = on_save
        root.bind_all("<Control-s>", self._on_ctrl_s)
        root.bind_all("<Control-S>", self._on_ctrl_s)
        root.bind_all("<Control-KeyPress>", self._on_control_keypress)

    def _on_ctrl_s(self, _event: tk.Event) -> str:
        self._on_save()
        return "break"

    def _on_control_keypress(self, event: tk.Event) -> str | None:
        if event.keycode == 83:
            if event.keysym.lower() == "s":
                return None
            self._on_save()
            return "break"
        info = self._ACTIONS_BY_KEYCODE.get(event.keycode)
        if info is None:
            return None
        expected, fn = info
        if event.keysym.lower() == expected:
            return None
        fn(event.widget)
        return "break"
