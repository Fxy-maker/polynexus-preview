from __future__ import annotations

from pathlib import Path

from polynexus.core.project_workflow.adapters import SingleInputTechniqueAdapter


def _portable_manifest(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    raw = tmp_path / "sample.ngb-ds1"
    raw.write_bytes(b"Netzsch TA file\x00_db_format_1\x00opaque")
    exported = tmp_path / "sample.csv"
    exported.write_text("Temperature (C),Mass (%)\n25,100\n100,98\n", encoding="utf-8")
    return raw, exported, {
        "workflow_id": "project.technique.single.v1",
        "technique": "tga",
        "path": str(raw),
        "portable_export": {
            "export_path": str(exported),
            "exporter": "Proteus portable CSV",
        },
    }


def test_project_adapter_accepts_opaque_raw_with_bound_portable_export(tmp_path: Path) -> None:
    raw, exported, manifest = _portable_manifest(tmp_path)
    proposal = SingleInputTechniqueAdapter().propose_recipe(manifest)

    assert proposal.status == "review_required"
    assert proposal.recipe is not None
    step = proposal.recipe.steps[0]
    assert step.parameters["portable_export"]["export_path"] == str(exported)
    binding = step.parameters["canonical_template"]["payload"]["portable_export_binding"]
    assert binding["raw_source_sha256"] == proposal.recipe.artifacts[0].sha256
    assert binding["raw_source_path"] == str(raw.resolve())
