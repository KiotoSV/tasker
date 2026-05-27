"""Платформенные адаптеры: тёмная шапка Windows, открытие файлов и проводника,
запуск PowerShell с claude. Всё кросс-платформенное по возможности."""

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path


def _hex_to_colorref(color_hex: str) -> int:
    """Конвертирует '#RRGGBB' в Win32 COLORREF (0x00BBGGRR)."""
    r = int(color_hex[1:3], 16)
    g = int(color_hex[3:5], 16)
    b = int(color_hex[5:7], 16)
    return r | (g << 8) | (b << 16)


def apply_titlebar_style(
    window: tk.Tk, caption: str, text: str, border: str | None
) -> None:
    """Красит шапку окна заданными цветами через DWM на Windows 11 (build 22000+).
    border=None убирает контур окна (DWMWA_COLOR_NONE = 0xFFFFFFFE).
    На других платформах и старых сборках — тихий no-op."""
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
        hwnd_arg = wintypes.HWND(hwnd)

        # Снимаем immersive-dark, если он был — поверх ляжет наш цвет.
        dark_off = ctypes.c_int(0)
        for attr in (20, 19):
            set_attr(hwnd_arg, wintypes.DWORD(attr),
                     ctypes.byref(dark_off), ctypes.sizeof(dark_off))

        border_value = 0xFFFFFFFE if border is None else _hex_to_colorref(border)
        for attr, value in (
            (35, _hex_to_colorref(caption)),  # DWMWA_CAPTION_COLOR
            (36, _hex_to_colorref(text)),     # DWMWA_TEXT_COLOR
            (34, border_value),               # DWMWA_BORDER_COLOR
        ):
            colorref = ctypes.c_uint(value)
            set_attr(hwnd_arg, wintypes.DWORD(attr),
                     ctypes.byref(colorref), ctypes.sizeof(colorref))
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


def create_desktop_shortcut(target: Path, icon: Path, name: str = "Планнер") -> bool:
    """Создаёт .lnk на рабочем столе через PowerShell. Возвращает True при успехе."""
    if sys.platform != "win32":
        return False
    desktop = Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))
    lnk = desktop / f"{name}.lnk"
    if lnk.exists():
        return True
    ps = (
        '$ws = New-Object -ComObject WScript.Shell; '
        f'$s = $ws.CreateShortcut("{lnk}"); '
        f'$s.TargetPath = "{target}"; '
        f'$s.WorkingDirectory = "{target.parent}"; '
        f'$s.IconLocation = "{icon}"; '
        '$s.Save()'
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=10,
        )
        return lnk.exists()
    except Exception:
        return False


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
