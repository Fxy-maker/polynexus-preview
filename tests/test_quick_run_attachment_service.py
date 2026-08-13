from pathlib import Path

from polynexus.gui.quick_run_attachment_service import attach_current_run_to_project
from polynexus.gui.workspace_context import WorkspaceContext, WorkspaceResultStatus


def test_attach_current_run_uses_the_workspace_run_as_a_reference_only(tmp_path: Path):
    source = tmp_path / "standalone" / "sample.csv"
    source.parent.mkdir()
    source.write_text("q,I\n0.1,1\n", encoding="utf-8")
    output = tmp_path / "standalone" / "output"
    output.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    context = WorkspaceContext(
        technique="saxs",
        source_path=str(source),
        output_dir=str(output),
        run_id="quick-42",
        result_status=WorkspaceResultStatus.COMPLETE,
    )

    attachment = attach_current_run_to_project(context, project)

    assert attachment.quick_run_id == "quick-42"
    assert attachment.manifest_path.exists()
    assert not (project / "raw").exists()
    assert list(project.rglob("sample.csv")) == []


def test_attach_current_run_rejects_noncompleted_or_incomplete_workspace_context(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()

    for context in (
        WorkspaceContext.empty(),
        WorkspaceContext(technique="saxs", source_path="sample.csv", run_id="run-1"),
    ):
        try:
            attach_current_run_to_project(context, project)
        except ValueError as exc:
            assert "completed run" in str(exc)
        else:
            raise AssertionError("incomplete context must not attach a run")
