"""Typed, technique-neutral presentation profiles for the Results Workbench.

Profiles describe the user's review path.  They do not calculate scientific
values and they do not decide whether evidence is publishable; those decisions
remain in the analysis/evidence services.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .i18n import tr_for_language


@dataclass(frozen=True)
class WorkbenchActionSpec:
    key: str
    label_key: str
    language: str = "en"

    @property
    def label(self) -> str:
        return self.label_for(self.language)

    def label_for(self, language: str) -> str:
        return tr_for_language(self.label_key, language)


@dataclass(frozen=True)
class WorkbenchFigureLink:
    key: str
    label_key: str
    role: str
    alternatives: tuple[str, ...] = ()

    @property
    def candidates(self) -> tuple[str, ...]:
        return (self.key, *self.alternatives)

    def label_for(self, language: str) -> str:
        return tr_for_language(self.label_key, language)


@dataclass(frozen=True)
class ResultsWorkbenchProfile:
    key: str
    title_key: str
    subtitle_key: str
    tab_keys: tuple[str, str, str]
    review_action: WorkbenchActionSpec
    figure_links: tuple[WorkbenchFigureLink, ...]
    empty_state_key: str
    error_state_key: str
    language: str = "en"

    def for_language(self, language: str) -> "ResultsWorkbenchProfile":
        return replace(
            self,
            language=language,
            review_action=replace(self.review_action, language=language),
        )

    @property
    def title(self) -> str:
        return tr_for_language(self.title_key, self.language)

    @property
    def subtitle(self) -> str:
        return tr_for_language(self.subtitle_key, self.language)

    @property
    def tab_labels(self) -> tuple[str, str, str]:
        return tuple(tr_for_language(key, self.language) for key in self.tab_keys)

    @property
    def empty_state(self) -> str:
        return tr_for_language(self.empty_state_key, self.language)

    @property
    def error_state(self) -> str:
        return tr_for_language(self.error_state_key, self.language)


def _profile(
    key: str,
    *,
    title: str,
    subtitle: str,
    tabs: tuple[str, str, str],
    figures: tuple[tuple[str, str, str], ...],
    action: str = "RESULTS_WORKBENCH_REVIEW_ACTION",
) -> ResultsWorkbenchProfile:
    return ResultsWorkbenchProfile(
        key=key,
        title_key=title,
        subtitle_key=subtitle,
        tab_keys=tabs,
        review_action=WorkbenchActionSpec(f"{key}.review", action),
        figure_links=tuple(WorkbenchFigureLink(*figure) for figure in figures),
        empty_state_key="RESULTS_WORKBENCH_EMPTY",
        error_state_key="RESULTS_WORKBENCH_ERROR",
    )


_PROFILES = {
    "saxs.static": _profile(
        "saxs.static",
        title="RESULTS_WORKBENCH_SAXS_STATIC_TITLE",
        subtitle="RESULTS_WORKBENCH_SAXS_STATIC_SUBTITLE",
        tabs=(
            "RESULTS_WORKBENCH_SAXS_STATIC_PRIMARY",
            "RESULTS_WORKBENCH_SAXS_STATIC_SUPPORT",
            "RESULTS_WORKBENCH_SAXS_STATIC_DIAGNOSTICS",
        ),
        figures=(
            (
                "saxs.static.comparison",
                "RESULTS_WORKBENCH_FIGURE_MAIN",
                "main",
                ("saxs.series.static.waterfall",),
            ),
            ("saxs.static.correlation.support", "RESULTS_WORKBENCH_FIGURE_SUPPORT", "support"),
        ),
    ),
    "saxs.temperature": _profile(
        "saxs.temperature",
        title="RESULTS_WORKBENCH_SAXS_TEMPERATURE_TITLE",
        subtitle="RESULTS_WORKBENCH_SAXS_TEMPERATURE_SUBTITLE",
        tabs=(
            "RESULTS_WORKBENCH_SAXS_TEMPERATURE_PRIMARY",
            "RESULTS_WORKBENCH_SAXS_TEMPERATURE_SUPPORT",
            "RESULTS_WORKBENCH_SAXS_TEMPERATURE_DIAGNOSTICS",
        ),
        figures=(
            (
                "saxs.temperature.evolution",
                "RESULTS_WORKBENCH_FIGURE_MAIN",
                "main",
                (
                    "saxs.temperature.waterfall",
                    "saxs.series.temperature.parameters",
                ),
            ),
            ("saxs.temperature.waterfall", "RESULTS_WORKBENCH_FIGURE_SELECTED", "selected"),
        ),
    ),
    "saxs.strain": _profile(
        "saxs.strain",
        title="RESULTS_WORKBENCH_SAXS_STRAIN_TITLE",
        subtitle="RESULTS_WORKBENCH_SAXS_STRAIN_SUBTITLE",
        tabs=(
            "RESULTS_WORKBENCH_SAXS_STRAIN_PRIMARY",
            "RESULTS_WORKBENCH_SAXS_STRAIN_SUPPORT",
            "RESULTS_WORKBENCH_SAXS_STRAIN_DIAGNOSTICS",
        ),
        figures=(
            (
                "saxs.strain.evolution.1d",
                "RESULTS_WORKBENCH_FIGURE_MAIN",
                "main",
                ("saxs.series.strain.waterfall",),
            ),
            ("saxs.strain.phase-evidence", "RESULTS_WORKBENCH_FIGURE_SELECTED", "selected"),
        ),
    ),
}


_GENERIC_NARRATIVES = {
    "dsc.standard": ("DSC / Thermal events", "Thermal events and baseline support"),
    "dsc.isothermal": ("DSC / Isothermal crystallization", "Crystallization evolution and Avrami support"),
    "dsc.nonisothermal": ("DSC / Non-isothermal kinetics", "Conversion and kinetic-method agreement"),
    "waxs.static": ("WAXS / Static phase structure", "Pattern, phase, size and orientation evidence"),
    "waxs.temperature": ("WAXS / Temperature evolution", "Phase transition and trend support"),
    "waxs.strain": ("WAXS / Strain evolution", "Orientation, phase and size evidence"),
    "ir.standard": ("IR / Spectrum and bands", "Band assignments and baseline support"),
    "ir.mapping": ("IR / Mapping", "ROI spectra, assignment and pixel diagnostics"),
    "ir.temperature_2d": ("IR / Temperature evolution", "Band trends and map support"),
    "nmr.liquid_h": ("NMR / Liquid ¹H", "Peaks, assignments and solvent support"),
    "nmr.liquid_c": ("NMR / Liquid ¹³C", "Peaks, assignments and solvent support"),
    "nmr.solid_h": ("NMR / Solid ¹H", "Phase, composition and assignment coverage"),
    "nmr.solid_c": ("NMR / Solid ¹³C", "Phase, composition and assignment coverage"),
    "joint": ("Joint / Cross-technique review", "Consistency, conflicts and provenance"),
}

_TECHNIQUE_FIGURES = {
    "dsc.standard": (
        ("dsc.standard.thermogram", "RESULTS_WORKBENCH_FIGURE_MAIN", "main"),
        ("dsc.comparison.thermal-events", "RESULTS_WORKBENCH_FIGURE_SUPPORT", "support"),
    ),
    "dsc.isothermal": (
        ("dsc.isothermal.avrami", "RESULTS_WORKBENCH_FIGURE_MAIN", "main"),
        ("dsc.isothermal.series", "RESULTS_WORKBENCH_FIGURE_SUPPORT", "support"),
    ),
    "dsc.nonisothermal": (
        ("dsc.nonisothermal.conversion", "RESULTS_WORKBENCH_FIGURE_MAIN", "main"),
        ("dsc.nonisothermal.kissinger", "RESULTS_WORKBENCH_FIGURE_SUPPORT", "support"),
    ),
}

_TECHNIQUE_TABS = {
    "dsc.standard": (
        "RESULTS_WORKBENCH_DSC_STANDARD_PRIMARY",
        "RESULTS_WORKBENCH_DSC_STANDARD_SUPPORT",
        "RESULTS_WORKBENCH_DSC_STANDARD_DIAGNOSTICS",
    ),
    "dsc.isothermal": (
        "RESULTS_WORKBENCH_DSC_ISOTHERMAL_PRIMARY",
        "RESULTS_WORKBENCH_DSC_ISOTHERMAL_SUPPORT",
        "RESULTS_WORKBENCH_DSC_ISOTHERMAL_DIAGNOSTICS",
    ),
    "dsc.nonisothermal": (
        "RESULTS_WORKBENCH_DSC_NONISOTHERMAL_PRIMARY",
        "RESULTS_WORKBENCH_DSC_NONISOTHERMAL_SUPPORT",
        "RESULTS_WORKBENCH_DSC_NONISOTHERMAL_DIAGNOSTICS",
    ),
}

for _key, (_title, _subtitle) in _GENERIC_NARRATIVES.items():
    _PROFILES[_key] = _profile(
        _key,
        title=f"RESULTS_WORKBENCH_{_key.upper().replace('.', '_')}_TITLE",
        subtitle=f"RESULTS_WORKBENCH_{_key.upper().replace('.', '_')}_SUBTITLE",
        tabs=_TECHNIQUE_TABS.get(
            _key,
            (
                "RESULTS_WORKBENCH_PRIMARY",
                "RESULTS_WORKBENCH_SUPPORT",
                "RESULTS_WORKBENCH_DIAGNOSTICS",
            ),
        ),
        figures=_TECHNIQUE_FIGURES.get(
            _key,
            (
                (f"{_key}.main", "RESULTS_WORKBENCH_FIGURE_MAIN", "main"),
                (f"{_key}.support", "RESULTS_WORKBENCH_FIGURE_SUPPORT", "support"),
            ),
        ),
    )


_PROFILES["generic"] = _profile(
    "generic",
    title="RESULTS_WORKBENCH_GENERIC_TITLE",
    subtitle="RESULTS_WORKBENCH_GENERIC_SUBTITLE",
    tabs=(
        "RESULTS_TAB_KEY",
        "RESULTS_TAB_DETAIL",
        "RESULTS_TAB_DIAGNOSTICS",
    ),
    figures=(),
)


def profile_for(mode: str | None, *, language: str = "en") -> ResultsWorkbenchProfile:
    """Return an immutable profile, falling back to the generic shell."""
    key = str(mode or "").strip().lower()
    if key == "saxs":
        key = "saxs.static"
    return _PROFILES.get(key, _PROFILES["generic"]).for_language(language)
