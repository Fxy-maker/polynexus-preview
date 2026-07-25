from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from polynexus.gui.analysis_history_service import flatten_params
from polynexus.gui.result_table_models import ResultTableSection
from polynexus.gui.results_table_service import build_results_table_model
from polynexus.gui.results_workbench_profiles import profile_for


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
    assert tuple(link.key for link in profile.figure_links) == figure_keys
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
