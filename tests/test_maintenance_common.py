from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.maintenance_common import relative_posix, split_display_items


def test_split_display_items_caps_items_and_reports_remaining():
    displayed, remaining = split_display_items(["a", "b", "c"], max_items=2)

    assert displayed == ["a", "b"]
    assert remaining == 1


def test_split_display_items_returns_all_when_requested():
    displayed, remaining = split_display_items(["a", "b", "c"], max_items=1, list_all=True)

    assert displayed == ["a", "b", "c"]
    assert remaining == 0


def test_relative_posix_returns_relative_path_when_under_root(tmp_path):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = root / "nested" / "artifact.txt"

        assert relative_posix(path, root) == "nested/artifact.txt"


def test_relative_posix_falls_back_to_absolute_path_for_external_paths(tmp_path):
    external = Path("C:/other/artifact.txt")

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        assert relative_posix(external, root) == external.as_posix()
