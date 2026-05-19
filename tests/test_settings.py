"""Юнит-тесты для persistence в settings.py: round-trip и missing-file."""

import pytest

from tasker import config, settings


@pytest.fixture
def _settings_in_tmp(tmp_path, monkeypatch):
    target = tmp_path / "settings.json"
    monkeypatch.setattr(config, "SETTINGS_PATH", target)
    return target


def test_load_settings_missing_file_returns_empty_dict(_settings_in_tmp):
    assert settings.load_settings() == {}


def test_save_and_load_roundtrip(_settings_in_tmp):
    settings.save_settings({"theme": "dark"})
    assert settings.load_settings() == {"theme": "dark"}


def test_load_settings_corrupt_json_returns_empty_dict(_settings_in_tmp):
    _settings_in_tmp.write_text("{not json", encoding="utf-8")
    assert settings.load_settings() == {}


def test_save_settings_overwrites(_settings_in_tmp):
    settings.save_settings({"theme": "dark"})
    settings.save_settings({"theme": "light"})
    assert settings.load_settings() == {"theme": "light"}
