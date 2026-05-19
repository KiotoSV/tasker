"""Проверка bundled-шрифтов: файл на месте, регистрация идемпотентна,
на не-Windows тихо no-op'ит."""

import sys
from pathlib import Path

from tasker.ui import fonts


def test_bundled_ttf_present():
    ttf = Path(fonts.__file__).parent / "fonts" / "PlusJakartaSans-Variable.ttf"
    assert ttf.is_file(), "PlusJakartaSans-Variable.ttf должен лежать в репо"
    # Sanity: variable .ttf обычно > 100KB; защита от случайного пустого
    # файла в pre-commit или артефакта.
    assert ttf.stat().st_size > 50_000


def test_register_is_idempotent():
    # _registered guard защищает от повторных вызовов AddFontResourceExW.
    fonts.register_bundled_fonts()
    fonts.register_bundled_fonts()
    assert fonts._registered is True


def test_resolved_font_is_jakarta_on_windows():
    """На Windows bundled Plus Jakarta Sans должен подхватиться раньше
    Segoe UI в цепочке предпочтений theme._FONT_PREFERENCES."""
    if sys.platform != "win32":
        return
    from tasker.ui import theme

    assert theme.FONT_FAMILY == "Plus Jakarta Sans", (
        f"ожидался bundled-шрифт, получили {theme.FONT_FAMILY!r}"
    )
