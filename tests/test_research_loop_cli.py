from __future__ import annotations

import json
from pathlib import Path

from polynexus.cli.parser import build_parser
from polynexus.cli.run_research_loop_service import run_research_loop


def _output(capsys) -> dict:
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    return json.loads(lines[0])


def test_parser_exposes_research_loop_operations(tmp_path: Path) -> None:
    parser = build_parser()
    for operation in ("create", "inspect", "propose-mapping", "confirm-mapping", "resume", "recompute", "ars-completion", "complete-export"):
        args = parser.parse_args(["research-loop", operation, "--project-root", str(tmp_path)])
        assert args.cmd == "research-loop"
        assert args.operation == operation


def test_parser_accepts_export_paths_for_research_loop_completion(tmp_path: Path) -> None:
    args = build_parser().parse_args(
        [
            "research-loop",
            "complete-export",
            "--project-root",
            str(tmp_path),
            "--task-id",
            "task-1",
            "--export-paths",
            "manuscript.docx",
            "manuscript.pdf",
        ]
    )
    assert args.export_paths == ["manuscript.docx", "manuscript.pdf"]


def test_cli_creates_confirms_and_resumes_a_task(capsys, tmp_path: Path) -> None:
    task_args = build_parser().parse_args(
        [
            "research-loop",
            "create",
            "--project-root",
            str(tmp_path),
            "--project-id",
            "demo",
            "--question",
            "Compare crystallization",
            "--paths",
            "raw/sample.csv",
        ]
    )
    assert run_research_loop(task_args) == 0
    created = _output(capsys)["task"]

    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps({"raw/sample.csv": {"sample_id": "A"}}), encoding="utf-8")
    proposed_args = build_parser().parse_args(
        [
            "research-loop",
            "propose-mapping",
            "--project-root",
            str(tmp_path),
            "--task-id",
            created["task_id"],
            "--mapping",
            str(mapping),
        ]
    )
    assert run_research_loop(proposed_args) == 0
    assert _output(capsys)["task"]["status"] == "awaiting_mapping_confirmation"

    confirmed_args = build_parser().parse_args(
        [
            "research-loop",
            "confirm-mapping",
            "--project-root",
            str(tmp_path),
            "--task-id",
            created["task_id"],
            "--approve",
            "--approver",
            "user",
        ]
    )
    assert run_research_loop(confirmed_args) == 0
    assert _output(capsys)["task"]["status"] == "ready"

    resumed_args = build_parser().parse_args(
        [
            "research-loop",
            "resume",
            "--project-root",
            str(tmp_path),
            "--task-id",
            created["task_id"],
        ]
    )
    assert run_research_loop(resumed_args) == 0
    assert _output(capsys)["task"]["revision"] == 3


def test_cli_blocks_mapping_without_task_or_invalid_json(capsys, tmp_path: Path) -> None:
    args = build_parser().parse_args(
        ["research-loop", "propose-mapping", "--project-root", str(tmp_path)]
    )
    assert run_research_loop(args) == 2
    assert _output(capsys)["reason_codes"] == ["task_id_required"]


def test_cli_recompute_and_complete_export_route_through_service(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    class FakeTask:
        status = "checkpointed"

        def to_dict(self):
            return {"status": self.status}

    class FakeService:
        @classmethod
        def open(cls, root):
            return cls()

        def recompute(self, task_id, *, requested_outputs):
            assert task_id == "task-1"
            assert requested_outputs == ("figures", "tables")
            return FakeTask()

        def complete_export(self, task_id, *, export_paths):
            assert task_id == "task-1"
            assert export_paths == ("manuscript.docx", "manuscript.pdf")
            task = FakeTask()
            task.status = "completed"
            return task

    monkeypatch.setattr("polynexus.cli.run_research_loop_service.ResearchLoopService", FakeService)
    recompute_args = build_parser().parse_args(
        [
            "research-loop", "recompute", "--project-root", str(tmp_path),
            "--task-id", "task-1", "--requested-outputs", "figures", "tables",
        ]
    )
    assert run_research_loop(recompute_args) == 0
    assert _output(capsys)["status"] == "checkpointed"

    export_args = build_parser().parse_args(
        [
            "research-loop", "complete-export", "--project-root", str(tmp_path),
            "--task-id", "task-1", "--export-paths", "manuscript.docx", "manuscript.pdf",
        ]
    )
    assert run_research_loop(export_args) == 0
    assert _output(capsys)["status"] == "completed"


def test_cli_records_a_completed_ars_return_through_the_shared_service(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    completion_path = tmp_path / "completion.json"
    completion_path.write_text(
        json.dumps({"status": "completed", "integrity": "passed"}),
        encoding="utf-8",
    )

    class FakeTask:
        status = "ars_in_progress"

        def to_dict(self):
            return {"status": self.status}

    class FakeService:
        @classmethod
        def open(cls, root):
            return cls()

        def record_ars_completion(self, task_id, completion):
            assert task_id == "task-1"
            assert completion == {"status": "completed", "integrity": "passed"}
            return {"completion_id": "ars-completion-1", "ars_completion": completion}

        def resume(self, task_id):
            assert task_id == "task-1"
            return FakeTask()

    monkeypatch.setattr("polynexus.cli.run_research_loop_service.ResearchLoopService", FakeService)
    args = build_parser().parse_args(
        [
            "research-loop", "ars-completion", "--project-root", str(tmp_path),
            "--task-id", "task-1", "--ars-completion", str(completion_path),
        ]
    )

    assert run_research_loop(args) == 0
    payload = _output(capsys)
    assert payload["status"] == "ars_in_progress"
    assert payload["ars_completion"]["completion_id"] == "ars-completion-1"
