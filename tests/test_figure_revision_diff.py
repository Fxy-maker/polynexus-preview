from __future__ import annotations

from polynexus.core.figure_revision_diff import build_revision_diff


def test_revision_diff_ignores_volatile_timestamps_and_reports_fields():
    left = {"updated_at": "old", "style": {"xlabel": "q"}, "objects": [{"id": "a", "visible": True}]}
    right = {"updated_at": "new", "style": {"xlabel": "r"}, "objects": [{"id": "a", "visible": False}]}

    diff = build_revision_diff(left, right)

    assert "updated_at" not in {change.path for change in diff.document_changes}
    assert {change.path for change in diff.document_changes} == {"style.xlabel", "objects[0].visible"}


def test_revision_diff_reports_asset_add_remove_and_change():
    diff = build_revision_diff(
        {},
        {},
        left_assets={"figure.png": "sha-old", "old.csv": "sha-old-csv"},
        right_assets={"figure.png": "sha-new", "new.csv": "sha-new-csv"},
    )

    changes = {(item.path, item.status) for item in diff.asset_changes}
    assert changes == {
        ("figure.png", "changed"),
        ("old.csv", "removed"),
        ("new.csv", "added"),
    }
