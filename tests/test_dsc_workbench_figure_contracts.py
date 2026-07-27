from __future__ import annotations

from polynexus.gui.results_workbench_profiles import profile_for


def _links(mode: str) -> tuple[str, ...]:
    return tuple(link.key for link in profile_for(mode).figure_links)


def test_dsc_profiles_use_publication_provider_manifest_ids() -> None:
    assert _links("dsc.standard")[:2] == (
        "dsc.standard.thermogram",
        "dsc.comparison.thermal-events",
    )
    assert _links("dsc.isothermal")[:2] == (
        "dsc.isothermal.avrami",
        "dsc.isothermal.series",
    )
    assert _links("dsc.nonisothermal")[:2] == (
        "dsc.nonisothermal.conversion",
        "dsc.nonisothermal.kissinger",
    )


def test_dsc_profiles_keep_diagnostics_out_of_main_and_support_links() -> None:
    for mode in ("dsc.standard", "dsc.isothermal", "dsc.nonisothermal"):
        profile = profile_for(mode)
        assert profile.figure_links[0].role == "main"
        assert all(link.role != "main" for link in profile.figure_links[1:])


def test_dsc_profiles_have_mode_specific_review_tabs() -> None:
    assert profile_for("dsc.standard").tab_labels == (
        "Thermal events",
        "Support evidence",
        "Baseline diagnostics",
    )
    assert profile_for("dsc.isothermal").tab_labels == (
        "Crystallization evolution",
        "Avrami fit",
        "Fit diagnostics",
    )
    assert profile_for("dsc.nonisothermal").tab_labels == (
        "Conversion",
        "Kinetic methods",
        "Method diagnostics",
    )
