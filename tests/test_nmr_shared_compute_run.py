from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from polynexus.core.project_workflow import ProjectWorkflowService


@pytest.mark.parametrize(
    ("relative_source", "submodule"),
    (("测试数据/NMR/液体核磁/H谱/fid", "nmr.liquid_h"),),
)
def test_nmr_vendor_input_replays_through_project_compute_run_and_package(
    tmp_path: Path, relative_source: str, submodule: str
) -> None:
    source = Path(__file__).resolve().parents[1] / relative_source
    if not source.is_file():
        pytest.skip("vendor NMR fixture unavailable")
    target = tmp_path / "raw" / "NMR" / "fid"
    target.parent.mkdir(parents=True)
    shutil.copyfile(source, target)

    project_service = ProjectWorkflowService.open(tmp_path)
    summary = project_service.analyze_project(
        question="Replay vendor NMR evidence",
        data_scope=(target.relative_to(tmp_path).as_posix(),),
        nmr_submodule=submodule,
    )

    assert summary.computation == "passed"
    assert summary.package is not None
    assert len(summary.runs) == 1
    run = summary.runs[0]
    assert run.status == "review_required"
    assert run.analysis_run is not None
    assert run.analysis_run.steps[0].compute_run is not None
    assert run.analysis_run.steps[0].compute_run["canonical_template"]["template_id"] == "nmr.spectrum.v1"
    assert run.analysis_run.steps[0].result_summary["canonical_conversion"]["conversion_id"] == "raw-file-envelope.nmr.v1"

    export_dir = tmp_path / "nmr-export"
    exported = project_service.agent_service.export_run(run.analysis_run, export_dir)
    assert exported == export_dir.resolve()
    assert (export_dir / "evidence.json").is_file()
    assert not (export_dir / "raw").exists()
