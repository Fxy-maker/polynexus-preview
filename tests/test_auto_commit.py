from pathlib import Path

import pytest

from scripts.auto_commit import normalize_requested_files


def test_normalize_requested_files_returns_unique_repository_relative_paths(tmp_path: Path):
    first = tmp_path / "one.txt"
    second = tmp_path / "nested" / "two.txt"
    second.parent.mkdir()
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")

    assert normalize_requested_files(tmp_path, ["one.txt", "nested/two.txt", "one.txt"]) == [
        "nested/two.txt",
        "one.txt",
    ]


def test_normalize_requested_files_rejects_paths_outside_repository(tmp_path: Path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    with pytest.raises(ValueError, match="outside repository"):
        normalize_requested_files(tmp_path, [str(outside)])
