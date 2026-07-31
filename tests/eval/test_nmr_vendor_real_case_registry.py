from __future__ import annotations

import json
from pathlib import Path
from dataclasses import replace

import pytest

from polynexus.core import get_engine
from tests.eval.runner import EvalRunner


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CASE_ROOT = PROJECT_ROOT / "tests" / "eval" / "cases" / "real"

EXPECTED_CASES = {
    "nmr_real_liquid_h_vendor": "nmr.liquid_h",
    "nmr_real_liquid_c_vendor": "nmr.liquid_c",
    "nmr_real_solid_h_vendor": "nmr.solid_h",
    "nmr_real_solid_c_vendor": "nmr.solid_c",
}


def test_vendor_registry_loads_all_four_nmr_partitions() -> None:
    runner = EvalRunner(project_root=PROJECT_ROOT)
    loaded = runner.load_all_cases(CASE_ROOT)

    cases = {case.case_id: case for case in loaded if case.technique == "nmr"}
    assert set(cases) == set(EXPECTED_CASES)
    assert runner.load_errors == []

    for case_id, submodule in EXPECTED_CASES.items():
        case = cases[case_id]
        assert case.submodule == submodule.removeprefix("nmr.")
        assert case.source == "vendor_unreviewed"
        assert case.ground_truth == case.ground_truth.__class__()
        assert runner._uses_real_engine(case) is True
        assert runner._real_engine_submodule_id(case) == submodule


@pytest.mark.parametrize("case_id", sorted(EXPECTED_CASES))
def test_vendor_case_runs_real_nmr_without_writing_source_tree(tmp_path: Path, case_id: str) -> None:
    runner = EvalRunner(project_root=PROJECT_ROOT)
    case_path = CASE_ROOT / f"{case_id}.json"
    case = runner.load_case(case_path)
    output_root = tmp_path / case_id
    engine = get_engine("nmr", submodule_id=case.submodule)

    assert engine is not None
    result = engine.run_pipeline(str(runner._resolve_real_engine_path(case)), str(output_root))

    assert result.technique == "nmr"
    assert result.metadata.get("figure_manifest")
    assert result.parameters
    parameter_block = next(iter(result.parameters.values()))
    assert parameter_block["nucleus"] in {"1H", "13C"}
    assert parameter_block["sample_state"] in {"liquid", "solid"}
    if case.submodule == "solid_c":
        assert parameter_block["Xc_assignment_status"] == "assignment_limited"
    assert output_root.exists()
    assert not any(path.is_relative_to(PROJECT_ROOT / "测试数据") for path in output_root.rglob("*"))


def test_vendor_case_descriptors_have_no_hidden_ground_truth() -> None:
    for case_id in EXPECTED_CASES:
        payload = json.loads((CASE_ROOT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["source"] == "vendor_unreviewed"
        assert payload["ground_truth"] == {}


def test_output_isolation_forwards_external_output_dir(monkeypatch, tmp_path: Path) -> None:
    runner = EvalRunner(project_root=PROJECT_ROOT)
    case = runner.load_case(CASE_ROOT / "nmr_real_solid_c_vendor.json")
    output_root = tmp_path / "external-eval-output"
    case = replace(
        case,
        config_overrides={**case.config_overrides, "eval_output_dir": str(output_root)},
    )

    class _FakeResult:
        technique = "nmr"
        metadata = {}
        parameters = {"solid_c": {"n_peaks": 1}}

    class _FakeEngine:
        active_submodule = "nmr.solid_c"
        _results = []

        def run_pipeline(self, filepath: str, output_dir: str = "") -> _FakeResult:
            calls.append((filepath, output_dir))
            return _FakeResult()

        def get_parameters(self) -> dict[str, object]:
            return {"n_peaks": 1}

    calls: list[tuple[str, str]] = []
    monkeypatch.setattr("polynexus.core.get_engine", lambda *args, **kwargs: _FakeEngine())

    runner._run_real_engine(case)

    assert calls == [(str(runner._resolve_real_engine_path(case)), str(output_root))]
