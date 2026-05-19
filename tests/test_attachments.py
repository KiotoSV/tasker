from pathlib import Path

from tasker.attachments import (
    _unique_attachment_path,
    attachments_dir,
    copy_attachment,
    list_attachments,
    parse_dnd_paths,
)


class TestAttachmentsDir:
    def test_derived_from_task_stem(self, tmp_path):
        task = tmp_path / "My Task.txt"
        assert attachments_dir(task) == tmp_path / "My Task"

    def test_works_for_nonexistent_task(self, tmp_path):
        # Function is pure path arithmetic — doesn't touch filesystem.
        assert attachments_dir(tmp_path / "ghost.txt") == tmp_path / "ghost"


class TestListAttachments:
    def test_empty_when_no_folder(self, tmp_path):
        task = tmp_path / "t.txt"
        task.write_text("", encoding="utf-8")
        assert list_attachments(task) == []

    def test_lists_files_only(self, tmp_path):
        task = tmp_path / "t.txt"
        task.write_text("", encoding="utf-8")
        folder = tmp_path / "t"
        folder.mkdir()
        (folder / "a.txt").write_text("", encoding="utf-8")
        (folder / "b.png").write_bytes(b"")
        (folder / "subdir").mkdir()
        items = list_attachments(task)
        names = [p.name for p in items]
        assert names == ["a.txt", "b.png"]

    def test_sorted_case_insensitive(self, tmp_path):
        task = tmp_path / "t.txt"
        task.write_text("", encoding="utf-8")
        folder = tmp_path / "t"
        folder.mkdir()
        for name in ["Banana", "apple", "Cherry"]:
            (folder / name).write_text("", encoding="utf-8")
        names = [p.name for p in list_attachments(task)]
        assert names == ["apple", "Banana", "Cherry"]


class TestUniqueAttachmentPath:
    def test_no_collision(self, tmp_path):
        assert _unique_attachment_path(tmp_path, "a.txt") == tmp_path / "a.txt"

    def test_with_collision_appends_number(self, tmp_path):
        (tmp_path / "a.txt").write_text("", encoding="utf-8")
        assert _unique_attachment_path(tmp_path, "a.txt") == tmp_path / "a (2).txt"

    def test_skips_multiple(self, tmp_path):
        (tmp_path / "a.txt").write_text("", encoding="utf-8")
        (tmp_path / "a (2).txt").write_text("", encoding="utf-8")
        assert _unique_attachment_path(tmp_path, "a.txt") == tmp_path / "a (3).txt"

    def test_preserves_extension(self, tmp_path):
        (tmp_path / "img.png").write_text("", encoding="utf-8")
        assert _unique_attachment_path(tmp_path, "img.png") == tmp_path / "img (2).png"

    def test_no_extension(self, tmp_path):
        (tmp_path / "README").write_text("", encoding="utf-8")
        assert _unique_attachment_path(tmp_path, "README") == tmp_path / "README (2)"


class TestCopyAttachment:
    def test_creates_folder_if_missing(self, tmp_path):
        task = tmp_path / "t.txt"
        task.write_text("", encoding="utf-8")
        source = tmp_path / "src.txt"
        source.write_text("hello", encoding="utf-8")
        dest = copy_attachment(task, source)
        assert dest == tmp_path / "t" / "src.txt"
        assert dest.read_text(encoding="utf-8") == "hello"

    def test_handles_collision(self, tmp_path):
        task = tmp_path / "t.txt"
        task.write_text("", encoding="utf-8")
        folder = tmp_path / "t"
        folder.mkdir()
        (folder / "src.txt").write_text("old", encoding="utf-8")
        source = tmp_path / "src.txt"
        source.write_text("new", encoding="utf-8")
        dest = copy_attachment(task, source)
        assert dest == folder / "src (2).txt"
        assert dest.read_text(encoding="utf-8") == "new"
        assert (folder / "src.txt").read_text(encoding="utf-8") == "old"


class TestParseDndPaths:
    def test_single_simple_path(self):
        assert parse_dnd_paths("C:/foo/bar.txt") == [Path("C:/foo/bar.txt")]

    def test_multiple_paths_space_separated(self):
        assert parse_dnd_paths("C:/a.txt C:/b.png") == [
            Path("C:/a.txt"), Path("C:/b.png"),
        ]

    def test_path_with_spaces_braced(self):
        assert parse_dnd_paths("{C:/My Docs/file.txt}") == [Path("C:/My Docs/file.txt")]

    def test_mixed(self):
        data = "{C:/My Docs/a.txt} C:/b.png {D:/Other Folder/c}"
        assert parse_dnd_paths(data) == [
            Path("C:/My Docs/a.txt"),
            Path("C:/b.png"),
            Path("D:/Other Folder/c"),
        ]

    def test_empty(self):
        assert parse_dnd_paths("") == []
