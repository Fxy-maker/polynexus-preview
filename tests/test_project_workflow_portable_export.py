from __future__ import annotations

from pathlib import Path

from polynexus.core.project_workflow.adapters import SingleInputTechniqueAdapter, TechniqueSeriesAdapter


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


def test_series_adapter_binds_each_explicit_portable_export_after_path_sorting(tmp_path: Path) -> None:
    raw_paths_by_name = {}
    portable_exports = []
    for name in ("sample-a", "sample-b"):
        raw = tmp_path / f"{name}.ngb-ds1"
        raw.write_bytes(name.encode("utf-8"))
        exported = tmp_path / f"{name}.csv"
        exported.write_text(
            "Temperature (C),Mass (%)\n25,100\n100,98\n",
            encoding="utf-8",
        )
        raw_paths_by_name[name] = raw
        portable_exports.append({
            "raw_source": str(raw),
            "export_path": str(exported),
            "exporter": "Proteus portable CSV",
        })

    proposal = TechniqueSeriesAdapter().propose_recipe({
        "workflow_id": TechniqueSeriesAdapter.workflow_id,
        "technique": "tga",
        "paths": [str(raw_paths_by_name["sample-b"]), str(raw_paths_by_name["sample-a"])],
        "portable_exports": list(reversed(portable_exports)),
    })

    assert proposal.status == "review_required"
    assert proposal.recipe is not None
    assert TechniqueSeriesAdapter.is_valid_recipe(proposal.recipe)
    assert [
        step.parameters["portable_export"]["export_path"]
        for step in proposal.recipe.steps
    ] == [item["export_path"] for item in portable_exports]


def test_series_adapter_rejects_unbound_or_reused_portable_exports(tmp_path: Path) -> None:
    raw_a = tmp_path / "sample-a.ngb-ds1"
    raw_b = tmp_path / "sample-b.ngb-ds1"
    raw_a.write_bytes(b"opaque-a")
    raw_b.write_bytes(b"opaque-b")
    exported = tmp_path / "sample.csv"
    exported.write_text("Temperature (C),Mass (%)\n25,100\n100,98\n", encoding="utf-8")
    base_manifest = {
        "workflow_id": TechniqueSeriesAdapter.workflow_id,
        "technique": "tga",
        "paths": [str(raw_a), str(raw_b)],
    }

    missing_source = TechniqueSeriesAdapter().propose_recipe({
        **base_manifest,
        "portable_exports": [
            {"export_path": str(exported), "exporter": "Proteus portable CSV"},
            {"export_path": str(exported), "exporter": "Proteus portable CSV"},
        ],
    })
    assert missing_source.reason_codes == ("portable_export_invalid",)

    reused_export = TechniqueSeriesAdapter().propose_recipe({
        **base_manifest,
        "portable_exports": [
            {
                "raw_source": str(raw_a),
                "export_path": str(exported),
                "exporter": "Proteus portable CSV",
            },
            {
                "raw_source": str(raw_b),
                "export_path": str(exported),
                "exporter": "Proteus portable CSV",
            },
        ],
    })
    assert reused_export.reason_codes == ("portable_export_invalid",)
