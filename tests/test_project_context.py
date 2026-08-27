from __future__ import annotations

import json
from pathlib import Path

import pytest

from polynexus.core.project_context import ProjectContext


def test_missing_context_is_empty_and_hashable(tmp_path: Path) -> None:
    context = ProjectContext.load(tmp_path)

    assert context.snapshot == {}
    assert context.sha256
    assert context.source == "absent"


def test_valid_context_preserves_explicit_dsc_reference(tmp_path: Path) -> None:
    context_dir = tmp_path / ".polynexus"
    context_dir.mkdir()
    (context_dir / "project-context.json").write_text(
        json.dumps(
            {
                "schema": "project-context.v1",
                "material": {"name": "PA6"},
                "techniques": {
                    "dsc": {
                        "reference_enthalpy_Jg": 230.0,
                        "reference_enthalpy_source": "literature:example",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    context = ProjectContext.load(tmp_path)

    assert context.snapshot["material"]["name"] == "PA6"
    assert context.dsc_reference_enthalpy == 230.0
    assert context.dsc_reference_source == "literature:example"
    assert context.source.endswith("project-context.json")


@pytest.mark.parametrize(
    "payload",
    (
        {"schema": "project-context.v0"},
        {"schema": "project-context.v1", "techniques": {"dsc": {"reference_enthalpy_Jg": 0}}},
        {"schema": "project-context.v1", "techniques": {"dsc": {"reference_enthalpy_Jg": "230"}}},
    ),
)
def test_invalid_context_fails_closed(tmp_path: Path, payload: dict[str, object]) -> None:
    path = tmp_path / "context.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="project_context_invalid"):
        ProjectContext.load(path)
