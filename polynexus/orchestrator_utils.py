from __future__ import annotations

import json
import logging
import math
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from polynexus.config_bridge import DSC_PARAM_MAP, IR_PARAM_MAP, NMR_PARAM_MAP, SAXS_PARAM_MAP, WAXS_PARAM_MAP
from polynexus.core.ir_engine.names import normalize_ir_polymer_name

logger = logging.getLogger(__name__)


def _resolve_data_file(self: Any, data_file: str) -> Path:
    path = Path(data_file)
    if path.is_absolute():
        return path
    direct = (self.project_root / path).resolve()
    if direct.exists():
        return direct
    return (self.project_root / "测试数据" / path).resolve()


def _config_snapshot(self: Any, engine: Any) -> dict[str, Any]:
    config = self._engine_config(engine)
    return self._config_to_dict(config)


def _config_to_dict(self: Any, config: Any) -> dict[str, Any]:
    if config is None:
        return {}
    if hasattr(config, "to_dict"):
        return self._to_plain_value(config.to_dict())
    if is_dataclass(config):
        return self._to_plain_value(asdict(config))
    return {}


def _ir_reference_bands(self: Any, engine: Any) -> dict[str, Any]:
    if self.technique != "ir":
        return {}
    config = self._engine_config(engine)
    polymer_db = getattr(config, "polymer_peaks_db", {}) if config is not None else {}
    if not isinstance(polymer_db, dict):
        return {}

    polymer_key = normalize_ir_polymer_name(
        self.polymer_name or getattr(config, "polymer_name", "")
    )
    if not polymer_key:
        return {}

    bands = polymer_db.get(polymer_key, [])
    if not isinstance(bands, list) or not bands:
        return {}

    normalized: list[dict[str, Any]] = []
    for band in bands:
        if not isinstance(band, (list, tuple)) or not band:
            continue
        wavenumber = self._safe_float(band[0])
        if wavenumber is None:
            continue
        item = {
            "wavenumber": wavenumber,
            "assignment": str(band[1] if len(band) > 1 else "").strip() or None,
            "intensity": str(band[2] if len(band) > 2 else "").strip() or None,
            "crystallinity_sensitive": bool(band[3]) if len(band) > 3 else False,
        }
        normalized.append(
            {key: value for key, value in item.items() if value not in (None, "")}
        )

    if not normalized:
        return {}

    return self._to_plain_value(
        {
            "polymer_name": polymer_key,
            "band_count": len(normalized),
            "bands": normalized,
            "source": "IRConfig.polymer_peaks_db",
        }
    )


def _tunable_params(
    self: Any,
    config: dict[str, Any],
    allowed_actions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if self.technique == "dsc":
        param_map = DSC_PARAM_MAP
    elif self.technique == "saxs":
        param_map = SAXS_PARAM_MAP
    elif self.technique == "ir":
        param_map = IR_PARAM_MAP
    elif self.technique == "nmr":
        param_map = NMR_PARAM_MAP
    else:
        param_map = WAXS_PARAM_MAP
    goal_focus = self._goal_tuning_focus()
    joint_focus = self._joint_tuning_focus()
    allowed_by_param: dict[str, list[str]] = {}
    for action in allowed_actions or []:
        if not isinstance(action, dict):
            continue
        action_name = str(action.get("name", "") or "").strip()
        for param_name in action.get("allowed_params", []):
            key = str(param_name or "").strip()
            if not key:
                continue
            bucket = allowed_by_param.setdefault(key, [])
            if action_name and action_name not in bucket:
                bucket.append(action_name)
    params = []
    for order, (name, rule) in enumerate(param_map.items()):
        goal = goal_focus.get(name, {})
        focus = joint_focus.get(name, {})
        goal_priority = int(goal.get("priority", 0) or 0)
        joint_priority = int(focus.get("priority", 0) or 0)
        params.append(
            {
                "_order": order,
                "name": name,
                "config_field": rule.field_name,
                "current_value": config.get(rule.field_name),
                "constraint": list(rule.constraint) if rule.constraint is not None else [],
                "type": rule.value_type.__name__,
                "goal_priority": goal_priority,
                "goal_priority_reason": " | ".join(goal.get("reasons", [])),
                "goal_priority_goals": list(goal.get("goals", [])),
                "joint_priority": joint_priority,
                "joint_priority_reason": " | ".join(focus.get("reasons", [])),
                "joint_priority_families": list(focus.get("families", [])),
                "allowed_actions": list(allowed_by_param.get(name, [])),
                "action_guarded": bool(allowed_by_param.get(name)),
            }
        )
    params.sort(
        key=lambda item: (
            -int(item.get("joint_priority", 0) or 0),
            -int(item.get("goal_priority", 0) or 0),
            int(item.get("_order", 0) or 0),
        )
    )
    for item in params:
        item.pop("_order", None)
    return params


def _goal_tuning_focus(self: Any) -> dict[str, dict[str, Any]]:
    from polynexus.orchestrator import GOAL_TUNING_PRIORITY_RULES

    workspace_context = self.workspace_context if isinstance(self.workspace_context, dict) else {}
    goal_key = str(workspace_context.get("tuning_goal") or "").strip().lower()
    if goal_key not in {"symptom", "risk", "joint", "stability"}:
        goal_key = "symptom"
    technique_rules = GOAL_TUNING_PRIORITY_RULES.get(self.technique.upper(), {})
    goal_rules = technique_rules.get(goal_key, [])
    focus: dict[str, dict[str, Any]] = {}
    for rank, item in enumerate(goal_rules):
        if not isinstance(item, tuple) or len(item) != 2:
            continue
        param_name, reason = item
        param_name = str(param_name or "").strip()
        reason = str(reason or "").strip()
        if not param_name:
            continue
        entry = focus.setdefault(param_name, {"priority": 0, "reasons": [], "goals": []})
        entry["priority"] += max(1, 4 - rank)
        if reason and reason not in entry["reasons"]:
            entry["reasons"].append(reason)
        if goal_key and goal_key not in entry["goals"]:
            entry["goals"].append(goal_key)
    return focus


def _joint_tuning_focus(self: Any) -> dict[str, dict[str, Any]]:
    from polynexus.orchestrator import JOINT_TUNING_PRIORITY_RULES

    joint_ai_context = self._joint_ai_context()
    issue_families = joint_ai_context.get("issue_families")
    if not isinstance(issue_families, list) or not issue_families:
        return {}

    technique_rules = JOINT_TUNING_PRIORITY_RULES.get(self.technique.upper(), {})
    focus: dict[str, dict[str, Any]] = {}
    for family in issue_families:
        family_label = str(family or "").strip()
        family_key = family_label.lower()
        if not family_key:
            continue
        for rank, item in enumerate(technique_rules.get(family_key, [])):
            if not isinstance(item, tuple) or len(item) != 2:
                continue
            param_name, reason = item
            param_name = str(param_name or "").strip()
            reason = str(reason or "").strip()
            if not param_name:
                continue
            entry = focus.setdefault(
                param_name,
                {"priority": 0, "reasons": [], "families": []},
            )
            entry["priority"] += max(1, 4 - rank)
            if reason and reason not in entry["reasons"]:
                entry["reasons"].append(reason)
            if family_label and family_label not in entry["families"]:
                entry["families"].append(family_label)
    return focus


def _engine_config(self: Any, engine: Any) -> Any:
    if self.technique == "dsc":
        return getattr(engine, "_dsc_config", None)
    if self.technique == "saxs":
        return getattr(engine, "cfg", None)
    if self.technique == "ir":
        return getattr(engine, "_ir_config", None)
    if self.technique == "nmr":
        return getattr(engine, "_cfg", None)
    return getattr(engine, "_waxs_config", None)


def _canonical_submodule_id(self: Any, submodule: str) -> str:
    if self.technique == "waxs":
        mapping = {
            "waxs.in_situ_temp": "waxs.temperature",
            "waxs.in_situ_stretch": "waxs.strain",
            "waxs.static": "waxs.static",
        }
        return mapping.get(submodule, submodule)
    return submodule


def _waxs_submodule_id(self: Any) -> str:
    text = self.data_file.replace("\\", "/")
    if "原位变温广角" in text:
        return "waxs.temperature"
    if "原位拉伸广角" in text:
        return "waxs.strain"
    return "waxs.static"


def _nmr_submodule_id(self: Any) -> str:
    text = self.data_file.lower().replace("\\", "/")
    if "液体" in text or "liquid" in text:
        return "nmr.liquid_h" if ("h谱" in text or "proton" in text) else "nmr.liquid_c"
    if "固体" in text or "solid" in text:
        return (
            "nmr.solid_h"
            if ("氢谱" in text or "single_pulse" in text or "_h_" in text)
            else "nmr.solid_c"
        )
    if "proton" in text or "_h_" in text or "-h_" in text:
        return "nmr.liquid_h"
    if "carbon" in text or "13c" in text or "_c_" in text or "-c_" in text:
        return "nmr.liquid_c"
    return "nmr.solid_c"


def _flatten_dsc_parameters(self: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    preserved_keys = (
        "quality_flag",
        "quality_flags",
        "validation_summary",
        "validation_warnings",
    )
    preserved = {key: payload[key] for key in preserved_keys if key in payload}
    if any(key in payload for key in ("Tm_peak_C", "Tc_peak_C", "Xc_pct")):
        if preserved:
            flat = dict(payload)
            flat.update(preserved)
            return flat
        return payload
    for value in payload.values():
        if isinstance(value, dict) and any(
            key in value for key in ("Tm_peak_C", "Tc_peak_C", "Xc_pct")
        ):
            flat = dict(value)
            flat.update(preserved)
            return flat
    if preserved:
        merged = dict(payload)
        merged.update(preserved)
        return merged
    return payload


def _flatten_ir_parameters(self: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    if any(key in payload for key in ("n_peaks", "polymer_score", "r_squared")):
        return payload
    for value in payload.values():
        if isinstance(value, dict) and any(
            key in value for key in ("n_peaks", "polymer_score", "r_squared")
        ):
            return dict(value)
    return payload


def _flatten_nmr_parameters(self: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    if any(key in payload for key in ("n_peaks", "dominant_peak_ppm", "r_squared")):
        return payload
    for value in payload.values():
        if isinstance(value, dict) and any(
            key in value for key in ("n_peaks", "dominant_peak_ppm", "r_squared")
        ):
            return dict(value)
    return payload


def _is_nan(self: Any, value: Any) -> bool:
    try:
        return bool(value != value)
    except Exception:
        logger.warning("Orchestrator NaN check failed.", exc_info=True)
        return False


def _safe_float(self: Any, value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _to_plain_value(self: Any, value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): self._to_plain_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [self._to_plain_value(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value


def _stable_signature(self: Any, value: Any) -> str:
    try:
        return json.dumps(
            self._to_plain_value(value),
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
    except Exception:
        return repr(self._to_plain_value(value))
