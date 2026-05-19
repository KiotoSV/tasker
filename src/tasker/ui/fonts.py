"""Регистрация bundled-шрифтов в процессе.

DESIGN.md требует halyard-display-variable; legal-open субститут — Plus Jakarta
Sans (OFL). Чтобы не зависеть от установки в системе, кладём .ttf рядом с
кодом и подгружаем через WinAPI AddFontResourceExW с флагом FR_PRIVATE —
шрифт виден только нашему процессу, install в Windows не нужен.

Вызывать ДО создания корневого Tk-окна: tkinter кеширует список семейств
при инициализации Tcl, поэтому шрифты, зарегистрированные позже, могут не
подхватиться в ttk.Style."""

import sys
from pathlib import Path

_FONTS_DIR = Path(__file__).resolve().parent / "fonts"
_BUNDLED = ("PlusJakartaSans-Variable.ttf",)

_registered = False


def register_bundled_fonts() -> None:
    """Подгружает .ttf из ui/fonts/ в процесс. Идемпотентно. Тихо игнорирует
    ошибки — на macOS/Linux или при отсутствии файла приложение продолжит
    работать с системным фоллбэком."""
    global _registered
    if _registered:
        return
    _registered = True
    if sys.platform != "win32":
        return
    try:
        import ctypes
    except ImportError:
        return
    try:
        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    except OSError:
        return
    FR_PRIVATE = 0x10
    for name in _BUNDLED:
        path = _FONTS_DIR / name
        if not path.is_file():
            continue
        try:
            gdi32.AddFontResourceExW(str(path), FR_PRIVATE, 0)
        except OSError:
            pass
