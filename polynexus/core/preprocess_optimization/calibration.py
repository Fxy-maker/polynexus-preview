from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from polynexus import __version__

from .contracts import SCHEMA_VERSION
from .policy import PreprocessPolicy


GENERATOR_VERSION = "1"
CORE_MAJOR_VERSION = str(__version__).split(".", 1)[0]
_SAXS_CASE_MODES = {"static", "temperature", "strain"}
_SAXS_CASE_REQUIRED_FIELDS = {
    "case_schema_version",
    "case_id",
    "mode",
    "source_ref",
    "original_config_hash",
    "effective_config_hash",
    "expert_accept",
    "expert_reason",
}


class PolicyConfigError(ValueError):
    """Raised when a configured automation profile lacks valid calibration."""


@dataclass(frozen=True)
class CalibrationReport:
    schema_version: str
    technique: str
    policy_version: str
    generator_version: str
    core_major_version: str
    case_count: int
    mean_evidence_coverage: float
    hard_guard_false_accept_count: int
    expert_agreement: float
    confidence_distribution: dict[str, int]
    artificial_accept_count: int
    artificial_reject_count: int
    false_reject_count: int
    metric_drift_percentiles: dict[str, dict[str, float]]
    blockers: tuple[str, ...]
    promotion_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blockers"] = list(self.blockers)
        return payload


def _percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(item) for item in values)
    position = (len(ordered) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def _saxs_case_contract_invalid(case: Mapping[str, Any]) -> bool:
    if not _SAXS_CASE_REQUIRED_FIELDS.issubset(case):
        return True
    if str(case.get("case_schema_version", "")) != SCHEMA_VERSION:
        return True
    if str(case.get("mode", "") or "").strip().lower() not in _SAXS_CASE_MODES:
        return True
    if not isinstance(case.get("expert_accept"), bool):
        return True
    return not bool(str(case.get("expert_reason", "") or "").strip())


def calibrate_cases(
    cases: Sequence[Mapping[str, Any]],
    *,
    policy: PreprocessPolicy,
) -> CalibrationReport:
    rows = [dict(item) for item in cases if isinstance(item, Mapping)]
    coverages = [float(item.get("evidence_coverage", 0.0) or 0.0) for item in rows]
    false_accepts = sum(
        bool(item.get("selected")) and bool(item.get("hard_guard_violation"))
        for item in rows
    )
    agreements = sum(
        bool(item.get("selected")) == bool(item.get("expert_accept")) for item in rows
    )
    confidence_distribution = {"high": 0, "medium": 0, "low": 0}
    drift_values: dict[str, list[float]] = {}
    for item in rows:
        band = str(item.get("confidence_band", "low") or "low")
        if band in confidence_distribution:
            confidence_distribution[band] += 1
        drifts = item.get("metric_drifts", {})
        if isinstance(drifts, Mapping):
            for name, value in drifts.items():
                try:
                    drift_values.setdefault(str(name), []).append(float(value))
                except (TypeError, ValueError):
                    continue
    case_count = len(rows)
    mean_coverage = sum(coverages) / case_count if case_count else 0.0
    expert_agreement = agreements / case_count if case_count else 0.0
    false_rejects = sum(
        not bool(item.get("selected")) and bool(item.get("expert_accept"))
        for item in rows
    )
    blockers: list[str] = []
    if not rows:
        blockers.append("no_calibration_cases")
    if false_accepts:
        blockers.append("hard_guard_false_accept")
    if mean_coverage < 0.90:
        blockers.append("insufficient_evidence_coverage")
    if expert_agreement < 0.90:
        blockers.append("insufficient_expert_agreement")
    if policy.technique.upper() == "SAXS" and any(
        _saxs_case_contract_invalid(item) for item in rows
    ):
        blockers.append("invalid_case_contract")
    percentiles = {
        name: {
            "p50": _percentile(values, 0.50),
            "p95": _percentile(values, 0.95),
        }
        for name, values in sorted(drift_values.items())
    }
    return CalibrationReport(
        schema_version=SCHEMA_VERSION,
        technique=policy.technique,
        policy_version=policy.policy_version,
        generator_version=GENERATOR_VERSION,
        core_major_version=CORE_MAJOR_VERSION,
        case_count=case_count,
        mean_evidence_coverage=mean_coverage,
        hard_guard_false_accept_count=false_accepts,
        expert_agreement=expert_agreement,
        confidence_distribution=confidence_distribution,
        artificial_accept_count=sum(bool(item.get("selected")) for item in rows),
        artificial_reject_count=sum(not bool(item.get("selected")) for item in rows),
        false_reject_count=false_rejects,
        metric_drift_percentiles=percentiles,
        blockers=tuple(blockers),
        promotion_allowed=not blockers,
    )


def write_calibration_report(path: str | Path, report: CalibrationReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def report_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_report(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyConfigError(f"invalid calibration report: {exc}") from exc
    if not isinstance(payload, dict):
        raise PolicyConfigError("calibration report must be an object")
    return payload


def load_policy_config(
    path: str | Path,
    *,
    base_policies: Mapping[str, PreprocessPolicy],
) -> dict[str, PreprocessPolicy]:
    config_path = Path(path)
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyConfigError(f"invalid policy config: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise PolicyConfigError("policy config schema_version mismatch")
    if str(payload.get("generator_version", "")) != GENERATOR_VERSION:
        raise PolicyConfigError("policy config generator_version mismatch")
    if str(payload.get("core_major_version", "")) != CORE_MAJOR_VERSION:
        raise PolicyConfigError("policy config core_major_version mismatch")
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        raise PolicyConfigError("policy config profiles must be an object")

    loaded: dict[str, PreprocessPolicy] = {}
    for technique, profile in profiles.items():
        key = str(technique).upper()
        if key not in base_policies or not isinstance(profile, dict):
            raise PolicyConfigError(f"unknown policy technique: {technique}")
        base = base_policies[key]
        if str(profile.get("policy_version", "")) != base.policy_version:
            raise PolicyConfigError(f"{key} policy_version mismatch")
        state = str(profile.get("automation_state", "shadow") or "shadow")
        calibrated = bool(profile.get("calibrated", False))
        if state != "shadow":
            report_name = str(profile.get("calibration_report", "") or "").strip()
            expected_hash = str(
                profile.get("calibration_report_sha256", "") or ""
            ).strip()
            if not calibrated or not report_name or not expected_hash:
                raise PolicyConfigError(f"{key} calibration report is required")
            report_path = (config_path.parent / report_name).resolve()
            if not report_path.is_file():
                raise PolicyConfigError(f"{key} calibration report not found")
            if report_sha256(report_path) != expected_hash:
                raise PolicyConfigError(f"{key} calibration report hash mismatch")
            report = _load_report(report_path)
            checks = {
                "technique": key,
                "schema_version": SCHEMA_VERSION,
                "policy_version": base.policy_version,
                "generator_version": GENERATOR_VERSION,
                "core_major_version": CORE_MAJOR_VERSION,
            }
            for field, expected in checks.items():
                if str(report.get(field, "")) != expected:
                    raise PolicyConfigError(
                        f"{key} calibration report {field} mismatch"
                    )
            if report.get("promotion_allowed") is not True:
                raise PolicyConfigError(f"{key} calibration report blocks promotion")
        elif calibrated:
            raise PolicyConfigError(f"{key} shadow profile cannot claim calibrated")
        loaded[key] = replace(
            base,
            automation_state=state,
            calibrated=calibrated,
        )
    return loaded
