from __future__ import annotations

from polynexus.gui.results_workbench_profiles import profile_for
from polynexus.gui.main_window_output_mixin import MainWindowOutputMixin


def _link(profile, role: str):
    return next(item for item in profile.figure_links if item.role == role)


def test_saxs_profile_figure_links_use_real_manifest_ids_and_fallback_candidates() -> None:
    static_main = _link(profile_for("saxs.static"), "main")
    assert static_main.key == "saxs.static.comparison"
    assert static_main.candidates == (
        "saxs.static.comparison",
        "saxs.series.static.waterfall",
    )

    temperature_main = _link(profile_for("saxs.temperature"), "main")
    assert temperature_main.candidates == (
        "saxs.temperature.evolution",
        "saxs.temperature.waterfall",
        "saxs.series.temperature.parameters",
    )

    strain_main = _link(profile_for("saxs.strain"), "main")
    assert strain_main.candidates == (
        "saxs.strain.evolution.1d",
        "saxs.series.strain.waterfall",
    )


def test_saxs_support_and_selected_links_remain_outside_main_publication_role() -> None:
    for mode in ("saxs.static", "saxs.temperature", "saxs.strain"):
        profile = profile_for(mode)
        assert all(link.role != "main" for link in profile.figure_links[1:])


def test_results_figure_link_routes_to_first_available_manifest_candidate() -> None:
    class Gallery:
        def __init__(self) -> None:
            self.ids = {"saxs.series.temperature.parameters"}
            self.selected: list[str] = []

        def figure_ids(self):
            return self.ids

        def select_figure(self, key: str, *, emit: bool = True):
            if key in self.ids:
                self.selected.append(key)

    class Window(MainWindowOutputMixin):
        def __init__(self) -> None:
            self.tabs: list[int] = []
            self._chart_gallery = Gallery()
            self._results_panel = type(
                "Panel",
                (),
                {"profile": profile_for("saxs.temperature")},
            )()

        def _jump_to_tab(self, index: int) -> None:
            self.tabs.append(index)

    window = Window()
    window._on_results_figure_link("saxs.temperature.evolution")

    assert window.tabs == [3]
    assert window._chart_gallery.selected == ["saxs.series.temperature.parameters"]


def test_results_figure_link_routes_frame_indexed_diagnostic_from_active_gallery() -> None:
    class Gallery:
        def __init__(self) -> None:
            self.ids = {"nmr.frame.deconvolution.003"}
            self.selected: list[str] = []

        def figure_ids(self):
            return self.ids

        def select_figure(self, key: str, *, emit: bool = True):
            if key in self.ids:
                self.selected.append(key)

    class Window(MainWindowOutputMixin):
        def __init__(self) -> None:
            self.tabs: list[int] = []
            self._chart_gallery = Gallery()
            self._results_panel = type(
                "Panel",
                (),
                {"profile": profile_for("nmr.liquid_h")},
            )()

        def _jump_to_tab(self, index: int) -> None:
            self.tabs.append(index)

    window = Window()
    window._on_results_figure_link("nmr.frame.deconvolution.001")

    assert window.tabs == [3]
    assert window._chart_gallery.selected == ["nmr.frame.deconvolution.003"]
