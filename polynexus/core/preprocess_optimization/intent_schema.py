from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

from .contracts import PreprocessIntent, SCHEMA_VERSION


INTENT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version",
        "analysis_id",
        "technique",
        "target",
        "direction",
        "desired_effect",
        "protected_features",
        "target_symptoms",
        "rationale_code",
        "human_summary",
    ],
    "properties": {
        "schema_version": {"const": SCHEMA_VERSION},
        "analysis_id": {"type": "string", "minLength": 1},
        "technique": {"enum": ["DSC", "IR", "WAXS", "SAXS", "NMR"]},
        "target": {"enum": ["baseline", "smoothing", "both"]},
        "direction": {"enum": ["weaken", "strengthen", "change_method"]},
        "desired_effect": {"enum": ["light", "medium", "strong"]},
        "protected_features": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "uniqueItems": True,
        },
        "target_symptoms": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "uniqueItems": True,
        },
        "rationale_code": {"type": "string"},
        "human_summary": {"type": "string"},
    },
}

INTENT_VALIDATOR = Draft202012Validator(INTENT_SCHEMA)


class ContractValidationError(ValueError):
    """Raised when an AI preprocessing contract fails strict validation."""


def parse_preprocess_intent(payload: object) -> PreprocessIntent:
    if not isinstance(payload, dict):
        raise ContractValidationError("PreprocessIntent must be an object")

    errors = sorted(
        INTENT_VALIDATOR.iter_errors(payload),
        key=lambda item: (list(item.absolute_path), item.message),
    )
    if errors:
        raise ContractValidationError("; ".join(error.message for error in errors))

    return PreprocessIntent(
        schema_version=str(payload["schema_version"]),
        analysis_id=str(payload["analysis_id"]),
        technique=str(payload["technique"]),
        target=str(payload["target"]),
        direction=str(payload["direction"]),
        desired_effect=str(payload["desired_effect"]),
        protected_features=tuple(str(item) for item in payload["protected_features"]),
        target_symptoms=tuple(str(item) for item in payload["target_symptoms"]),
        rationale_code=str(payload["rationale_code"]),
        human_summary=str(payload["human_summary"]),
    )
