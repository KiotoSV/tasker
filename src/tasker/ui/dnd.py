"""Опциональная поддержка drag-and-drop файлов через tkinterdnd2.

Если пакет недоступен — AVAILABLE=False, BaseTk вырождается в обычный tk.Tk."""

import tkinter as tk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    BaseTk = TkinterDnD.Tk
    AVAILABLE = True
except ImportError:
    BaseTk = tk.Tk
    DND_FILES = None
    AVAILABLE = False
