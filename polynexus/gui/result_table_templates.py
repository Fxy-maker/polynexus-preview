"""Explicit field templates for structured result tables."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResultFieldSpec:
    """Describe one result field and the source keys that can supply it."""

    key: str
    label_key: str
    unit: str = ""
    digits: int | None = None
    aliases: tuple[str, ...] = ()
    provenance_key: str = ""
    status_key: str = ""

    @property
    def source_keys(self) -> tuple[str, ...]:
        return (self.key, *self.aliases)


@dataclass(frozen=True)
class ResultTableTemplate:
    """Describe the hero and primary fields for one result-table mode."""

    key: str
    hero_fields: tuple[ResultFieldSpec, ...]
    primary_fields: tuple[ResultFieldSpec, ...]


_FILE = ResultFieldSpec("file", "TABLE_FIELD_FILE")
_L = ResultFieldSpec("L_nm", "TABLE_FIELD_LONG_PERIOD", "nm", 2)
_LC = ResultFieldSpec(
    "lc_nm",
    "TABLE_FIELD_EFFECTIVE_LC",
    "nm",
    2,
    aliases=("lc_nm_calibrated", "lc_nm_raw"),
    provenance_key="lc_method",
    status_key="lc_reliability_status",
)
_LA = ResultFieldSpec("la_nm", "TABLE_FIELD_AMORPHOUS_LAYER", "nm", 2)
_PHI_C = ResultFieldSpec(
    "phi_c",
    "TABLE_FIELD_CRYSTAL_FRACTION",
    digits=3,
    aliases=("Xc",),
)

_SAXS_STATIC = ResultTableTemplate(
    key="saxs.static",
    hero_fields=(_L, _LC, _LA, _PHI_C),
    primary_fields=(
        _FILE,
        _L,
        _LC,
        _LA,
        _PHI_C,
        ResultFieldSpec("lc_method", "TABLE_FIELD_VALUE_SOURCE"),
        ResultFieldSpec("lc_reliability_status", "TABLE_FIELD_RELIABILITY"),
    ),
)

_SAXS_TEMPERATURE = ResultTableTemplate(
    key="saxs.temperature",
    hero_fields=(
        _L,
        _LC,
        ResultFieldSpec("Tm_peak_C", "TABLE_FIELD_TM_PEAK", "°C", 1),
        ResultFieldSpec("condition_confidence", "TABLE_FIELD_SEQUENCE_CONFIDENCE", digits=2),
    ),
    primary_fields=(
        ResultFieldSpec(
            "temperature_C",
            "TABLE_FIELD_TEMPERATURE",
            "°C",
            1,
            aliases=("condition_value",),
        ),
        ResultFieldSpec("stage", "TABLE_FIELD_STAGE"),
        _L,
        _LC,
        ResultFieldSpec("lc_method", "TABLE_FIELD_VALUE_SOURCE"),
        ResultFieldSpec("melting_window_status", "TABLE_FIELD_MELTING_WINDOW"),
        ResultFieldSpec("lc_reliability_status", "TABLE_FIELD_RELIABILITY"),
    ),
)

_SAXS_STRAIN = ResultTableTemplate(
    key="saxs.strain",
    hero_fields=(
        ResultFieldSpec("Q_star_rel_mean", "TABLE_FIELD_Q_STAR_REL", digits=4),
        ResultFieldSpec("phi_void_mean", "TABLE_FIELD_VOID_FRACTION", digits=4),
        ResultFieldSpec(
            "f_Herman_mean",
            "TABLE_FIELD_HERMAN",
            digits=4,
            aliases=("f_Herman",),
        ),
        ResultFieldSpec(
            "f_Herman_raw_mean",
            "TABLE_FIELD_HERMAN_DIAGNOSTIC",
            digits=4,
            aliases=("f_Herman_raw",),
        ),
        ResultFieldSpec("phase_support_mean", "TABLE_FIELD_PHASE_SUPPORT", digits=3),
    ),
    primary_fields=(
        ResultFieldSpec(
            "strain_pct",
            "TABLE_FIELD_STRAIN",
            "%",
            1,
            aliases=("condition_value",),
        ),
        ResultFieldSpec(
            "Q_star_rel",
            "TABLE_FIELD_Q_STAR_REL",
            digits=4,
            aliases=("Q_rel",),
        ),
        ResultFieldSpec("phi_void", "TABLE_FIELD_VOID_FRACTION", digits=4),
        ResultFieldSpec("f_Herman", "TABLE_FIELD_HERMAN", digits=4),
        ResultFieldSpec(
            "f_Herman_raw",
            "TABLE_FIELD_HERMAN_DIAGNOSTIC",
            digits=4,
        ),
        ResultFieldSpec("delta_f_from_zero", "TABLE_FIELD_HERMAN_DELTA", digits=4),
        ResultFieldSpec(
            "delta_f_stability_lower",
            "TABLE_FIELD_HERMAN_STABILITY_LOWER",
            digits=4,
        ),
        ResultFieldSpec(
            "delta_f_stability_upper",
            "TABLE_FIELD_HERMAN_STABILITY_UPPER",
            digits=4,
        ),
        ResultFieldSpec("orientation_q_min_nm1", "TABLE_FIELD_ORIENTATION_Q_MIN", "nm^-1", 4),
        ResultFieldSpec("orientation_q_max_nm1", "TABLE_FIELD_ORIENTATION_Q_MAX", "nm^-1", 4),
        ResultFieldSpec("orientation_track_id", "TABLE_FIELD_ORIENTATION_TRACK"),
        ResultFieldSpec("orientation_reliability_status", "TABLE_FIELD_ORIENTATION_RELIABILITY"),
        ResultFieldSpec("orientation_reason_summary", "TABLE_FIELD_ORIENTATION_REASONS"),
        ResultFieldSpec(
            "phase_name",
            "TABLE_FIELD_STRUCTURE_STAGE",
            aliases=("strain_phase",),
        ),
        ResultFieldSpec("phase_support_score", "TABLE_FIELD_PHASE_SUPPORT", digits=3),
        ResultFieldSpec("strain_reliability_status", "TABLE_FIELD_RELIABILITY"),
    ),
)

_SAXS_TEMPLATES = {
    "static": _SAXS_STATIC,
    "saxs.static": _SAXS_STATIC,
    "temperature": _SAXS_TEMPERATURE,
    "saxs.temperature": _SAXS_TEMPERATURE,
    "strain": _SAXS_STRAIN,
    "saxs.strain": _SAXS_STRAIN,
}


def saxs_template(submodule: str | None) -> ResultTableTemplate:
    """Return the explicit SAXS template for *submodule*, defaulting to static."""
    normalized = str(submodule or "").strip().lower()
    return _SAXS_TEMPLATES.get(normalized, _SAXS_STATIC)
