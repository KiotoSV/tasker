import re
import time
from datetime import datetime

import pytest

from tasker.config import DATE_FMT
from tasker.tasks import (
    TaskRepository,
    now_str,
    parse_task,
    sanitize_filename,
    write_task,
)


class TestNowStr:
    def test_matches_format(self):
        s = now_str()
        # Should parse back via the canonical format.
        datetime.strptime(s, DATE_FMT)


class TestSanitizeFilename:
    @pytest.mark.parametrize("raw,expected", [
        ("hello", "hello"),
        ("  with spaces  ", "with spaces"),
        ("trailing dots...", "trailing dots"),
        ("a/b\\c:d*e?f", "a_b_c_d_e_f"),
        ('quote"and<>pipes|', "quote_and__pipes_"),
    ])
    def test_replaces_forbidden(self, raw, expected):
        assert sanitize_filename(raw) == expected

    def test_empty_becomes_fallback(self):
        assert sanitize_filename("") == "Без названия"
        assert sanitize_filename("   ") == "Без названия"
        assert sanitize_filename("...") == "Без названия"

    def test_control_chars_stripped(self):
        # \x00-\x1f are forbidden.
        assert "\x00" not in sanitize_filename("a\x00b")
        assert "\x1f" not in sanitize_filename("a\x1fb")


class TestParseTask:
    def test_minimal_pending(self, tmp_path):
        p = tmp_path / "t.txt"
        p.write_text(
            "status: pending\n"
            "created: 2026-05-19 10:00\n"
            "completed:\n"
            "\n"
            "Тело",
            encoding="utf-8",
        )
        meta = parse_task(p)
        assert meta["status"] == "pending"
        assert meta["projects"] == []
        assert meta["created"] == "2026-05-19 10:00"
        assert meta["completed"] == ""
        assert meta["body"] == "Тело"

    def test_done_with_multiple_projects(self, tmp_path):
        p = tmp_path / "t.txt"
        p.write_text(
            "status: done\n"
            "project: C:/dev/a\n"
            "project: C:/dev/b\n"
            "created: 2026-05-19 10:00\n"
            "completed: 2026-05-19 12:00\n"
            "\n"
            "line1\nline2",
            encoding="utf-8",
        )
        meta = parse_task(p)
        assert meta["status"] == "done"
        assert meta["projects"] == ["C:/dev/a", "C:/dev/b"]
        assert meta["completed"] == "2026-05-19 12:00"
        assert meta["body"] == "line1\nline2"

    def test_duplicate_projects_dedup(self, tmp_path):
        p = tmp_path / "t.txt"
        p.write_text(
            "status: pending\n"
            "project: x\n"
            "project: x\n"
            "project: y\n"
            "created: 2026-05-19 10:00\n"
            "completed:\n"
            "\n"
            "",
            encoding="utf-8",
        )
        assert parse_task(p)["projects"] == ["x", "y"]

    def test_empty_project_skipped(self, tmp_path):
        p = tmp_path / "t.txt"
        p.write_text(
            "status: pending\n"
            "project:\n"
            "project: real\n"
            "created: 2026-05-19 10:00\n"
            "completed:\n"
            "\n",
            encoding="utf-8",
        )
        assert parse_task(p)["projects"] == ["real"]

    def test_invalid_status_falls_back_to_pending(self, tmp_path):
        p = tmp_path / "t.txt"
        p.write_text(
            "status: garbage\n"
            "created: 2026-05-19 10:00\n"
            "completed:\n"
            "\n",
            encoding="utf-8",
        )
        assert parse_task(p)["status"] == "pending"

    def test_missing_file_returns_defaults(self, tmp_path):
        meta = parse_task(tmp_path / "missing.txt")
        assert meta["status"] == "pending"
        assert meta["projects"] == []
        assert meta["body"] == ""
        # created defaults to current time — just ensure it parses.
        datetime.strptime(meta["created"], DATE_FMT)


class TestWriteTask:
    def test_roundtrip(self, tmp_path):
        p = tmp_path / "t.txt"
        write_task(
            p,
            status="done",
            projects=["A", "B"],
            created="2026-05-19 09:00",
            completed="2026-05-19 11:00",
            body="hello\nworld",
        )
        text = p.read_text(encoding="utf-8")
        assert "status: done\n" in text
        assert "project: A\n" in text
        assert "project: B\n" in text
        assert "created: 2026-05-19 09:00\n" in text
        assert "completed: 2026-05-19 11:00\n" in text
        # Body separated by blank line.
        assert text.endswith("\nhello\nworld")

        meta = parse_task(p)
        assert meta == {
            "status": "done",
            "projects": ["A", "B"],
            "created": "2026-05-19 09:00",
            "completed": "2026-05-19 11:00",
            "body": "hello\nworld",
        }

    def test_no_projects_block(self, tmp_path):
        p = tmp_path / "t.txt"
        write_task(p, "pending", [], "2026-05-19 09:00", "", "")
        text = p.read_text(encoding="utf-8")
        assert "project:" not in text


class TestTaskRepository:
    def test_unique_path_no_collision(self, tmp_path):
        repo = TaskRepository(tmp_path)
        assert repo.unique_path("foo") == tmp_path / "foo.txt"

    def test_unique_path_with_collision(self, tmp_path):
        (tmp_path / "foo.txt").write_text("", encoding="utf-8")
        repo = TaskRepository(tmp_path)
        assert repo.unique_path("foo") == tmp_path / "foo (2).txt"

    def test_unique_path_skips_multiple(self, tmp_path):
        (tmp_path / "foo.txt").write_text("", encoding="utf-8")
        (tmp_path / "foo (2).txt").write_text("", encoding="utf-8")
        repo = TaskRepository(tmp_path)
        assert repo.unique_path("foo") == tmp_path / "foo (3).txt"

    def test_unique_path_exclude_returns_same(self, tmp_path):
        existing = tmp_path / "foo.txt"
        existing.write_text("", encoding="utf-8")
        repo = TaskRepository(tmp_path)
        # Renaming to its own name should be a no-op.
        assert repo.unique_path("foo", exclude=existing) == existing

    def test_list_tasks_empty(self, tmp_path):
        repo = TaskRepository(tmp_path)
        assert repo.list_tasks() == []

    def test_list_tasks_returns_metadata(self, tmp_path):
        p = tmp_path / "alpha.txt"
        write_task(p, "pending", ["proj"], "2026-05-19 09:00", "", "body")
        items = TaskRepository(tmp_path).list_tasks()
        assert len(items) == 1
        item = items[0]
        assert item["title"] == "alpha"
        assert item["path"] == p
        assert item["projects"] == ["proj"]

    def test_list_tasks_sorted_desc_by_created_then_title(self, tmp_path):
        write_task(tmp_path / "a.txt", "pending", [], "2026-05-19 09:00", "", "")
        write_task(tmp_path / "b.txt", "pending", [], "2026-05-19 10:00", "", "")
        write_task(tmp_path / "c.txt", "pending", [], "2026-05-19 09:00", "", "")
        titles = [t["title"] for t in TaskRepository(tmp_path).list_tasks()]
        # Newest created first; same created → title desc.
        assert titles == ["b", "c", "a"]

    def test_cache_avoids_reparse_when_mtime_unchanged(self, tmp_path, monkeypatch):
        p = tmp_path / "t.txt"
        write_task(p, "pending", [], "2026-05-19 09:00", "", "body1")
        repo = TaskRepository(tmp_path)
        repo.list_tasks()  # populates cache
        # Replace parse_task with a sentinel that should not be called again.
        called = []
        import tasker.tasks as tasks_module
        original = tasks_module.parse_task
        monkeypatch.setattr(tasks_module, "parse_task", lambda path: called.append(path) or original(path))
        repo.list_tasks()
        assert called == []  # cached

    def test_cache_invalidated_on_mtime_change(self, tmp_path):
        p = tmp_path / "t.txt"
        write_task(p, "pending", [], "2026-05-19 09:00", "", "body1")
        repo = TaskRepository(tmp_path)
        first = repo.list_tasks()[0]
        assert first["body"] == "body1"

        # Bump mtime by writing again with a different body.
        time.sleep(0.02)
        write_task(p, "pending", [], "2026-05-19 09:00", "", "body2")
        # Force mtime to differ even on coarse filesystems.
        import os
        st = p.stat()
        os.utime(p, (st.st_atime, st.st_mtime + 1))

        second = repo.list_tasks()[0]
        assert second["body"] == "body2"

    def test_cache_drops_deleted_paths(self, tmp_path):
        p = tmp_path / "t.txt"
        write_task(p, "pending", [], "2026-05-19 09:00", "", "")
        repo = TaskRepository(tmp_path)
        repo.list_tasks()
        assert p in repo._cache
        p.unlink()
        repo.list_tasks()
        assert p not in repo._cache


class TestForbiddenCharsRegex:
    def test_pattern_covers_windows_reserved(self):
        from tasker.config import FORBIDDEN_CHARS
        for ch in '<>:"/\\|?*':
            assert FORBIDDEN_CHARS.search(ch), f"missing: {ch!r}"
        assert isinstance(FORBIDDEN_CHARS, re.Pattern)
