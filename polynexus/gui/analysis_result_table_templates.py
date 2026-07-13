"""Explicit Wave 2 result-table templates for DSC, IR, WAXS, and NMR."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisFieldSpec:
    key: str
    label_key: str
    unit: str = ""
    digits: int | None = None
    importance: str = "detail"
    aliases: tuple[str, ...] = ()
    provenance_key: str = ""
    status_key: str = ""

    @property
    def source_keys(self) -> tuple[str, ...]:
        return (self.key, *self.aliases)


@dataclass(frozen=True)
class AnalysisResultTemplate:
    key: str
    hero_fields: tuple[AnalysisFieldSpec, ...]
    primary_fields: tuple[AnalysisFieldSpec, ...]
    diagnostic_keys: tuple[str, ...] = ()


def _f(key: str, label: str, unit: str = "", digits: int | None = None, importance: str = "detail", aliases: tuple[str, ...] = (), provenance: str = "", status: str = "") -> AnalysisFieldSpec:
    return AnalysisFieldSpec(key, f"TABLE_ANALYSIS_{label}", unit, digits, importance, aliases, provenance, status)


_SCAN = _f("scan", "SCAN")
_TG = _f("Tg_C", "TG", "°C", 1, "hero", ("Tg",))
_TM = _f("Tm_peak_C", "TM_PEAK", "°C", 1, "hero", ("Tm_C",))
_DHM = _f("DHm_Jg", "DHM", "J/g", 2, "hero", ("DHm",))
_TC = _f("Tc_C", "TC", "°C", 1, "primary", ("Tcc_C", "Tc"))
_XC = _f("Xc_pct", "XC", "%", 2, "hero", ("Xc", "crystallinity_pct"))
_STATUS = _f("status", "STATUS")
_EVENT_SUPPORT = _f(
    "event_support_status",
    "EVENT_SUPPORT",
    "",
    3,
    "primary",
    ("event_support_score", "event_support"),
    "event_support_source",
    "event_support_status",
)

_KINETICS = (
    _f("time_s", "TIME", "s", 2, "primary", ("time",)),
    _f("temperature_C", "TEMPERATURE", "°C", 1, "primary", ("T_C",)),
    _f("conversion_pct", "CONVERSION", "%", 2, "hero", ("alpha_pct", "alpha")),
    _f("Avrami_n", "AVRAMI_N", "", 3, "hero", ("n",)),
    _f("Kissinger_Ea_kJ_mol", "KISSINGER_EA", "kJ/mol", 2, "hero", ("Ea_Kissinger_kJ_mol",)),
    _f("Ozawa_Ea_kJ_mol", "OZAWA_EA", "kJ/mol", 2, "primary", ("Ea_Ozawa_kJ_mol",)),
    _f("Mo_Ea_kJ_mol", "MO_EA", "kJ/mol", 2, "primary", ("Ea_Mo_kJ_mol",)),
    _f("Friedman_Ea_kJ_mol", "FRIEDMAN_EA", "kJ/mol", 2, "primary", ("Ea_Friedman_kJ_mol",)),
    _f("fit_quality", "FIT_QUALITY", "", 3, "primary", ("r2", "R2")),
)

_DSC_STANDARD = AnalysisResultTemplate(
    "dsc.standard",
    (_TG, _TM, _DHM, _XC),
    (_SCAN, _TG, _TM, _DHM, _TC, _XC, _EVENT_SUPPORT, _STATUS),
    ("baseline_stability", "integration_sensitivity", "peak_decomposition", "thermodynamic_consistency"),
)
_DSC_ISOTHERMAL = AnalysisResultTemplate(
    "dsc.isothermal",
    (_KINETICS[2], _KINETICS[3], _KINETICS[-1]),
    (_KINETICS[0], _KINETICS[2], _KINETICS[3], _KINETICS[-1]),
    ("avrami", "fit_quality", "conversion_support"),
)
_DSC_NONISOTHERMAL = AnalysisResultTemplate("dsc.nonisothermal", (_KINETICS[4], _KINETICS[5], _KINETICS[-1]), _KINETICS, ("kissinger", "ozawa", "mo", "friedman", "fit_quality"))

_IR_STANDARD = AnalysisResultTemplate(
    "ir.standard",
    (_f("match_score", "MATCH_SCORE", "", 3, "hero"), _f("assignment_confidence", "ASSIGNMENT_CONFIDENCE", "", 3, "hero"), _f("crystallinity_index", "CRYSTALLINITY_INDEX", "", 3, "hero")),
    (_f("sample", "SAMPLE"), _f("material_match", "MATERIAL_MATCH"), _f("match_score", "MATCH_SCORE", "", 3, "hero"), _f("peak_count", "PEAK_COUNT", "", 0, "primary"), _f("band_hit_count", "BAND_HIT_COUNT", "", 0, "primary"), _f("assignment_confidence", "ASSIGNMENT_CONFIDENCE", "", 3, "hero"), _f("crystallinity_index", "CRYSTALLINITY_INDEX", "", 3, "hero", ("IR_CI",)), _STATUS),
    ("peak_wavenumber", "peak_height", "peak_area", "peak_FWHM", "assignment", "assignment_source", "assignment_confidence"),
)
_IR_2D = AnalysisResultTemplate(
    "ir.temperature_2d",
    (_f("transition_temperature_C", "TRANSITION_TEMPERATURE", "°C", 1, "hero", ("transition_C",)), _f("synchronous_support", "SYNCHRONOUS_SUPPORT", "", 3, "hero"), _f("asynchronous_support", "ASYNCHRONOUS_SUPPORT", "", 3, "hero")),
    (_f("temperature_C", "TEMPERATURE", "°C", 1, "primary"), _f("time_s", "TIME", "s", 2, "primary"), _f("band_tracking_status", "BAND_TRACKING_STATUS"), _f("transition_temperature_C", "TRANSITION_TEMPERATURE", "°C", 1, "hero"), _f("synchronous_support", "SYNCHRONOUS_SUPPORT", "", 3, "hero"), _f("asynchronous_support", "ASYNCHRONOUS_SUPPORT", "", 3, "hero"), _f("low_confidence_frame_ratio", "LOW_CONFIDENCE_RATIO", "%", 2, "primary"), _STATUS),
    ("matrix_shape", "nan_ratio", "correlation_quality", "band_tracking_reason"),
)
_IR_MAPPING = AnalysisResultTemplate("ir.mapping", _IR_STANDARD.hero_fields, _IR_STANDARD.primary_fields, _IR_STANDARD.diagnostic_keys + ("map_shape", "pixel_valid_ratio"))

_WAXS_STATIC = AnalysisResultTemplate(
    "waxs.static",
    (_XC, _f("D_Scherrer_nm", "SCHERRER_SIZE", "nm", 2, "hero", ("D_nm",)), _f("physical_support_score", "PHYSICAL_SUPPORT", "", 3, "hero")),
    (_f("sample", "SAMPLE"), _f("condition", "CONDITION"), _XC, _f("D_Scherrer_nm", "SCHERRER_SIZE", "nm", 2, "hero", ("D_nm",)), _f("dominant_crystal_type", "DOMINANT_CRYSTAL"), _f("peak_count", "PEAK_COUNT", "", 0, "primary"), _f("physical_support_score", "PHYSICAL_SUPPORT", "", 3, "hero"), _STATUS),
    ("peak_2theta", "peak_d_A", "peak_FWHM", "peak_area", "phase_assignment", "peak_support"),
)
_WAXS_TEMPERATURE = AnalysisResultTemplate("waxs.temperature", (_XC, _f("D_Scherrer_nm", "SCHERRER_SIZE", "nm", 2, "hero")), (_f("temperature_C", "TEMPERATURE", "°C", 1, "primary"), _XC, _f("D_Scherrer_nm", "SCHERRER_SIZE", "nm", 2, "hero"), _f("trend_support", "TREND_SUPPORT", "", 3, "primary"), _f("crystal_type_transition", "CRYSTAL_TRANSITION"), _f("orientation_index", "ORIENTATION", "", 3, "primary"), _STATUS), _WAXS_STATIC.diagnostic_keys + ("temperature_axis_source",))
_WAXS_STRAIN = AnalysisResultTemplate("waxs.strain", (_XC, _f("orientation_index", "ORIENTATION", "", 3, "hero")), (_f("strain_pct", "STRAIN", "%", 1, "primary"), _XC, _f("D_Scherrer_nm", "SCHERRER_SIZE", "nm", 2, "hero"), _f("trend_support", "TREND_SUPPORT", "", 3, "primary"), _f("crystal_type_transition", "CRYSTAL_TRANSITION"), _f("orientation_index", "ORIENTATION", "", 3, "hero"), _STATUS), _WAXS_STATIC.diagnostic_keys + ("strain_axis_source",))

_NMR_COMMON = (
    _f("spectrum", "SPECTRUM"), _f("nucleus", "NUCLEUS"), _f("sample_state", "SAMPLE_STATE"), _f("peak_count", "PEAK_COUNT", "", 0, "primary"), _f("dominant_peak_ppm", "DOMINANT_PEAK", "ppm", 3, "hero", ("dominant_peak",)), _f("median_SNR", "MEDIAN_SNR", "", 2, "hero", ("SNR_median",)), _f("mean_FWHM_ppm", "MEAN_FWHM", "ppm", 3, "primary", ("FWHM_mean",)), _f("fit_quality", "FIT_QUALITY", "", 3, "primary", ("r2",)), _STATUS,
)
_NMR_LIQUID_H = AnalysisResultTemplate("nmr.liquid_h", (_NMR_COMMON[4], _NMR_COMMON[5]), _NMR_COMMON, ("peak_ppm", "peak_area", "peak_FWHM", "peak_assignment", "solvent_flag"))
_NMR_LIQUID_C = AnalysisResultTemplate("nmr.liquid_c", (_NMR_COMMON[4], _NMR_COMMON[5]), _NMR_COMMON, ("peak_ppm", "peak_area", "peak_FWHM", "peak_assignment", "solvent_flag"))
_NMR_SOLID_H = AnalysisResultTemplate("nmr.solid_h", (_NMR_COMMON[4], _NMR_COMMON[5]), _NMR_COMMON, ("peak_ppm", "peak_area", "peak_FWHM", "peak_assignment", "phase_assignment"))
_NMR_SOLID_C = AnalysisResultTemplate("nmr.solid_c", (_NMR_COMMON[4], _NMR_COMMON[5], _f("Xc_pct", "XC", "%", 2, "hero")), _NMR_COMMON + (_XC, _f("phase_composition", "PHASE_COMPOSITION"), _f("assignment_coverage", "ASSIGNMENT_COVERAGE", "%", 2, "primary")), ("peak_ppm", "peak_area", "peak_FWHM", "peak_assignment", "phase_assignment"))

_TEMPLATES = {
    template.key: template
    for template in (
        _DSC_STANDARD, _DSC_ISOTHERMAL, _DSC_NONISOTHERMAL,
        _IR_STANDARD, _IR_MAPPING, _IR_2D,
        _WAXS_STATIC, _WAXS_TEMPERATURE, _WAXS_STRAIN,
        _NMR_LIQUID_H, _NMR_LIQUID_C, _NMR_SOLID_H, _NMR_SOLID_C,
    )
}


def analysis_template(technique: str, submodule: str = "") -> AnalysisResultTemplate | None:
    tech = str(technique or "").strip().lower()
    normalized = str(submodule or "").strip().lower()
    if normalized and not normalized.startswith(f"{tech}."):
        normalized = f"{tech}.{normalized}"
    if not normalized:
        normalized = {"dsc": "dsc.standard", "ir": "ir.standard", "waxs": "waxs.static", "nmr": "nmr.solid_h"}.get(tech, "")
    template = _TEMPLATES.get(normalized)
    if template is not None:
        return template
    fallback = {"dsc": _DSC_STANDARD, "ir": _IR_STANDARD, "waxs": _WAXS_STATIC, "nmr": _NMR_SOLID_H}
    return fallback.get(tech)
