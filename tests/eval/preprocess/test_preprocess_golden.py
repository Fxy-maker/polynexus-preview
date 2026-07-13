from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from tests.eval.runner import run_preprocess_manifest


MANIFEST = Path(__file__).with_name("golden_manifest.json")


def test_preprocess_manifest_covers_two_cases_per_technique() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    counts = Counter(item["technique"] for item in payload["cases"])

    assert counts == {"DSC": 2, "IR": 2, "WAXS": 2, "SAXS": 2, "NMR": 2}
    assert any("boundary" in item["case_id"] for item in payload["cases"] if item["technique"] == "SAXS")
    assert {item["input_mode"] for item in payload["cases"] if item["technique"] == "NMR"} == {"processed", "fid"}


def test_golden_cases_use_real_preprocessing_and_preserve_weak_features() -> None:
    results = run_preprocess_manifest(MANIFEST)

    assert len(results) == 10
    for result in results:
        assert result["real_preprocess_function"]
        assert result["recovery_improvement"] > 0.0
        assert result["weak_peak_retention"] >= result["expected_min_weak_peak_retention"]
        assert result["decision"] in result["allowed_decisions"]
        assert result["candidate_ids"]


def test_golden_candidate_ids_and_decisions_are_reproducible() -> None:
    left = run_preprocess_manifest(MANIFEST)
    right = run_preprocess_manifest(MANIFEST)

    assert [item["candidate_ids"] for item in left] == [item["candidate_ids"] for item in right]
    assert [item["decision"] for item in left] == [item["decision"] for item in right]
