"""Палитра, шрифты и регистрация ttk-стилей.

Светлая тема — четыре тона: кремовый #fffeec холст, графит #222223 текст,
кислотно-жёлтый #cac426 — заливка кнопок и активных пилюль, мягкая
лаванда #bcb4ff — рамки и фон выделений. Тёмная — те же акценты
(жёлтый/лаванда сохраняем), инверсия BG/TEXT/SURFACE_ALT/MUTED.

set_theme() мутирует module-level globals по словарям LIGHT/DARK,
консьюмеры должны обращаться к цветам через квалифицированный доступ
`theme.BG`, а не `from theme import BG` — иначе ловят копию по ссылке
на момент импорта и не видят переключения.
"""

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from tasker.ui.fonts import register_bundled_fonts

register_bundled_fonts()

LIGHT = {
    "BG": "#fffeec",
    "SURFACE": "#fffeec",
    "SURFACE_ALT": "#efeaf9",
    "BORDER": "#bcb4ff",
    "BORDER_STRONG": "#bcb4ff",
    "TEXT": "#222223",
    "MUTED": "#7a7689",
    "ACCENT": "#cac426",
    "HIGHLIGHT": "#bcb4ff",
    "CORK": "#cac426",
    "DANGER": "#cac426",
    "SASH": "#c8c8c8",
    "TITLEBAR": "#c8c8c8",
    "TITLEBAR_TEXT": "#222223",
}

DARK = {
    "BG": "#222223",
    "SURFACE": "#222223",
    "SURFACE_ALT": "#34313f",
    "BORDER": "#bcb4ff",
    "BORDER_STRONG": "#bcb4ff",
    "TEXT": "#fffeec",
    "MUTED": "#8a85a0",
    "ACCENT": "#cac426",
    "HIGHLIGHT": "#bcb4ff",
    "CORK": "#cac426",
    "DANGER": "#cac426",
    "SASH": "#000000",
    "TITLEBAR": "#000000",
    "TITLEBAR_TEXT": "#fffeec",
}

_PALETTES = {"light": LIGHT, "dark": DARK}

CURRENT_THEME = "light"
BG = LIGHT["BG"]
SURFACE = LIGHT["SURFACE"]
SURFACE_ALT = LIGHT["SURFACE_ALT"]
BORDER = LIGHT["BORDER"]
BORDER_STRONG = LIGHT["BORDER_STRONG"]
TEXT = LIGHT["TEXT"]
MUTED = LIGHT["MUTED"]
ACCENT = LIGHT["ACCENT"]
HIGHLIGHT = LIGHT["HIGHLIGHT"]
CORK = LIGHT["CORK"]
DANGER = LIGHT["DANGER"]
SASH = LIGHT["SASH"]
TITLEBAR = LIGHT["TITLEBAR"]
TITLEBAR_TEXT = LIGHT["TITLEBAR_TEXT"]


def set_theme(name: str) -> None:
    """Мутирует module-level цвета согласно выбранной палитре.
    Неизвестное имя — silent fallback на light."""
    palette = _PALETTES.get(name, LIGHT)
    resolved = "dark" if palette is DARK else "light"
    g = globals()
    for key, value in palette.items():
        g[key] = value
    g["CURRENT_THEME"] = resolved

_FONT_PREFERENCES = (
    "halyard-display-variable",
    "Plus Jakarta Sans",
    "Figtree",
    "DM Sans",
    "Segoe UI Variable Display",
    "Segoe UI",
)


def _resolve_font_family() -> str:
    """Возвращает первый установленный шрифт из списка предпочтений.
    Создаёт временный Tk root, если ещё нет — нужен для tkfont.families()."""
    temp_root: tk.Tk | None = None
    try:
        try:
            families = tkfont.families()
        except (tk.TclError, RuntimeError):
            try:
                temp_root = tk.Tk()
                temp_root.withdraw()
            except tk.TclError:
                return "Segoe UI"
            families = tkfont.families()
        available = {name.lower(): name for name in families}
        for candidate in _FONT_PREFERENCES:
            match = available.get(candidate.lower())
            if match:
                return match
        return "Segoe UI"
    finally:
        if temp_root is not None:
            try:
                temp_root.destroy()
            except tk.TclError:
                pass


FONT_FAMILY = _resolve_font_family()

# Type scale, DESIGN.md px → Tkinter pt (1pt ≈ 1.333px @ Windows default DPI).
# DESIGN.md treats this as one continuous family from 10px caption to 51px display.
FONT_CAPTION = (FONT_FAMILY, 9)        # 10–12px utility / small-caps labels
FONT_BODY = (FONT_FAMILY, 11)          # 14px body
FONT_BODY_BOLD = (FONT_FAMILY, 11, "bold")
FONT_SUBHEADING = (FONT_FAMILY, 13)    # 18px subheading
FONT_HEADING_SM = (FONT_FAMILY, 16)    # 24px small heading
FONT_HEADING = (FONT_FAMILY, 20)       # 29px section heading
FONT_HEADING_LG = (FONT_FAMILY, 26)    # 41px in-content title (editor title)
FONT_DISPLAY = (FONT_FAMILY, 32, "bold")  # 51px wordmark — the loudest type on screen


def apply_theme(root: tk.Misc, name: str | None = None) -> None:
    if name is not None:
        set_theme(name)
    root.configure(bg=BG)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=BG, foreground=TEXT, font=FONT_BODY)
    style.configure("TFrame", background=BG)
    style.configure("Surface.TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT, font=FONT_BODY)
    style.configure("Surface.TLabel", background=BG, foreground=TEXT)
    style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=FONT_CAPTION)
    style.configure(
        "Section.TLabel", background=BG, foreground=MUTED, font=FONT_CAPTION
    )
    style.configure(
        "Heading.TLabel", background=BG, foreground=TEXT, font=FONT_HEADING
    )
    style.configure(
        "Display.TLabel", background=BG, foreground=TEXT, font=FONT_DISPLAY
    )
    style.configure(
        "Accent.TLabel", background=BG, foreground=ACCENT, font=FONT_BODY_BOLD
    )

    style.configure(
        "TEntry",
        fieldbackground=BG,
        background=BG,
        foreground=TEXT,
        bordercolor=BORDER_STRONG,
        lightcolor=BORDER_STRONG,
        darkcolor=BORDER_STRONG,
        insertcolor=ACCENT,
        padding=10,
        font=FONT_BODY,
        relief="flat",
    )
    style.configure(
        "Headline.TEntry",
        fieldbackground=BG,
        background=BG,
        foreground=TEXT,
        bordercolor=BG,
        lightcolor=BG,
        darkcolor=BG,
        insertcolor=ACCENT,
        padding=(0, 6),
        font=FONT_HEADING_LG,
        relief="flat",
    )
    style.map(
        "Headline.TEntry",
        bordercolor=[("focus", BG)],
        lightcolor=[("focus", BG)],
        darkcolor=[("focus", BG)],
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", ACCENT)],
        lightcolor=[("focus", ACCENT)],
        darkcolor=[("focus", ACCENT)],
    )

    style.configure(
        "TCombobox",
        fieldbackground=BG,
        background=BG,
        foreground=TEXT,
        bordercolor=BORDER_STRONG,
        lightcolor=BORDER_STRONG,
        darkcolor=BORDER_STRONG,
        arrowcolor=TEXT,
        insertcolor=ACCENT,
        padding=6,
        font=FONT_BODY,
        relief="flat",
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", BG)],
        foreground=[("readonly", TEXT)],
        bordercolor=[("focus", ACCENT), ("active", ACCENT)],
        lightcolor=[("focus", ACCENT)],
        darkcolor=[("focus", ACCENT)],
    )
    root.option_add("*TCombobox*Listbox.background", BG)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", HIGHLIGHT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
    root.option_add("*TCombobox*Listbox.font", FONT_BODY)

    style.configure(
        "Primary.TButton",
        background=CORK,
        foreground=TEXT,
        bordercolor=CORK,
        lightcolor=CORK,
        darkcolor=CORK,
        focusthickness=0,
        padding=(18, 9),
        font=FONT_BODY,
        relief="flat",
    )
    style.map(
        "Primary.TButton",
        background=[("active", CORK), ("pressed", CORK), ("disabled", CORK)],
        bordercolor=[("active", BORDER_STRONG), ("pressed", ACCENT)],
        lightcolor=[("active", BORDER_STRONG), ("pressed", ACCENT)],
        darkcolor=[("active", BORDER_STRONG), ("pressed", ACCENT)],
        foreground=[("disabled", MUTED)],
    )

    style.configure(
        "Subtle.TButton",
        background=BG,
        foreground=TEXT,
        bordercolor=BORDER_STRONG,
        lightcolor=BORDER_STRONG,
        darkcolor=BORDER_STRONG,
        focusthickness=0,
        padding=(12, 6),
        relief="flat",
        font=FONT_BODY,
    )
    style.map(
        "Subtle.TButton",
        background=[("active", BG), ("disabled", BG)],
        bordercolor=[("active", ACCENT), ("disabled", BORDER)],
        lightcolor=[("active", ACCENT)],
        darkcolor=[("active", ACCENT)],
        foreground=[("active", TEXT), ("disabled", MUTED)],
    )

    style.configure(
        "Danger.TButton",
        background=BG,
        foreground=TEXT,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        focusthickness=0,
        padding=(12, 6),
        relief="flat",
        font=FONT_BODY,
    )
    style.map(
        "Danger.TButton",
        background=[("active", BG), ("pressed", BG)],
        bordercolor=[("active", ACCENT), ("pressed", ACCENT)],
        lightcolor=[("active", ACCENT)],
        darkcolor=[("active", ACCENT)],
        foreground=[("disabled", MUTED)],
    )

    style.layout(
        "Filter.TRadiobutton",
        [
            (
                "Radiobutton.padding",
                {
                    "sticky": "nswe",
                    "children": [
                        ("Radiobutton.indicator", {"side": "left", "sticky": ""}),
                        ("Radiobutton.label", {"sticky": "nswe"}),
                    ],
                },
            ),
        ],
    )
    style.configure(
        "Filter.TRadiobutton",
        background=BG,
        foreground=MUTED,
        indicatorrelief="flat",
        indicatordiameter=0,
        padding=(8, 4),
        font=(FONT_FAMILY, 9),
        focuscolor=BG,
    )
    style.map(
        "Filter.TRadiobutton",
        background=[("selected", CORK), ("active", SURFACE_ALT)],
        foreground=[("selected", TEXT), ("active", TEXT)],
    )

    style.configure(
        "TCheckbutton",
        background=BG,
        foreground=TEXT,
        focusthickness=0,
        font=FONT_BODY,
    )
    style.map(
        "TCheckbutton",
        background=[("active", BG)],
        foreground=[("disabled", MUTED)],
    )

    style.configure(
        "Treeview",
        background=BG,
        fieldbackground=BG,
        foreground=TEXT,
        rowheight=34,
        borderwidth=0,
        relief="flat",
        font=FONT_BODY,
    )
    style.map(
        "Treeview",
        background=[("selected", HIGHLIGHT)],
        foreground=[("selected", TEXT)],
    )
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    style.configure("TPanedwindow", background=SASH)
    style.configure("Sash", sashthickness=3, gripcount=0)

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
        background=[("active", HIGHLIGHT)],
    )
