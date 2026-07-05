from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Range = tuple[float, float]
RangeList = list[Range]


@dataclass(frozen=True)
class GroundTruth:
    Xc_pct: Range | None = field(default=None)
    peak_centers: RangeList | None = None
    D_Scherrer_nm: Range | None = None
    crystal_form: str | None = None
    Tm_peak_C: Range | None = None
    Tcc_peak_C: Range | None = None
    DHm_Jg: Range | None = None
    Tg_C: Range | None = None
    Tc_peak_C: Range | None = None
    L_nm: Range | None = None
    lc_nm: Range | None = None
    phi_c: Range | None = None
    Rg_nm: Range | None = None
    peak_wavenumbers: RangeList | None = None
    peak_shifts: RangeList | None = None
    temperature_range_C: Range | None = None


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    technique: str
    submodule: str
    data_file: str
    polymer_name: str
    polymer_phase: str | None
    config_overrides: dict[str, Any]
    ground_truth: GroundTruth
    source: str
    notes: str


@dataclass(frozen=True)
class EvalResult:
    case_id: str
    technique: str
    phys_score: float
    peak_score: float
    cross_score: float | None
    human_score: float | None
    composite: float
    details: dict[str, Any]
    parameters_used: dict[str, Any]
    output_parameters: dict[str, Any]


@dataclass(frozen=True)
class BenchmarkSummary:
    total_cases: int
    status_counts: dict[str, int]
    average_composite: float
    average_phys: float
    average_peak: float
    average_cross: float | None
    average_human: float | None
    reasons: dict[str, int]
    average_objective_delta: float | None = None
    objective_gain_cases: int = 0
    objective_loss_cases: int = 0
    acceptance_rate: float = 0.0
    rejection_rate: float = 0.0
    objective_gain_rate: float = 0.0
    rollback_reasons: dict[str, int] = field(default_factory=dict)
    constraint_hit_counts: dict[str, int] = field(default_factory=dict)
    constraint_hit_rate: float = 0.0
    symptom_hit_counts: dict[str, int] = field(default_factory=dict)
    symptom_fix_rate: float = 0.0


@dataclass(frozen=True)
class ParamSpec:
    name: str
    current_value: Any
    value_range: Range | tuple[Any, ...] | list[Any] | None
    description: str
    risk: str
    conflicts_with: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
