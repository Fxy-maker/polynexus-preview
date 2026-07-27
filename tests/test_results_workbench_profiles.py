from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from polynexus.gui.analysis_history_service import flatten_params
from polynexus.gui.result_table_models import ResultTableSection
from polynexus.gui.results_table_service import build_results_table_model
from polynexus.gui.results_workbench_profiles import WorkbenchFigureLink, profile_for


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    ("mode", "title", "tabs", "figure_keys"),
    [
        (
            "saxs.static",
            "SAXS / Static structure",
            ("Structure comparison", "Support evidence", "Frame diagnostics"),
            ("saxs.static.comparison", "saxs.static.correlation.support"),
        ),
        (
            "saxs.temperature",
            "SAXS / Temperature evolution",
            ("Evolution", "Transition support", "Sequence diagnostics"),
            ("saxs.temperature.evolution", "saxs.temperature.waterfall"),
        ),
        (
            "saxs.strain",
            "SAXS / Strain evolution",
            ("Morphology evolution", "Orientation & phase", "Sequence diagnostics"),
            ("saxs.strain.evolution.1d", "saxs.strain.phase-evidence"),
        ),
    ],
)
def test_saxs_profiles_define_mode_specific_narrative_and_figure_links(
    mode: str,
    title: str,
    tabs: tuple[str, str, str],
    figure_keys: tuple[str, str],
) -> None:
    profile = profile_for(mode, language="en")

    assert profile.key == mode
    assert profile.title == title
    assert profile.tab_labels == tabs
    assert tuple(link.key for link in profile.figure_links[:2]) == figure_keys
    assert profile.empty_state
    assert profile.error_state


def test_profiles_cover_all_structured_analysis_modes_and_unknowns() -> None:
    for mode in (
        "dsc.standard",
        "dsc.isothermal",
        "dsc.nonisothermal",
        "waxs.static",
        "waxs.temperature",
        "waxs.strain",
        "ir.standard",
        "ir.mapping",
        "ir.temperature_2d",
        "nmr.liquid_h",
        "nmr.liquid_c",
        "nmr.solid_h",
        "nmr.solid_c",
        "joint",
    ):
        profile = profile_for(mode, language="en")
        assert profile.key == mode
        assert profile.title
        assert len(profile.tab_labels) == 3
        assert profile.review_action.label

    assert profile_for("unknown.mode", language="en").key == "generic"


def test_structured_result_model_carries_the_mode_profile() -> None:
    model = build_results_table_model(
        {"batch_frames": 2, "_batch_data": [{"temperature_C": 180.0}]},
        ordered_columns_fn=lambda columns: list(columns),
        flatten_params_fn=flatten_params,
        technique="saxs",
        submodule="temperature",
        language="en",
    )

    assert model.profile is not None
    assert model.profile.key == "saxs.temperature"
    assert model.profile.title == "SAXS / Temperature evolution"


def test_panel_renders_profile_narrative_figure_links_and_empty_state(app: QApplication) -> None:
    from polynexus.gui.widgets.results_table_panel import ResultsTablePanel

    panel = ResultsTablePanel()
    requested: list[str] = []
    panel.figure_link_requested.connect(requested.append)
    panel.set_content(
        heroes=(),
        primary=ResultTableSection.empty(),
        detail=ResultTableSection.empty(),
        diagnostics=ResultTableSection.empty(),
        profile=profile_for("saxs.strain", language="en"),
    )

    assert panel.workbench_title.text() == "SAXS / Strain evolution"
    assert panel.workbench_subtitle.text()
    assert [panel.tabs.tabText(i) for i in range(3)] == [
        "Morphology evolution",
        "Orientation & phase",
        "Sequence diagnostics",
    ]
    assert panel.workbench_state.text() == panel.profile.empty_state
    link = panel.findChild(type(panel.workbench_review_action), "results_figure_link_saxs_strain_evolution_1d")
    assert link is not None
    link.click()
    assert requested == ["saxs.strain.evolution.1d"]

    panel.set_content(
        heroes=(),
        primary=ResultTableSection.empty(),
        detail=ResultTableSection.empty(),
        diagnostics=ResultTableSection.empty(),
        profile=panel.profile,
        error_text="synthetic failure",
    )
    assert panel.workbench_state.text() == "synthetic failure"


def test_workbench_figure_link_resolves_exact_candidates_before_prefixes() -> None:
    link = WorkbenchFigureLink(
        "nmr.frame.deconvolution.001",
        "RESULTS_WORKBENCH_FIGURE_DIAGNOSTIC",
        "diagnostic",
        ("nmr.frame.deconvolution.000",),
        ("nmr.frame.deconvolution.",),
    )

    assert link.resolve({"nmr.frame.deconvolution.003", "nmr.frame.deconvolution.001"}) == (
        "nmr.frame.deconvolution.001"
    )


def test_workbench_figure_link_resolves_prefixes_deterministically() -> None:
    link = WorkbenchFigureLink(
        "nmr.frame.deconvolution.001",
        "RESULTS_WORKBENCH_FIGURE_DIAGNOSTIC",
        "diagnostic",
        prefixes=("nmr.frame.deconvolution.",),
    )

    assert link.resolve({"nmr.frame.deconvolution.010", "nmr.frame.deconvolution.002"}) == (
        "nmr.frame.deconvolution.002"
    )


@pytest.mark.parametrize(
    ("mode", "diagnostic_key", "diagnostic_prefix"),
    [
        ("saxs.static", "saxs.static.frame.000.correlation", "saxs.static.frame."),
        ("saxs.temperature", "saxs.temperature.evidence.000", "saxs.temperature.evidence."),
        ("saxs.strain", "saxs.strain.low-q.diagnostic", ""),
        ("dsc.standard", "dsc.standard.integration.diagnostic", ""),
        ("dsc.isothermal", "dsc.isothermal.fit.diagnostic", ""),
        ("dsc.nonisothermal", "dsc.nonisothermal.kinetics.diagnostic", ""),
        ("waxs.static", "waxs.static.fit.diagnostic", ""),
        ("waxs.temperature", "waxs.temperature.sequence.diagnostic", ""),
        ("waxs.strain", "waxs.strain.sequence.diagnostic", ""),
        ("ir.standard", "ir.frame.comparison.001", "ir.frame.comparison."),
        ("ir.temperature_2d", "ir.temperature_2d.synchronous-correlation", ""),
        ("ir.mapping", "ir.mapping.invalid-pixels", ""),
        ("nmr.liquid_h", "nmr.frame.deconvolution.001", "nmr.frame.deconvolution."),
        ("nmr.liquid_c", "nmr.frame.deconvolution.001", "nmr.frame.deconvolution."),
        ("nmr.solid_h", "nmr.frame.deconvolution.001", "nmr.frame.deconvolution."),
        ("nmr.solid_c", "nmr.frame.deconvolution.001", "nmr.frame.deconvolution."),
        ("joint", "joint.series.coverage", ""),
    ],
)
def test_every_structured_profile_exposes_one_diagnostic_figure_link(
    mode: str,
    diagnostic_key: str,
    diagnostic_prefix: str,
) -> None:
    profile = profile_for(mode)
    links = [link for link in profile.figure_links if link.role == "diagnostic"]

    assert len(links) == 1
    assert links[0].key == diagnostic_key
    if diagnostic_prefix:
        assert diagnostic_prefix in links[0].prefixes
