from __future__ import annotations

from typing import Any

from .analysis_evidence_action_hint_rules import ACTION_HINT_MAPPING


def symptom_action_hints(
    technique: str,
    residual_type: str,
    output_parameters: dict[str, Any] | None = None,
) -> list[str]:
    technique_key = str(technique or "").upper()
    residual_key = str(residual_type or "").strip().lower()
    output = dict(output_parameters or {})

    spec = ACTION_HINT_MAPPING.get(technique_key, {}).get(residual_key)
    if not spec:
        return []

    actions, evidence = spec
    hints = [f"{residual_key} -> {' / '.join(actions)}"]
    hints.extend(f"expected evidence change: {item}" for item in evidence)

    quality_flag = str(output.get("quality_flag", "") or "").strip()
    validation_summary = str(output.get("validation_summary", "") or "").strip()
    if quality_flag:
        hints.append(f"current quality_flag: {quality_flag}")
    if validation_summary and validation_summary != "All checks passed":
        hints.append(f"current validation_summary: {validation_summary}")

    return hints
