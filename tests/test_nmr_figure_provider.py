import json

import numpy as np
import pytest

from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.figures.v2_capabilities import build_v2_definition_artifact
from polynexus.core.nmr import NMREngine
from polynexus.core.nmr_engine.core import NMRResult
from polynexus.core.nmr_engine.figure_provider import build_nmr_figure_definitions


@pytest.fixture
def nmr_results():
    ppm = np.array([180.0, 140.0, 100.0, 60.0, 20.0])
    return (
        NMRResult(
            label="nmr-a",
            nucleus="13C",
            ppm=ppm,
            intensity=np.array([0.1, 0.4, 0.25, 0.6, 0.15]),
            intensity_fit=np.array([0.11, 0.38, 0.26, 0.57, 0.16]),
            peaks=[
                {
                    "ppm": 60.0,
                    "height": 0.6,
                    "prominence": 0.5,
                    "assignment": "crystalline C",
                }
            ],
            matches=[
                {"exp_ppm": 60.0, "calc_ppm": 62.0},
                {"exp_ppm": 140.0, "calc_ppm": 138.0},
            ],
            region_integrals={"aliphatic": 63.0, "aromatic": 37.0},
            Xc_pct=41.0,
        ),
        NMRResult(
            label="nmr-b",
            nucleus="13C",
            ppm=ppm,
            intensity=np.array([0.08, 0.3, 0.2, 0.5, 0.12]),
            Xc_pct=33.0,
        ),
    )


def test_nmr_provider_emits_complete_semantic_figures(nmr_results):
    definitions = build_nmr_figure_definitions(nmr_results)

    assert [item.figure_id for item in definitions] == [
        "nmr.frame.spectrum.001",
        "nmr.frame.deconvolution.001",
        "nmr.frame.comparison.001",
        "nmr.frame.region-integrals.001",
        "nmr.frame.spectrum.002",
        "nmr.series.crystallinity",
    ]
    assert definitions[0].layout.panels[0].x_axis.reversed is True
    assert definitions[1].layout.panels[0].x_axis.reversed is True
    assert definitions[2].objects[0]["chart_kind"] == "scatter"
    assert definitions[3].objects[0]["chart_kind"] == "bar"
    assert definitions[-1].objects[0]["chart_kind"] == "bar"

    for definition in definitions:
        validate_figure_definition(definition)
        assert definition.recipe["v2_adapter"] == "nmr"
        assert build_v2_definition_artifact(definition).capability["v2_runtime"] == "ready"


def test_nmr_engine_exposes_complete_definitions(nmr_results):
    engine = NMREngine()
    engine._results = list(nmr_results)

    definitions = engine.build_figure_definitions()

    assert {item.figure_id for item in definitions} >= {
        "nmr.frame.spectrum.001",
        "nmr.series.crystallinity",
    }


def test_nmr_peak_labels_preserve_assignments_and_cycle_through_lanes(nmr_results):
    nmr_results[0].peaks = [
        {
            "ppm": 180.0 - index * 10.0,
            "height": 0.8 - index * 0.01,
            "prominence": 7 - index,
            "assignment": f"long-assignment-name-{index}",
        }
        for index in range(7)
    ]

    definition = build_nmr_figure_definitions(nmr_results)[0]
    labels = [
        item
        for item in definition.objects
        if item["type"] == "text" and item.get("coordinate_space") == "xdata_yaxes"
    ]
    assignment_rows = [
        item
        for item in definition.objects
        if item["type"] == "text" and item.get("coordinate_space") == "axes"
    ]

    assert [item["text"] for item in labels] == [
        f"{180.0 - index * 10.0:.1f}"
        for index in range(7)
    ]
    assert [item["text"] for item in assignment_rows] == [
        f"{180.0 - index * 10.0:.1f} — long-assignment-name-{index}"
        for index in range(7)
    ]
    assert [item["x"] for item in assignment_rows] == pytest.approx([1.02] * 7)
    assert [item["y"] for item in assignment_rows] == pytest.approx(
        [0.98 - index * 0.055 for index in range(7)]
    )
    assert [item["y"] for item in labels] == pytest.approx(
        [0.96, 0.84, 0.72, 0.60, 0.48, 0.96, 0.84]
    )
    assert definition.layout.width_in == pytest.approx(9.5)


def _solid_c_review(source_id: str = "solid-c.json") -> dict:
    return {
        "record_id": "review-nmr-solid-c-1",
        "scope": "nmr.solid_c",
        "reviewer": "reviewer-a",
        "reviewed_at": "2026-07-29T00:00:00Z",
        "policy_version": "nmr-solid-c-v1",
        "source_refs": [source_id],
        "decisions": {
            "assignment_source": "explicit reviewed peak assignments",
            "ambiguity_label_policy": "retain ambiguity labels",
            "xc_promotion_conditions": "supported phase pair and confidence",
        },
        "status": "accepted",
        "conditions": [],
    }


def _solid_c_result(review: dict | None = None, source_id: str = "solid-c.json") -> NMRResult:
    metadata = {"source_id": source_id}
    if review is not None:
        metadata["scientific_review"] = review
    return NMRResult(
        label="solid-c",
        nucleus="13C",
        sample_state="solid",
        metadata=metadata,
        ppm=np.array([180.0, 100.0, 20.0]),
        intensity=np.array([0.1, 0.5, 0.15]),
        intensity_fit=np.array([0.11, 0.48, 0.16]),
        matches=[{"exp_ppm": 100.0, "calc_ppm": 101.0}],
        region_integrals={"aliphatic_C": 100.0},
        Xc_pct=41.0,
    )


def test_solid_c_without_review_is_diagnostic_only():
    definitions = build_nmr_figure_definitions((_solid_c_result(),))

    assert definitions
    assert all(item.publication_role == "diagnostic" for item in definitions)
    assert definitions[0].recipe["scientific_review"]["reason"] == "review_missing"


def test_solid_c_accepted_matching_review_promotes_only_primary_spectrum():
    result = _solid_c_result(_solid_c_review())

    definitions = build_nmr_figure_definitions((result,))
    by_id = {item.figure_id: item for item in definitions}

    assert by_id["nmr.frame.spectrum.001"].publication_role == "main"
    assert by_id["nmr.frame.deconvolution.001"].publication_role == "diagnostic"
    assert by_id["nmr.frame.comparison.001"].publication_role == "si"
    assert by_id["nmr.frame.region-integrals.001"].publication_role == "si"
    assert by_id["nmr.series.crystallinity"].publication_role == "si"
    assert by_id["nmr.frame.spectrum.001"].recipe["scientific_review"]["allowed"] is True


def test_solid_c_source_mismatch_is_fail_closed_and_json_safe():
    result = _solid_c_result(_solid_c_review(source_id="other.json"))
    definition = build_nmr_figure_definitions((result,))[0]

    assert definition.publication_role == "diagnostic"
    restored = json.loads(json.dumps(definition.recipe, allow_nan=False))
    assert restored["scientific_review"]["reason"] == "source_mismatch"
