"""Юнит-тесты для чистых хелперов из editor.py — без поднятия Tk."""

from tasker.ui.editor import _plural_files, _small_caps


def test_small_caps_inserts_thin_spaces_between_letters():
    # U+2009 (THIN SPACE) — typographic letter-spacing fallback.
    thin = " "
    assert _small_caps("НАЗВАНИЕ") == thin.join("НАЗВАНИЕ")
    assert _small_caps("ABC") == f"A{thin}B{thin}C"


def test_small_caps_handles_empty_and_single_char():
    assert _small_caps("") == ""
    assert _small_caps("X") == "X"


def test_plural_files_russian_forms():
    # 1, 21, 31, ... — «файл»
    assert _plural_files(1) == "файл"
    assert _plural_files(21) == "файл"
    # 2–4, 22–24, ... — «файла»
    assert _plural_files(2) == "файла"
    assert _plural_files(3) == "файла"
    assert _plural_files(4) == "файла"
    assert _plural_files(22) == "файла"
    # 11–14 — «файлов» (исключение)
    assert _plural_files(11) == "файлов"
    assert _plural_files(12) == "файлов"
    assert _plural_files(14) == "файлов"
    # 5–20, 25–30, ... — «файлов»
    assert _plural_files(5) == "файлов"
    assert _plural_files(10) == "файлов"
    assert _plural_files(100) == "файлов"
