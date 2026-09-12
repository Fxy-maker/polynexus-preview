from __future__ import annotations

import pytest

from polynexus.core.ai_platform import (
    ProviderResultInput,
    UncertaintyComponent,
    UncertaintySummary,
    canonical_json_hash,
)
from polynexus.core.compute.models import ComputeResult


def test_uncertainty_summary_derives_rss_and_expanded_projection() -> None:
    repeatability = UncertaintyComponent.create(
        "repeatability", 0.6, unit="°C", value_kind="standard_deviation",
        method="three_replicates", input_metric_paths=("Tm_C",),
    )
    resolution = UncertaintyComponent.create(
        "resolution", 0.2, unit="°C", method="instrument_spec",
        input_metric_paths=("Tm_C",),
    )
    summary = UncertaintySummary.create(
        "Tm_C", unit="°C", components=(repeatability, resolution),
        coverage_factor=2.0, confidence_level=0.95,
    )

    assert summary.status == "available"
    assert summary.standard_uncertainty == pytest.approx((0.6**2 + 0.2**2) ** 0.5)
    assert summary.expanded_uncertainty == pytest.approx(2.0 * summary.standard_uncertainty)
    restored = UncertaintySummary.from_dict(summary.to_dict())
    assert restored == summary
    assert restored.summary_hash == canonical_json_hash(restored._identity_payload())


def test_unavailable_uncertainty_does_not_block_compute_result_and_enters_manifest() -> None:
    summary = UncertaintySummary.unavailable("Tm_C", "repeatability_missing", unit="°C")
    result = ComputeResult(metrics={"Tm_C": 168.4}, uncertainty={"Tm_C": summary})

    assert result.metrics["Tm_C"] == 168.4
    row = next(item for item in result.metric_manifest() if item["path"] == "Tm_C")
    assert row["status"] == "computed"
    assert row["uncertainty"]["status"] == "unavailable"
    assert row["uncertainty"]["reason_codes"] == ["repeatability_missing"]


def test_provider_result_input_serializes_the_same_uncertainty_dto() -> None:
    summary = UncertaintySummary.create(
        "peak", unit="cm-1",
        components=(UncertaintyComponent.create(
            "fit", 1.2, unit="cm-1", method="residual", input_metric_paths=("peak",)
        ),),
    )
    manifest = ({"path": "peak", "status": "computed", "value": 1630.0},)
    value = ProviderResultInput.create(
        source_artifact_id="artifact-1", technique="ir", metrics={"peak": 1630.0},
        metric_manifest=manifest, uncertainty={"peak": summary},
    )
    payload = value.to_dict()
    assert payload["uncertainty"]["peak"]["summary_hash"] == summary.summary_hash
    assert ProviderResultInput.from_dict(payload) == value


def test_unknown_uncertainty_models_fail_closed() -> None:
    with pytest.raises(ValueError, match="Unsupported uncertainty component kind"):
        UncertaintyComponent.from_dict(
            {"schema_version": "1", "kind": "bayesian_magic", "value": 1.0}
        )
    with pytest.raises(ValueError, match="schema version"):
        UncertaintySummary.from_dict(
            {"schema_version": "99", "metric_path": "x", "status": "unavailable", "reason_codes": ["missing"]}
        )
    with pytest.raises(ValueError, match="compatible unit"):
        UncertaintySummary.create(
            "x",
            components=(
                UncertaintyComponent.create("fit", 1.0, unit="nm"),
                UncertaintyComponent.create("resolution", 2.0, unit="cm"),
            ),
        )
