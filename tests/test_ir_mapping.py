from __future__ import annotations

import json

import numpy as np
import pytest

from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.ir_engine.ir_mapping import (
    IRMappingROISpectrum,
    IRMappingResult,
    build_ir_mapping_figure_definitions,
    validate_ir_mapping_result,
)
from polynexus.core.ir import IREngine
from polynexus.gui.results_workbench_profiles import profile_for


def _mapping_result() -> IRMappingResult:
    return IRMappingResult(
        label="map-a",
        map_values=np.array([[0.1, 0.2], [0.3, np.nan]]),
        row_coordinates=np.array([10.0, 20.0]),
        column_coordinates=np.array([1000.0, 1100.0]),
        invalid_pixel_mask=np.array([[False, False], [False, True]]),
        map_metric="absorbance at 1650 cm^-1",
        roi_spectra=(
            IRMappingROISpectrum(
                roi_id="roi-1",
                label="center",
                wavenumber=np.array([1800.0, 1700.0, 1600.0]),
                absorbance=np.array([0.1, 0.2, 0.15]),
                valid_pixel_count=3,
                assignments=("amide I",),
            ),
        ),
        provenance={"source_kind": "explicit_mapping_payload", "source_id": "map-a.json"},
    )


def _accepted_review_payload(*, source_id: str = "map-a.json") -> dict:
    return {
        "record_id": "review-ir-map-1",
        "scope": "ir.mapping",
        "reviewer": "reviewer-a",
        "reviewed_at": "2026-07-29T00:00:00Z",
        "policy_version": "ir-map-v1",
        "source_refs": [source_id],
        "decisions": {
            "coordinate_convention": "consume supplied row/column coordinates",
            "roi_inclusion_policy": "explicit ROI only",
            "invalid_pixel_policy": "preserve mask; no interpolation",
            "promotion_rule": "accepted source-matching review",
        },
        "status": "accepted",
        "conditions": [],
    }


def test_ir_mapping_contract_rejects_mismatched_geometry() -> None:
    result = _mapping_result()
    result.invalid_pixel_mask = np.zeros((1, 2), dtype=bool)

    with pytest.raises(ValueError, match="invalid_pixel_mask"):
        validate_ir_mapping_result(result)


def test_ir_mapping_provider_emits_main_support_and_diagnostic_definitions() -> None:
    definitions = build_ir_mapping_figure_definitions(_mapping_result())

    assert tuple(item.figure_id for item in definitions) == (
        "ir.mapping.roi",
        "ir.mapping.spectra",
        "ir.mapping.invalid-pixels",
    )
    assert definitions[0].publication_role == "diagnostic"
    assert definitions[1].publication_role == "diagnostic"
    assert definitions[2].publication_role == "diagnostic"
    for definition in definitions:
        validate_figure_definition(definition)


def test_ir_mapping_provider_publishes_a_manifest_with_provenance(tmp_path) -> None:
    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="ir-mapping-1",
        technique="ir",
        definitions=build_ir_mapping_figure_definitions(_mapping_result()),
        profile_id="paper_complete",
    )

    assert [item.figure_id for item in manifest.figures] == [
        "ir.mapping.roi",
        "ir.mapping.spectra",
        "ir.mapping.invalid-pixels",
    ]
    assert all(item.status == "ready" for item in manifest.figures)
    for item in manifest.figures:
        document = json.loads((tmp_path / "runs" / "ir-mapping-1" / item.document).read_text(encoding="utf-8"))
        assert document["recipe"]["provenance"]["source_id"] == "map-a.json"


def test_ir_mapping_provider_keeps_invalid_pixels_out_of_main_values() -> None:
    definition = build_ir_mapping_figure_definitions(_mapping_result())[0]
    source = definition.data_sources[0]

    assert source.values["value"][-1] != source.values["value"][-1]
    assert definition.recipe["valid_pixel_ratio"] == 0.75


def test_ir_engine_handoff_includes_mapping_figures() -> None:
    engine = IREngine()
    engine._mapping_result = _mapping_result()

    definitions = engine.build_figure_definitions()

    assert tuple(item.figure_id for item in definitions) == (
        "ir.mapping.roi",
        "ir.mapping.spectra",
        "ir.mapping.invalid-pixels",
    )


def test_ir_mapping_workbench_links_real_main_support_and_diagnostic_ids() -> None:
    assert tuple(link.key for link in profile_for("ir.mapping").figure_links) == (
        "ir.mapping.roi",
        "ir.mapping.spectra",
        "ir.mapping.invalid-pixels",
    )


def test_ir_mapping_result_exposes_structural_evidence_without_scientific_inference() -> None:
    evidence = _mapping_result().to_evidence()

    mapping = evidence["feature_evidence"]["mapping_evidence"]
    assert evidence["submodule_id"] == "ir.mapping"
    assert mapping["map_shape"] == [2, 2]
    assert mapping["invalid_pixel_count"] == 1
    assert mapping["valid_pixel_ratio"] == 0.75
    assert mapping["status"] == "review_required"
    assert mapping["source_id"] == "map-a.json"


def test_ir_mapping_without_review_is_fail_closed_and_traceable() -> None:
    definitions = build_ir_mapping_figure_definitions(_mapping_result())

    assert [item.publication_role for item in definitions] == [
        "diagnostic",
        "diagnostic",
        "diagnostic",
    ]
    decision = definitions[0].recipe["scientific_review"]
    assert decision == {
        "allowed": False,
        "reason": "review_missing",
        "record_id": "",
        "scope": "ir.mapping",
        "source_ref": "map-a.json",
        "policy_version": "",
    }


def test_ir_mapping_accepted_matching_review_promotes_map_and_roi() -> None:
    result = _mapping_result()
    result.provenance = {
        **result.provenance,
        "scientific_review": _accepted_review_payload(),
    }

    definitions = build_ir_mapping_figure_definitions(result)

    assert [item.publication_role for item in definitions] == ["main", "si", "diagnostic"]
    assert definitions[0].recipe["scientific_review"]["reason"] == "review_accepted"
    assert definitions[1].recipe["scientific_review"]["record_id"] == "review-ir-map-1"


def test_ir_mapping_source_mismatch_remains_diagnostic() -> None:
    result = _mapping_result()
    result.provenance = {
        **result.provenance,
        "scientific_review": _accepted_review_payload(source_id="other-map.json"),
    }

    definitions = build_ir_mapping_figure_definitions(result)

    assert definitions[0].publication_role == "diagnostic"
    assert definitions[1].publication_role == "diagnostic"
    assert definitions[0].recipe["scientific_review"]["reason"] == "source_mismatch"


def test_ir_mapping_review_decision_survives_json_round_trip() -> None:
    result = _mapping_result()
    result.provenance = {
        **result.provenance,
        "scientific_review": _accepted_review_payload(),
    }
    definition = build_ir_mapping_figure_definitions(result)[0]

    encoded = json.dumps(definition.recipe, ensure_ascii=False, allow_nan=False)
    restored = json.loads(encoded)

    assert restored["scientific_review"]["allowed"] is True
    assert restored["scientific_review"]["source_ref"] == "map-a.json"


def test_ir_engine_mapping_handoff_populates_analysis_result() -> None:
    engine = IREngine()
    engine.set_mapping_result(_mapping_result())

    assert engine.result.parameters["map_shape"] == [2, 2]
    assert engine.result.analysis_evidence["submodule_id"] == "ir.mapping"
    assert engine.result.metadata["mapping_source_id"] == "map-a.json"


def test_ir_engine_mapping_handoff_exposes_review_decision() -> None:
    result = _mapping_result()
    result.provenance = {
        **result.provenance,
        "scientific_review": _accepted_review_payload(),
    }
    engine = IREngine()
    engine.set_mapping_result(result)

    assert engine.result.analysis_evidence["feature_evidence"]["mapping_evidence"]["scientific_review"]["allowed"] is True
    assert json.loads(engine.result.metadata["mapping_review_decision"])["record_id"] == "review-ir-map-1"
