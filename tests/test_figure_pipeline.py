import json

import pytest

from polynexus.core.figures.pipeline import FigurePipeline


def test_pipeline_commits_complete_run_and_active_pointer(
    ir_definition,
    tmp_path,
):
    result = FigurePipeline().run(
        output_root=tmp_path,
        run_id="run-1",
        technique="ir",
        definitions=(ir_definition,),
        profile_id="paper_complete",
    )

    assert result.run_id == "run-1"
    assert result.figures[0].status == "ready"
    run_root = tmp_path / "runs" / "run-1"
    document_path = run_root / result.figures[0].document
    assert document_path.is_file()
    assert all((run_root / path).is_file() for path in result.figures[0].assets.values())
    document = json.loads(document_path.read_text("utf-8"))
    assert document["export"]["profile"] == "paper_complete"
    assert document["export"]["published_revision"] == 1
    assert document["export"]["assets"] == result.figures[0].assets
    assert json.loads((tmp_path / "active_run.json").read_text("utf-8")) == {
        "run_id": "run-1"
    }


def test_pipeline_records_failed_definition_without_silent_omission(
    invalid_ir_definition,
    tmp_path,
):
    result = FigurePipeline().run(
        output_root=tmp_path,
        run_id="run-failed",
        technique="ir",
        definitions=(invalid_ir_definition,),
        profile_id="paper_complete",
    )

    assert len(result.figures) == 1
    assert result.figures[0].status == "generation_failed"
    assert result.figures[0].error
    assert result.figures[0].assets == {}


def test_pipeline_rejects_empty_or_already_committed_run_id(ir_definition, tmp_path):
    pipeline = FigurePipeline()

    with pytest.raises(ValueError, match="run ID"):
        pipeline.run(
            output_root=tmp_path,
            run_id="",
            technique="ir",
            definitions=(ir_definition,),
        )

    pipeline.run(
        output_root=tmp_path,
        run_id="run-1",
        technique="ir",
        definitions=(ir_definition,),
    )
    with pytest.raises(FileExistsError, match="already exists"):
        pipeline.run(
            output_root=tmp_path,
            run_id="run-1",
            technique="ir",
            definitions=(ir_definition,),
        )
