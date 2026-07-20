from __future__ import annotations

import pytest

from polynexus.core.figure_batch_edit_service import (
    apply_batch_edit_plan,
    build_batch_edit_plan,
)


def _template():
    return {"canvas": {"width_px": 900}, "style": {"xlabel": "q (nm^-1)"}, "objects": []}


def _entries():
    return [
        {
            "id": "figure-a",
            "document_path": "a.pnfig.json",
            "document": {"canvas": {"width_px": 800}, "style": {"xlabel": "q"}, "objects": []},
        },
        {
            "id": "figure-b",
            "document_path": "b.pnfig.json",
            "document": {"canvas": {"width_px": 800}, "style": {"xlabel": "q"}, "objects": []},
        },
    ]


def test_batch_plan_contains_preview_changes_for_each_selected_entry():
    plan = build_batch_edit_plan(_entries(), _template())

    assert plan.valid is True
    assert [target.target_id for target in plan.targets] == ["figure-a", "figure-b"]
    assert all("canvas" in target.changed_fields for target in plan.targets)
    assert all(target.error == "" for target in plan.targets)


def test_batch_apply_validates_every_target_before_writing():
    entries = _entries()
    entries[1]["document"] = None
    plan = build_batch_edit_plan(entries, _template())
    written = []

    with pytest.raises(ValueError, match="figure-b"):
        apply_batch_edit_plan(plan, lambda path, document: written.append((path, document)))

    assert written == []


def test_batch_apply_rolls_back_already_written_targets_on_failure():
    plan = build_batch_edit_plan(_entries(), _template())
    documents = {"a.pnfig.json": _entries()[0]["document"], "b.pnfig.json": _entries()[1]["document"]}
    calls = []

    def save(path, document):
        calls.append((path, document))
        if path == "b.pnfig.json" and document["canvas"]["width_px"] == 900:
            raise OSError("disk full")
        documents[path] = document

    with pytest.raises(OSError, match="disk full"):
        apply_batch_edit_plan(plan, save)

    assert documents["a.pnfig.json"]["canvas"]["width_px"] == 800
    assert calls[-1][0] == "a.pnfig.json"
