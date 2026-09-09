"""CLI adapter for comparing persisted public validation projections."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from polynexus.core.validation_harness import ValidationCase, run_validation


def run_validation_cli(args: Any) -> int:
    """Compare two public result projections through the shared validator.

    This command intentionally compares persisted projections instead of
    importing arbitrary Python code.  Codex/Agent adapters that own a
    calculator should call ``run_validation`` directly; the CLI remains a safe
    machine-readable boundary for replay outputs.
    """

    try:
        case = ValidationCase.from_dict(_read_json(args.case, "validation case"))
        first = _read_json(args.first_output, "first validation output")
        second = _read_json(args.second_output, "second validation output")
        outputs = [first, second]

        def calculator(_payload: Any) -> Any:
            return outputs.pop(0)

        raw_values = [getattr(args, "raw_hash_before", None), getattr(args, "raw_hash_after", None)]
        raw_provider = None
        if any(value not in (None, "") for value in raw_values):
            raw_provider_values = [value for value in raw_values if value not in (None, "")]
            if len(raw_provider_values) == 1:
                raw_provider_values.append(raw_provider_values[0])
            raw_provider = iter(raw_provider_values)

            def read_raw_hash() -> str:
                return next(raw_provider)

        report = run_validation(case, calculator, raw_hash_provider=read_raw_hash if raw_provider else None)
        payload = report.to_dict()
    except (OSError, TypeError, ValueError, json.JSONDecodeError, StopIteration) as exc:
        payload = {
            "status": "failed",
            "reason_codes": ["validation_cli_input_invalid"],
            "error": str(exc),
        }
        return _emit(payload, args, 2)

    return _emit(payload, args, 0 if report.status == "passed" else 2)


def _read_json(path_value: object, label: str) -> dict[str, Any]:
    if path_value in (None, ""):
        raise ValueError(f"{label} path is required")
    path = Path(str(path_value))
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _emit(payload: dict[str, Any], args: Any, exit_code: int) -> int:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return exit_code


__all__ = ["run_validation_cli"]
