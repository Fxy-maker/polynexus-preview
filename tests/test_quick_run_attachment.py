from pathlib import Path

from polynexus.core.project_workflow.quick_run_attachment import attach_quick_run
from polynexus.core.project_workflow.service import ProjectWorkflowService
from polynexus.core.project_workflow.workspace import ProjectWorkspace


def test_quick_run_attachment_records_a_reference_without_copying_source_or_output(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    source = tmp_path / "standalone" / "sample.csv"
    source.parent.mkdir()
    source.write_text("q,I\n0.1,1\n", encoding="utf-8")
    output = tmp_path / "standalone" / "output"
    output.mkdir()

    attachment = attach_quick_run(
        ProjectWorkspace.open(project_root),
        quick_run_id="run-42",
        technique="saxs",
        source_file=source,
        output_dir=output,
    )

    assert attachment.quick_run_id == "run-42"
    assert attachment.source_file == str(source.resolve())
    assert attachment.output_dir == str(output.resolve())
    assert attachment.manifest_path.exists()
    assert not (project_root / "raw").exists()
    assert list(project_root.rglob("sample.csv")) == []


def test_attaching_the_same_quick_run_is_idempotent_and_conflicting_reference_is_rejected(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    source = tmp_path / "sample.csv"
    source.write_text("q,I\n0.1,1\n", encoding="utf-8")
    workspace = ProjectWorkspace.open(project_root)

    first = attach_quick_run(workspace, quick_run_id="run-42", technique="saxs", source_file=source)
    assert attach_quick_run(workspace, quick_run_id="run-42", technique="saxs", source_file=source) == first

    source.write_text("q,I\n0.1,2\n", encoding="utf-8")
    try:
        attach_quick_run(workspace, quick_run_id="run-42", technique="saxs", source_file=source)
    except ValueError as exc:
        assert "conflicts" in str(exc)
    else:
        raise AssertionError("attachment must not overwrite prior provenance")


def test_project_service_exposes_the_same_quick_run_attachment(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    source = tmp_path / "sample.csv"
    source.write_text("q,I\n0.1,1\n", encoding="utf-8")

    attachment = ProjectWorkflowService.open(project_root).attach_quick_run(
        quick_run_id="run-42", technique="saxs", source_file=source
    )

    assert attachment.quick_run_id == "run-42"
