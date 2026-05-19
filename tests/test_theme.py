"""Smoke-проверка палитры темы: цвета совпадают с заявленной палитрой,
шрифт резолвится в непустую строку, set_theme корректно переключает globals.

Все тесты, которые мутируют тему, должны делать teardown в light, иначе
порядок тестов может ломать соседние ассерты на дефолте."""

import pytest

from tasker.ui import theme


@pytest.fixture(autouse=True)
def _reset_theme_to_light():
    """Гарантирует, что каждый тест стартует и завершается на light."""
    theme.set_theme("light")
    yield
    theme.set_theme("light")


def test_palette_matches_brief():
    assert theme.BG == "#fffeec", "canvas — cream"
    assert theme.TEXT == "#222223", "foreground — graphite"
    assert theme.ACCENT == "#cac426", "filled action — yellow"
    assert theme.HIGHLIGHT == "#bcb4ff", "border/state surface — lavender"
    assert theme.CORK == theme.ACCENT, "filled button bg shares yellow accent"
    assert theme.BORDER == "#bcb4ff", "divider — lavender"
    assert theme.BORDER_STRONG == theme.HIGHLIGHT, "interactive border — lavender"


def test_surface_collapses_to_canvas():
    assert theme.SURFACE == theme.BG


def test_danger_shares_accent_hue():
    assert theme.DANGER == theme.ACCENT


def test_font_family_resolves():
    family = theme.FONT_FAMILY
    assert isinstance(family, str) and family, "FONT_FAMILY must resolve"


def test_font_tuples_use_resolved_family():
    assert theme.FONT_BODY[0] == theme.FONT_FAMILY
    assert theme.FONT_CAPTION[0] == theme.FONT_FAMILY
    assert theme.FONT_HEADING[0] == theme.FONT_FAMILY


def test_light_and_dark_palettes_have_same_keys():
    assert set(theme.LIGHT.keys()) == set(theme.DARK.keys())


def test_dark_palette_inverts_bg_text():
    assert theme.DARK["BG"] == "#222223"
    assert theme.DARK["TEXT"] == "#fffeec"
    assert theme.LIGHT["BG"] == "#fffeec"
    assert theme.LIGHT["TEXT"] == "#222223"


def test_accents_preserved_in_dark():
    assert theme.DARK["ACCENT"] == theme.LIGHT["ACCENT"]
    assert theme.DARK["CORK"] == theme.LIGHT["CORK"]
    assert theme.DARK["HIGHLIGHT"] == theme.LIGHT["HIGHLIGHT"]
    assert theme.DARK["BORDER"] == theme.LIGHT["BORDER"]
    assert theme.DARK["DANGER"] == theme.LIGHT["DANGER"]


def test_sash_and_titlebar_swap_between_themes():
    # Светлая — мягко-серая шапка и линия, тёмная — чёрная для контраста.
    assert theme.LIGHT["SASH"] == "#c8c8c8"
    assert theme.LIGHT["TITLEBAR"] == "#c8c8c8"
    assert theme.LIGHT["TITLEBAR_TEXT"] == "#222223"
    assert theme.DARK["SASH"] == "#000000"
    assert theme.DARK["TITLEBAR"] == "#000000"
    assert theme.DARK["TITLEBAR_TEXT"] == "#fffeec"
    theme.set_theme("dark")
    assert theme.SASH == "#000000"
    assert theme.TITLEBAR == "#000000"
    assert theme.TITLEBAR_TEXT == "#fffeec"
    theme.set_theme("light")
    assert theme.SASH == "#c8c8c8"
    assert theme.TITLEBAR == "#c8c8c8"
    assert theme.TITLEBAR_TEXT == "#222223"


def test_set_theme_switches_globals():
    theme.set_theme("dark")
    assert theme.BG == "#222223"
    assert theme.TEXT == "#fffeec"
    assert theme.CURRENT_THEME == "dark"
    theme.set_theme("light")
    assert theme.BG == "#fffeec"
    assert theme.TEXT == "#222223"
    assert theme.CURRENT_THEME == "light"


def test_set_theme_unknown_falls_back_to_light():
    theme.set_theme("dark")
    theme.set_theme("solarized-impossible")
    assert theme.CURRENT_THEME == "light"
    assert theme.BG == "#fffeec"
