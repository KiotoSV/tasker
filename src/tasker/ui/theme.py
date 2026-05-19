"""Палитра, шрифты и регистрация ttk-стилей."""

import tkinter as tk
from tkinter import ttk

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


def apply_theme(root: tk.Misc) -> None:
    root.configure(bg=BG)
    style = ttk.Style(root)
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
