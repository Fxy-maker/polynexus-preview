from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.saxs_engine.figure_evidence import attach_saxs_figure_evidence
from polynexus.core.saxs_engine.figure_common import frame_views_from_engine
from polynexus.core.saxs_engine.figure_static import (
    build_static_saxs_figure_definitions,
)
from polynexus.core.saxs_export_bundle import export_saxs_bundle
from polynexus.core.saxs_result_contract import publish_saxs_result_contract
from polynexus.gui.scientific_review_presentation import scientific_review_display
from tests.test_saxs_1d_review_evidence_binding import _review_payload
from tests.test_saxs_figure_evidence_binding import _static_engine


def _engine_with_2d_review():
    engine = _static_engine()
    engine.cfg.scientific_review = _review_payload(
        source_refs=("sample-0.dat", "sample-1.dat"),
        scope="saxs.2d",
    )
    engine.result = SimpleNamespace(
        parameters={},
        metadata={},
        analysis_evidence={},
        validation_passed=True,
        validation_summary="",
        quality_flags={},
    )
    return engine


def test_2d_review_reaches_result_contract_and_generic_presentation() -> None:
    engine = _engine_with_2d_review()

    publish_saxs_result_contract(engine)

    review = engine.result.parameters["scientific_review"]
    assert review["allowed"] is True
    assert review["scope"] == "saxs.2d"
    display = scientific_review_display(
        engine.result,
        technique="saxs",
        submodule="static",
        language="en",
    )
    assert display.status == "accepted"
    assert "saxs.2d" in display.text


def test_2d_review_reaches_authoritative_quality_evidence(tmp_path) -> None:
    engine = _engine_with_2d_review()

    bundle = export_saxs_bundle(engine, str(tmp_path / "bundle"))

    assert bundle.status == "ok"
    quality = json.loads(
        (tmp_path / "bundle" / "quality_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    assert quality["scientific_review"]["scope"] == "saxs.2d"
    assert quality["scientific_review"]["allowed"] is True
    manifest = json.loads(
        (tmp_path / "bundle" / "bundle_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["files"]["quality_evidence"] == "quality_evidence.json"


def test_2d_review_persists_in_figure_document_and_v2_sidecar(tmp_path) -> None:
    engine = _engine_with_2d_review()
    base = build_static_saxs_figure_definitions(engine)[0]
    detector = replace(
        base,
        figure_id="saxs.static.detector.2d",
        recipe={
            **base.recipe,
            "parameters": {"source_capability": "detector_2d"},
        },
    )
    detector = attach_saxs_figure_evidence(
        (detector,),
        frame_views_from_engine(engine),
        mode="static",
        scientific_review=engine.cfg.scientific_review,
    )[0]

    manifest = FigurePipeline().run(
        output_root=tmp_path / "figures",
        run_id="saxs-2d-review",
        technique="saxs",
        definitions=(detector,),
    )

    entry = manifest.figures[0]
    document = json.loads(
        (tmp_path / "figures" / "runs" / "saxs-2d-review" / entry.document).read_text(
            encoding="utf-8"
        )
    )
    sidecar = json.loads(
        (
            tmp_path
            / "figures"
            / "runs"
            / "saxs-2d-review"
            / entry.capability_report["v2_sidecar"]
        ).read_text(encoding="utf-8")
    )
    document_review = document["recipe"]["evidence"]["quality_provenance"][
        "scientific_review"
    ]
    sidecar_review = sidecar["graph_document"]["metadata"]["recipe"]["evidence"][
        "quality_provenance"
    ][
        "scientific_review"
    ]
    assert document_review == sidecar_review
    assert document_review["scope"] == "saxs.2d"
    assert document_review["allowed"] is True
    assert entry.status == "ready"
    assert entry.publication_role == base.publication_role


def test_2d_review_consumer_projection_remains_fail_closed_for_partial_sources(
    tmp_path,
) -> None:
    engine = _static_engine()
    engine.cfg.scientific_review = _review_payload(
        source_refs=("sample-0.dat",),
        scope="saxs.2d",
    )
    engine.result = SimpleNamespace(
        parameters={},
        metadata={},
        analysis_evidence={},
        validation_passed=True,
        validation_summary="",
        quality_flags={},
    )

    publish_saxs_result_contract(engine)
    assert engine.result.parameters["scientific_review"]["allowed"] is False
    assert engine.result.parameters["scientific_review"]["reason"] == "source_mismatch"
