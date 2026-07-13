from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import numpy as np

from polynexus.core.waxs_engine.figure_static import build_static_waxs_figure_definitions

from polynexus.core.waxs_engine.figure_common import (
    WAXSScanView,
    classify_waxs_scan_eligibility,
    scan_views_from_engine,
)


def _scan_view(
    *,
    r_squared: float = 0.96,
    two_theta: tuple[float, ...] = (10.0, 12.0, 14.0, 16.0, 18.0),
    intensity: tuple[float, ...] = (1.0, 2.0, 4.0, 2.0, 1.0),
) -> WAXSScanView:
    return WAXSScanView(
        index=0,
        label="scan-0",
        two_theta_deg=two_theta,
        intensity=intensity,
        fit=(),
        background=(),
        peaks=({"two_theta": 14.0, "d_spacing_A": 6.3, "fwhm_deg": 0.4},),
        parameters={"Xc_pct": 35.0, "D_Scherrer_nm": 12.0},
        r_squared=r_squared,
        size_reliability_status="reliable",
        sector_used="full",
    )


def test_reliable_profile_is_main_eligible_without_reanalysis() -> None:
    assert classify_waxs_scan_eligibility(_scan_view()).highest_role == "main"


def test_low_fit_or_short_profile_is_not_main() -> None:
    assert classify_waxs_scan_eligibility(_scan_view(r_squared=0.72)).highest_role == "diagnostic"
    assert classify_waxs_scan_eligibility(
        _scan_view(two_theta=(10.0, 20.0), intensity=(1.0, 2.0))
    ).highest_role == "diagnostic"


def test_intermediate_fit_quality_is_supplementary() -> None:
    assert classify_waxs_scan_eligibility(_scan_view(r_squared=0.87)).highest_role == "si"


def test_scan_views_copy_completed_result_fields_without_reanalysis() -> None:
    result = SimpleNamespace(
        label="result-0",
        two_theta=np.asarray([10.0, 12.0, 14.0, 16.0, 18.0]),
        I=np.asarray([1.0, 2.0, 4.0, 2.0, 1.0]),
        I_fit=np.asarray([1.0, 1.9, 3.8, 1.9, 1.0]),
        I_instrument_background=np.asarray([0.1] * 5),
        peaks=[{"two_theta": 14.0}],
        parameters={"Xc_pct": 35.0},
        r_squared=0.95,
        size_reliability_status="reliable",
        sector_used="full",
    )
    views = scan_views_from_engine(SimpleNamespace(_results=[result]))
    assert len(views) == 1
    assert views[0].two_theta_deg == (10.0, 12.0, 14.0, 16.0, 18.0)
    assert views[0].intensity == (1.0, 2.0, 4.0, 2.0, 1.0)
    assert views[0].parameters["Xc_pct"] == 35.0


def test_scan_parameters_are_recursively_immutable() -> None:
    view = WAXSScanView(
        index=0,
        label="nested",
        two_theta_deg=(10.0, 12.0, 14.0, 16.0, 18.0),
        intensity=(1.0, 2.0, 4.0, 2.0, 1.0),
        fit=(),
        background=(),
        peaks=(),
        parameters={"nested": {"values": [1.0]}},
        r_squared=0.95,
        size_reliability_status="reliable",
        sector_used="full",
    )
    try:
        view.parameters["nested"]["values"].append(2.0)
    except (AttributeError, TypeError):
        pass
    else:
        raise AssertionError("nested WAXS parameters must be immutable")


def _engine(*views: WAXSScanView) -> SimpleNamespace:
    results = []
    for view in views:
        results.append(
            SimpleNamespace(
                label=view.label,
                two_theta=np.asarray(view.two_theta_deg),
                I=np.asarray(view.intensity),
                I_fit=np.asarray(view.fit),
                I_instrument_background=np.asarray(view.background),
                peaks=[dict(peak) for peak in view.peaks],
                parameters=dict(view.parameters),
                r_squared=view.r_squared,
                size_reliability_status=view.size_reliability_status,
                sector_used=view.sector_used,
                quality_flags=list(view.quality_flags),
            )
        )
    return SimpleNamespace(_results=results)


def _definition(definitions, figure_id: str):
    return next(item for item in definitions if item.figure_id == figure_id)


def test_reliable_single_scan_creates_editable_profile_main() -> None:
    definitions = build_static_waxs_figure_definitions(_engine(_scan_view()))
    main = _definition(definitions, "waxs.static.profile")
    assert main.publication_role == "main"
    assert {item["type"] for item in main.objects} >= {"plot_series", "line"}


def test_three_reliable_samples_create_one_metric_comparison() -> None:
    views = [replace(_scan_view(), index=index) for index in range(3)]
    definitions = build_static_waxs_figure_definitions(_engine(*views))
    assert _definition(definitions, "waxs.comparison.peak-position").publication_role == "main"


def test_unreliable_size_is_not_promoted_to_main() -> None:
    views = [
        replace(
            _scan_view(),
            index=index,
            parameters={"Xc_pct": np.nan, "D_Scherrer_nm": 8.0 + index},
            size_reliability_status="unreliable",
        )
        for index in range(3)
    ]
    definitions = build_static_waxs_figure_definitions(_engine(*views))
    assert "waxs.comparison.size" not in {item.figure_id for item in definitions if item.publication_role == "main"}
