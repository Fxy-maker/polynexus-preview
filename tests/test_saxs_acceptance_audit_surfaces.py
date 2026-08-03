from __future__ import annotations

import copy
import json
from types import SimpleNamespace

from polynexus.core.saxs_engine.figure_common import SAXSFrameView
from polynexus.core.saxs_engine.figure_evidence import attach_saxs_figure_evidence
from polynexus.core.figures.contracts import FigureDefinition
from polynexus.core.saxs_export_bundle import _quality_evidence_payload
from polynexus.gui.saxs_results_table_service import build_saxs_results_presentation


def _audit() -> dict[str, object]:
    return {
        "status": "diagnostic_only",
        "automated_validation_passed": False,
        "existing_publication_gate": {
            "paper_figure_candidate": None,
            "paper_conclusion_candidate": None,
            "paper_conclusion_ready": None,
        },
        "evidence_levels": {"metric:porod": ["Diagnostic"]},
        "provenance_validity": {},
        "reliability": {"status": None, "reason": None},
        "reason_codes": ["automated_validation_failed", "porod_unresolved"],
        "audit_scope": "existing_gates_only",
        "publication_decision_changed": False,
    }


def _frame() -> SAXSFrameView:
    return SAXSFrameView(
        index=0,
        label="frame_001",
        condition=25.0,
        q=(0.01, 0.02),
        intensity=(10.0, 5.0),
        parameters={"scientific_acceptance_audit": _audit()},
        analysis=SimpleNamespace(
            final_parameters={"scientific_acceptance_audit": _audit()}
        ),
    )


def test_workbench_surfaces_existing_audit_without_mutating_parameters() -> None:
    params = {"scientific_acceptance_audit": _audit(), "_batch_data": []}
    before = copy.deepcopy(params)

    presentation = build_saxs_results_presentation(
        params,
        submodule="saxs.static",
        language="en",
    )

    assert "diagnostic_only" in presentation.risk_text
    assert "automated_validation_failed" in presentation.risk_text
    assert "existing gates" in presentation.next_text.lower()
    assert params == before


def test_figure_provenance_carries_detached_audit_without_role_drift() -> None:
    definition = FigureDefinition(
        figure_id="saxs.static.profile",
        technique="saxs",
        scope="frame",
        title="Static profile",
        category="main",
        layout=None,
        data_sources=(),
        objects=(),
        recipe={"evidence": {"roles": {0: "si"}}},
        style_profile="default",
        publication_role="si",
        display_order=10,
    )
    audit = _audit()

    attached = attach_saxs_figure_evidence(
        (definition,),
        (_frame(),),
        mode="static",
        acceptance_audit=audit,
    )[0]
    provenance = attached.recipe["evidence"]["quality_provenance"]

    assert attached.publication_role == "si"
    assert provenance["scientific_acceptance_audit"] == audit
    json.dumps(provenance, allow_nan=False)
    audit["status"] = "review_required"
    assert provenance["scientific_acceptance_audit"]["status"] == "diagnostic_only"


def test_quality_export_carries_existing_audit_only() -> None:
    audit = _audit()
    engine = SimpleNamespace(
        result=SimpleNamespace(
            parameters={"scientific_acceptance_audit": audit},
            quality_flags={},
            validation_warnings=[],
        ),
        _temperature_result=None,
        _strain_result=None,
        _batch_results=[],
        _analysis=None,
    )

    payload = _quality_evidence_payload(engine, "static")

    assert payload["scientific_acceptance_audit"] == audit
    json.dumps(payload, allow_nan=False)


def test_surface_consumers_do_not_invent_missing_audit() -> None:
    params = {"_batch_data": []}
    presentation = build_saxs_results_presentation(
        params,
        submodule="saxs.static",
        language="en",
    )
    definition = FigureDefinition(
        figure_id="saxs.static.profile",
        technique="saxs",
        scope="frame",
        title="Static profile",
        category="main",
        layout=None,
        data_sources=(),
        objects=(),
        recipe={},
        style_profile="default",
        publication_role="main",
        display_order=10,
    )
    attached = attach_saxs_figure_evidence(
        (definition,),
        (_frame(),),
        mode="static",
    )[0]
    export_payload = _quality_evidence_payload(
        SimpleNamespace(
            result=SimpleNamespace(
                parameters={}, quality_flags={}, validation_warnings=[]
            ),
            _temperature_result=None,
            _strain_result=None,
            _batch_results=[],
            _analysis=None,
        ),
        "static",
    )

    assert "diagnostic_only" not in presentation.risk_text
    assert "scientific_acceptance_audit" not in attached.recipe["evidence"]["quality_provenance"]
    assert "scientific_acceptance_audit" not in export_payload
