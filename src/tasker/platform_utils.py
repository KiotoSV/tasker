"""Платформенные адаптеры: тёмная шапка Windows, открытие файлов и проводника,
запуск PowerShell с claude. Всё кросс-платформенное по возможности."""

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path


def apply_dark_titlebar(window: tk.Tk) -> None:
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
