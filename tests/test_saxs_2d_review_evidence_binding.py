from __future__ import annotations

import json
from dataclasses import replace

from polynexus.core.saxs_engine.figure_evidence import attach_saxs_figure_evidence
from polynexus.core.saxs_engine.figure_static import (
    build_static_saxs_figure_definitions,
)
from tests.test_saxs_1d_review_evidence_binding import (
    _review_payload,
)
from tests.test_saxs_figure_evidence_binding import _frame, _static_engine


def test_2d_review_binds_detector_definition_without_promoting_1d_definition() -> None:
    engine = _static_engine()
    definitions = build_static_saxs_figure_definitions(engine)
    detector = replace(
        definitions[0],
        figure_id="saxs.static.detector.2d",
        recipe={
            **definitions[0].recipe,
            "parameters": {"source_capability": "detector_2d"},
        },
    )
    frames = tuple(
        _frame(index=index, source_path=f"sample-{index}.dat")
        for index in range(2)
    )
    attached = attach_saxs_figure_evidence(
        (definitions[0], detector),
        frames,
        mode="static",
        scientific_review=_review_payload(
            source_refs=("sample-0.dat", "sample-1.dat"),
            scope="saxs.2d",
        ),
    )

    one_d_review = attached[0].recipe["evidence"]["quality_provenance"][
        "scientific_review"
    ]
    two_d_review = attached[1].recipe["evidence"]["quality_provenance"][
        "scientific_review"
    ]
    json.dumps(two_d_review, allow_nan=False)
    assert one_d_review["reason"] == "scope_mismatch"
    assert two_d_review["allowed"] is True
    assert two_d_review["scope"] == "saxs.2d"
    assert attached[0].publication_role == definitions[0].publication_role


def test_2d_review_partial_source_match_remains_fail_closed() -> None:
    engine = _static_engine()
    definitions = build_static_saxs_figure_definitions(engine)
    detector = replace(
        definitions[0],
        figure_id="saxs.static.detector.2d",
        recipe={
            **definitions[0].recipe,
            "parameters": {"source_capability": "detector_2d"},
        },
    )
    frames = tuple(
        _frame(index=index, source_path=f"sample-{index}.dat")
        for index in range(2)
    )

    attached = attach_saxs_figure_evidence(
        (detector,),
        frames,
        mode="static",
        scientific_review=_review_payload(
            source_refs=("sample-0.dat",),
            scope="saxs.2d",
        ),
    )

    review = attached[0].recipe["evidence"]["quality_provenance"][
        "scientific_review"
    ]
    assert review["allowed"] is False
    assert review["reason"] == "source_mismatch"
