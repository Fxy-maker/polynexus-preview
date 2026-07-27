from __future__ import annotations

from polynexus.gui.results_workbench_profiles import profile_for


def test_waxs_profiles_use_real_static_temperature_and_strain_manifest_ids() -> None:
    assert tuple(link.key for link in profile_for("waxs.static").figure_links[:2]) == (
        "waxs.static.profile",
        "waxs.static.fit.si",
    )
    assert tuple(link.key for link in profile_for("waxs.temperature").figure_links[:2]) == (
        "waxs.temperature.evolution",
        "waxs.temperature.full-series.si",
    )
    assert tuple(link.key for link in profile_for("waxs.strain").figure_links[:2]) == (
        "waxs.strain.evolution",
        "waxs.strain.full-series.si",
    )


def test_waxs_profiles_have_mode_specific_review_tabs() -> None:
    assert profile_for("waxs.static").tab_labels == (
        "Pattern & phase",
        "Size & orientation",
        "Peak diagnostics",
    )
    assert profile_for("waxs.temperature").tab_labels == (
        "Phase evolution",
        "Trend support",
        "Sequence diagnostics",
    )
    assert profile_for("waxs.strain").tab_labels == (
        "Orientation & phase",
        "Response support",
        "Detector diagnostics",
    )
