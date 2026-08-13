from __future__ import annotations

import argparse
import json
from pathlib import Path

from polynexus.cli.parser import build_parser
from polynexus.cli.run_project_workflow_service import run_project_workflow
from polynexus.core.project_workflow.models import AnalysisRequest


def _write_mettler_fixture(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = ["Sample Weight: 5.95 mg"]
    index = 0
    for setpoint, duration in ((255.0, 70), (180.0, 80), (255.0, 70), (181.0, 85)):
        for second in range(duration + 1):
            temperature = setpoint + (0.05 if setpoint < 200 else 0.02)
            heat_flow = 1.0 + (20.0 / (second + 5) if setpoint < 200 else 0.0)
            rows.append(f"{index} {index} {temperature:.3f} {setpoint:.3f} {heat_flow:.6f}")
            index += 1
    path.write_text("\n".join(rows), encoding="utf-8")
    return path


def _args(operation: str, project_root: Path, **values: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "operation": operation,
        "project_root": str(project_root),
        "request": None,
        "paths": (),
        "plan": None,
        "runs": (),
        "package_id": "pa6-crystallization",
        "relations": None,
        "quick_run_id": None,
        "technique": None,
        "source_file": None,
        "output_dir": None,
    }
    defaults.update(values)
    return argparse.Namespace(**defaults)


def _one_envelope(capsys) -> dict:
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    return json.loads(lines[0])


def test_project_workflow_parser_accepts_all_operations(tmp_path: Path) -> None:
    parser = build_parser()
    for operation in ("inspect", "plan", "run", "package", "attach-quick-run"):
        args = parser.parse_args(["project-workflow", operation, "--project-root", str(tmp_path)])
        assert args.cmd == "project-workflow"
        assert args.operation == operation


def test_project_workflow_cli_inspect_emits_one_json_envelope(capsys, tmp_path: Path) -> None:
    source = _write_mettler_fixture(tmp_path / "raw" / "PA6-DWJJ.txt")

    code = run_project_workflow(
        _args("inspect", tmp_path, paths=(str(source.relative_to(tmp_path)),))
    )

    payload = _one_envelope(capsys)
    assert code == 0
    assert payload["operation"] == "inspect"
    assert payload["status"] == "completed"
    assert payload["graph"]["artifacts"][0]["relative_path"] == "raw/PA6-DWJJ.txt"


def test_project_workflow_cli_plan_run_and_package(capsys, tmp_path: Path) -> None:
    source = _write_mettler_fixture(tmp_path / "raw" / "PA6-DWJJ.txt")
    request = AnalysisRequest.create(
        question="Compare PA6 crystallization kinetics",
        requested_outputs=("avrami_parameter_table",),
        data_scope=(str(source.relative_to(tmp_path)),),
    )
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request.to_dict()), encoding="utf-8")

    assert run_project_workflow(_args("plan", tmp_path, request=str(request_path))) == 0
    planned = _one_envelope(capsys)
    assert planned["plan"]["status"] in {"ready", "review_required"}

    assert run_project_workflow(_args("run", tmp_path, request=str(request_path))) == 0
    executed = _one_envelope(capsys)
    assert executed["run"]["status"] == "review_required"
    run_path = Path(executed["run"]["manifest_path"])
    assert run_path.is_file()

    assert run_project_workflow(_args("package", tmp_path, runs=(str(run_path),))) == 0
    packaged = _one_envelope(capsys)
    assert packaged["package"]["status"] == "review_required"
    assert Path(packaged["package"]["path"]).is_relative_to(tmp_path / ".polynexus")


def test_project_workflow_cli_blocks_invalid_root_and_missing_request(capsys, tmp_path: Path) -> None:
    code = run_project_workflow(_args("inspect", tmp_path / "missing"))

    payload = _one_envelope(capsys)
    assert code == 2
    assert payload["reason_codes"] == ["project_root_invalid"]

    code = run_project_workflow(_args("plan", tmp_path))

    payload = _one_envelope(capsys)
    assert code == 2
    assert payload["reason_codes"] == ["request_invalid"]


def test_project_workflow_cli_attaches_existing_quick_run_by_reference(capsys, tmp_path: Path) -> None:
    source = tmp_path / "sample.csv"
    source.write_text("q,I\n0.1,1\n", encoding="utf-8")

    assert run_project_workflow(
        _args(
            "attach-quick-run",
            tmp_path,
            quick_run_id="quick-42",
            technique="saxs",
            source_file=str(source),
        )
    ) == 0

    payload = _one_envelope(capsys)
    assert payload["attachment"]["quick_run_id"] == "quick-42"
    assert payload["attachment"]["attachment_kind"] == "reference_only"
