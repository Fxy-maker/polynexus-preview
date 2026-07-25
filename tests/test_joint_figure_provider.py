from __future__ import annotations

from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.joint.dataset import JointBatchRow, JointRunRecord
from polynexus.core.joint.coordinator import JointCoordinator
from polynexus.core.joint.figure_provider import build_joint_figure_definitions


def _rows() -> list[JointBatchRow]:
    return [
        JointBatchRow(
            sample_id="sample-a",
            sample_name="PA6-A",
            family="polyamide",
            batch_id="batch-a",
            batch_label="annealed",
            runs={
                "dsc": JointRunRecord("dsc-a", "dsc", results_summary={"Xc_pct": 42.0}),
                "waxs": JointRunRecord("waxs-a", "waxs", results_summary={"Xc_pct": 39.0, "D_Scherrer_nm": 7.0}),
                "saxs": JointRunRecord("saxs-a", "saxs", results_summary={"L_nm": 12.0, "lc_nm": 5.0}),
            },
        ),
        JointBatchRow(
            sample_id="sample-b",
            sample_name="PA6-B",
            family="polyamide",
            batch_id="batch-b",
            batch_label="quenched",
            runs={
                "dsc": JointRunRecord("dsc-b", "dsc", results_summary={"Xc_pct": 28.0}),
                "waxs": JointRunRecord("waxs-b", "waxs", results_summary={"Xc_pct": 26.0, "D_Scherrer_nm": 5.0}),
                "saxs": JointRunRecord("saxs-b", "saxs", results_summary={"L_nm": 10.0, "lc_nm": 3.0}),
            },
        ),
    ]


def test_joint_provider_emits_custom_manifest_definitions():
    definitions = build_joint_figure_definitions(_rows())

    assert tuple(item.figure_id for item in definitions) == (
        "joint.series.crystallinity",
        "joint.series.multiscale",
        "joint.series.coverage",
    )
    assert definitions[0].publication_role == "main"
    assert definitions[1].publication_role == "si"
    for definition in definitions:
        validate_figure_definition(definition)


def test_joint_provider_publishes_manifest_entries(tmp_path):
    definitions = build_joint_figure_definitions(_rows())
    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="joint-review",
        technique="joint",
        definitions=definitions,
    )

    assert [entry.figure_id for entry in manifest.figures] == [
        "joint.series.crystallinity",
        "joint.series.multiscale",
        "joint.series.coverage",
    ]
    assert all(entry.status == "ready" for entry in manifest.figures)


def test_joint_coordinator_exposes_manifest_publication_entrypoint(tmp_path):
    publication = JointCoordinator().publish_figure_definitions(
        tmp_path,
        _rows(),
        run_id="joint-coordinator-review",
    )

    assert publication.run_id == "joint-coordinator-review"
    assert set(publication.primary_assets) >= {
        "joint.series.crystallinity",
        "joint.series.multiscale",
    }


def test_joint_coordinator_attaches_manifest_context_to_hub_report(tmp_path):
    report = JointCoordinator().publish_hub_report(_rows(), tmp_path, run_id="joint-hub")

    publication = report["figure_publication"]
    assert publication["run_id"] == "joint-hub"
    assert publication["manifest"].endswith("runs\\joint-hub\\figure_manifest.json")
    assert "joint.series.crystallinity" in publication["figure_ids"]
