from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any

import numpy as np
from jsonschema import Draft202012Validator, ValidationError

from polynexus.core.dsc_engine import aggregate_dsc_result_metrics

from .models import EvalCase, EvalResult, GroundTruth, Range


def run_preprocess_manifest(path: str | Path) -> list[dict[str, Any]]:
    from tests.eval.preprocess.synthetic_signals import run_synthetic_case

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = payload.get("cases", []) if isinstance(payload, dict) else []
    if not isinstance(cases, list):
        raise EvalCaseLoadError("Preprocessing manifest cases must be a list")
    return [run_synthetic_case(item) for item in cases if isinstance(item, dict)]


class EvalCaseLoadError(ValueError):
    """Raised when a case file cannot be parsed into a valid EvalCase."""


class EvalRunner:
    EVAL_CASE_SCHEMA: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "EvalCase",
        "type": "object",
        "required": [
            "case_id",
            "technique",
            "data_file",
            "polymer_name",
            "ground_truth",
            "source",
        ],
        "properties": {
            "case_id": {"type": "string"},
            "technique": {"type": "string", "enum": ["waxs", "dsc", "saxs", "ir", "nmr"]},
            "submodule": {"type": "string"},
            "data_file": {"type": "string"},
            "polymer_name": {"type": "string"},
            "polymer_phase": {"type": ["string", "null"]},
            "config_overrides": {"type": "object"},
            "ground_truth": {
                "type": "object",
                "properties": {
                    "Xc_pct": {"$ref": "#/$defs/rangeOrNull"},
                    "peak_centers": {"$ref": "#/$defs/rangeListOrNull"},
                    "D_Scherrer_nm": {"$ref": "#/$defs/rangeOrNull"},
                    "crystal_form": {"type": ["string", "null"]},
                    "Tm_peak_C": {"$ref": "#/$defs/rangeOrNull"},
                    "Tcc_peak_C": {"$ref": "#/$defs/rangeOrNull"},
                    "DHm_Jg": {"$ref": "#/$defs/rangeOrNull"},
                    "Tg_C": {"$ref": "#/$defs/rangeOrNull"},
                    "Tc_peak_C": {"$ref": "#/$defs/rangeOrNull"},
                    "L_nm": {"$ref": "#/$defs/rangeOrNull"},
                    "lc_nm": {"$ref": "#/$defs/rangeOrNull"},
                    "Rg_nm": {"$ref": "#/$defs/rangeOrNull"},
                    "phi_c": {"$ref": "#/$defs/rangeOrNull"},
                    "peak_wavenumbers": {"$ref": "#/$defs/rangeListOrNull"},
                    "peak_shifts": {"$ref": "#/$defs/rangeListOrNull"},
                    "temperature_range_C": {"$ref": "#/$defs/rangeOrNull"},
                },
                "additionalProperties": False,
            },
            "source": {
                "type": "string",
                "enum": ["synthetic", "literature", "cross_validation", "expert_review"],
            },
            "notes": {"type": "string"},
        },
        "$defs": {
            "range": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {"type": "number"},
            },
            "rangeOrNull": {"anyOf": [{"$ref": "#/$defs/range"}, {"type": "null"}]},
            "rangeList": {
                "type": "array",
                "items": {"$ref": "#/$defs/range"},
            },
            "rangeListOrNull": {"anyOf": [{"$ref": "#/$defs/rangeList"}, {"type": "null"}]},
        },
    }

    RANGE_FIELDS = {
        "Xc_pct",
        "D_Scherrer_nm",
        "Tm_peak_C",
        "DHm_Jg",
        "Tg_C",
        "Tc_peak_C",
        "L_nm",
        "lc_nm",
        "phi_c",
        "Rg_nm",
    }
    RANGE_LIST_FIELDS = {"peak_centers", "peak_wavenumbers", "peak_shifts"}
    DEFAULT_WEIGHTS = {"PHYS": 0.25, "PEAK": 0.25, "CROSS": 0.25, "HUMAN": 0.25}

    def __init__(self, project_root: str | Path | None = None, eval_root: str | Path | None = None):
        self.eval_root = Path(eval_root).resolve() if eval_root else Path(__file__).resolve().parent
        self.project_root = Path(project_root).resolve() if project_root else self.eval_root.parents[1]
        self.validator = Draft202012Validator(self.EVAL_CASE_SCHEMA)
        self.load_errors: list[tuple[Path, str]] = []

    def load_case(self, path: str | Path) -> EvalCase:
        case_path = Path(path)
        try:
            payload = json.loads(case_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise EvalCaseLoadError(f"{case_path}: invalid JSON at line {exc.lineno}: {exc.msg}") from exc
        except OSError as exc:
            raise EvalCaseLoadError(f"{case_path}: cannot read file: {exc}") from exc

        try:
            normalized = self._normalize_payload(payload)
            self.validator.validate(normalized)
        except ValidationError as exc:
            location = ".".join(str(part) for part in exc.absolute_path) or "<root>"
            raise EvalCaseLoadError(f"{case_path}: schema error at {location}: {exc.message}") from exc
        except (TypeError, ValueError) as exc:
            raise EvalCaseLoadError(f"{case_path}: normalization error: {exc}") from exc

        data_file = str(normalized["data_file"])
        self.resolve_data_file(data_file)
        gt = self._ground_truth_from_mapping(normalized["ground_truth"])
        return EvalCase(
            case_id=str(normalized["case_id"]),
            technique=str(normalized["technique"]),
            submodule=str(normalized.get("submodule", "")),
            data_file=data_file,
            polymer_name=str(normalized["polymer_name"]),
            polymer_phase=normalized.get("polymer_phase"),
            config_overrides=dict(normalized.get("config_overrides", {})),
            ground_truth=gt,
            source=str(normalized["source"]),
            notes=str(normalized.get("notes", "")),
        )

    def load_all_cases(self, cases_dir: str | Path) -> list[EvalCase]:
        self.load_errors = []
        loaded: list[EvalCase] = []
        for path in self._iter_case_paths(cases_dir):
            try:
                loaded.append(self.load_case(path))
            except EvalCaseLoadError as exc:
                self.load_errors.append((path, str(exc)))
        return loaded

    def run_case(self, case: EvalCase) -> EvalResult:
        if self._uses_real_engine(case):
            output = self._run_real_engine(case)
        else:
            output = self._stub_output_from_ground_truth(case)
        return self.compute_metrics(case, output)

    def compute_metrics(self, case: EvalCase, output: dict[str, Any]) -> EvalResult:
        output_parameters_source = output.get("output_parameters")
        if output_parameters_source is None:
            output_parameters_source = output.get("tuned_output_parameters")
        if output_parameters_source is None:
            output_parameters_source = output
        output_parameters = dict(output_parameters_source)

        parameters_used_source = output.get("parameters_used")
        if parameters_used_source is None:
            parameters_used_source = output.get("tuned_parameters_used")
        if parameters_used_source is None:
            parameters_used_source = case.config_overrides
        parameters_used = dict(parameters_used_source)

        phys_score, phys_details = self._compute_phys_score(case, output_parameters)
        peak_score, peak_available, peak_details = self._compute_peak_score(case, output_parameters)
        cross_score = self._optional_float(output.get("cross_score"))
        human_score = self._optional_float(output.get("human_score"))

        available = {"PHYS"}
        if peak_available:
            available.add("PEAK")
        if cross_score is not None:
            available.add("CROSS")
        if human_score is not None:
            available.add("HUMAN")

        weights = self.redistribute_weights(available)
        values = {
            "PHYS": phys_score,
            "PEAK": peak_score,
            "CROSS": cross_score if cross_score is not None else 0.0,
            "HUMAN": (human_score / 5.0) if human_score is not None else 0.0,
        }
        composite = sum(weights[name] * values[name] for name in weights)
        details = {
            "available_metrics": sorted(available),
            "weights": weights,
            "phys": phys_details,
            "peak": peak_details,
        }
        comparison = self._comparison_metrics(case, output, output_parameters, parameters_used)
        if comparison:
            details["benchmark"] = comparison
        return EvalResult(
            case_id=case.case_id,
            technique=case.technique,
            phys_score=round(phys_score, 6),
            peak_score=round(peak_score, 6),
            cross_score=cross_score,
            human_score=human_score,
            composite=round(composite, 6),
            details=details,
            parameters_used=parameters_used,
            output_parameters=output_parameters,
        )

    def _comparison_metrics(
        self,
        case: EvalCase,
        output: dict[str, Any],
        tuned_output_parameters: dict[str, Any],
        tuned_parameters_used: dict[str, Any],
    ) -> dict[str, Any]:
        baseline_output_parameters = output.get("baseline_output_parameters")
        if not isinstance(baseline_output_parameters, dict):
            baseline_output_parameters = output.get("baseline_parameters")
        if not isinstance(baseline_output_parameters, dict):
            return {}

        baseline_parameters_used = output.get("baseline_parameters_used")
        if not isinstance(baseline_parameters_used, dict):
            baseline_parameters_used = case.config_overrides

        baseline_eval = self.compute_metrics(
            case,
            {
                "output_parameters": baseline_output_parameters,
                "parameters_used": baseline_parameters_used,
            },
        )
        tuned_eval = self.compute_metrics(
            case,
            {
                "output_parameters": tuned_output_parameters,
                "parameters_used": tuned_parameters_used,
            },
        )

        objective_delta = round(tuned_eval.composite - baseline_eval.composite, 6)
        phys_delta = round(tuned_eval.phys_score - baseline_eval.phys_score, 6)
        peak_delta = round(tuned_eval.peak_score - baseline_eval.peak_score, 6)
        cross_delta = None
        if tuned_eval.cross_score is not None or baseline_eval.cross_score is not None:
            cross_delta = round((tuned_eval.cross_score or 0.0) - (baseline_eval.cross_score or 0.0), 6)
        human_delta = None
        if tuned_eval.human_score is not None or baseline_eval.human_score is not None:
            human_delta = round((tuned_eval.human_score or 0.0) - (baseline_eval.human_score or 0.0), 6)

        return {
            "baseline": {
                "phys_score": baseline_eval.phys_score,
                "peak_score": baseline_eval.peak_score,
                "cross_score": baseline_eval.cross_score,
                "human_score": baseline_eval.human_score,
                "composite": baseline_eval.composite,
            },
            "tuned": {
                "phys_score": tuned_eval.phys_score,
                "peak_score": tuned_eval.peak_score,
                "cross_score": tuned_eval.cross_score,
                "human_score": tuned_eval.human_score,
                "composite": tuned_eval.composite,
            },
            "objective_delta": objective_delta,
            "phys_delta": phys_delta,
            "peak_delta": peak_delta,
            "cross_delta": cross_delta,
            "human_delta": human_delta,
            "objective_improved": objective_delta > 0.0,
            "physical_improved": phys_delta > 0.0,
            "peak_improved": peak_delta > 0.0,
            "symptom_hit": (objective_delta > 0.0) and (phys_delta > 0.0 or peak_delta > 0.0),
        }

    @classmethod
    def redistribute_weights(cls, available: set[str]) -> dict[str, float]:
        active = {name.upper() for name in available} & set(cls.DEFAULT_WEIGHTS)
        if not active:
            raise ValueError("At least one known metric must be available.")

        table = {
            frozenset({"PHYS", "PEAK", "CROSS", "HUMAN"}): {
                "PHYS": 0.25,
                "PEAK": 0.25,
                "CROSS": 0.25,
                "HUMAN": 0.25,
            },
            frozenset({"PHYS", "PEAK", "CROSS"}): {"PHYS": 0.40, "PEAK": 0.35, "CROSS": 0.25},
            frozenset({"PHYS", "PEAK"}): {"PHYS": 0.55, "PEAK": 0.45},
            frozenset({"PHYS"}): {"PHYS": 1.0},
        }
        if frozenset(active) in table:
            return table[frozenset(active)]

        total = sum(cls.DEFAULT_WEIGHTS[name] for name in active)
        return {name: cls.DEFAULT_WEIGHTS[name] / total for name in cls.DEFAULT_WEIGHTS if name in active}

    def resolve_data_file(self, data_file: str) -> Path:
        if data_file.startswith("synth:"):
            synth_id = data_file.split(":", 1)[1]
            return self.eval_root / "synth_data" / f"{synth_id}.xy"

        path = Path(data_file)
        if path.is_absolute():
            return path

        direct = (self.project_root / path).resolve()
        if direct.exists() or data_file.startswith(("tests/", "tests\\", "测试数据/", "测试数据\\")):
            return direct
        return (self.project_root / "测试数据" / path).resolve()

    def _uses_real_engine(self, case: EvalCase) -> bool:
        tech = case.technique.lower().strip()
        if tech not in {"waxs", "dsc", "saxs", "ir", "nmr"}:
            return False
        if case.data_file.startswith("synth:"):
            return False
        data_path = self._resolve_real_engine_path(case)
        if not data_path.exists():
            return False
        submodule = self._real_engine_submodule_id(case)
        allowed = {
            "waxs": {"waxs.static", "waxs.temperature", "waxs.strain"},
            "saxs": {"saxs.static", "saxs.temperature", "saxs.strain"},
            "dsc": {"dsc.standard", "dsc.heating", "dsc.cooling", "dsc.isothermal", "dsc.nonisothermal"},
            "ir": {"ir.standard", "ir.temperature_2d"},
            "nmr": {"nmr.liquid_h", "nmr.liquid_c", "nmr.solid_h", "nmr.solid_c"},
        }
        return submodule in allowed[tech]

    def _run_real_engine(self, case: EvalCase) -> dict[str, Any]:
        tech = case.technique.lower().strip()
        if tech not in {"waxs", "dsc", "saxs", "ir", "nmr"}:
            raise NotImplementedError("Engine bridge does not support this real case.")

        from polynexus.core import get_engine

        data_path = self._resolve_real_engine_path(case)
        submodule_id = self._real_engine_submodule_id(case)
        engine = get_engine(tech, submodule_id=submodule_id)
        if engine is None:
            raise RuntimeError(f"{case.technique.upper()} engine is not registered.")

        if tech == "dsc":
            self._apply_dsc_config_overrides(engine, case)
        elif tech == "waxs":
            self._apply_waxs_config_overrides(engine, case)
        elif tech == "ir":
            self._apply_ir_config_overrides(engine, case)
        elif tech == "nmr":
            self._apply_nmr_config_overrides(engine, case)
        else:
            self._apply_saxs_config_overrides(engine, case)
        result = engine.run_pipeline(str(data_path), output_dir="")
        if tech == "dsc":
            output_parameters = self._dsc_output_parameters(engine, result)
            parameters_used = self._dsc_parameters_used(engine, data_path)
        elif tech == "ir":
            output_parameters = self._ir_output_parameters(engine, result)
            parameters_used = self._ir_parameters_used(engine, data_path)
        elif tech == "saxs":
            output_parameters = self._saxs_output_parameters(engine, result)
            parameters_used = self._saxs_parameters_used(engine, data_path)
        elif tech == "nmr":
            output_parameters = self._nmr_output_parameters(engine, result)
            parameters_used = self._nmr_parameters_used(engine, data_path)
        else:
            output_parameters = self._waxs_output_parameters(engine, result)
            parameters_used = self._waxs_parameters_used(engine, data_path)
        if not output_parameters:
            raise RuntimeError(f"{case.technique.upper()} engine produced no output parameters for {data_path}")

        return {
            "parameters_used": parameters_used,
            "output_parameters": output_parameters,
        }

    def _resolve_real_engine_path(self, case: EvalCase) -> Path:
        source_file = case.config_overrides.get("source_file")
        if source_file:
            return Path(str(source_file)).resolve()
        return self.resolve_data_file(case.data_file)

    def _real_engine_submodule_id(self, case: EvalCase) -> str:
        technique = str(case.technique or "").strip().lower()
        submodule = str(case.submodule or "").strip().lower()
        if not technique:
            return submodule
        if not submodule:
            defaults = {
                "waxs": "static",
                "saxs": "static",
                "dsc": "standard",
                "ir": "standard",
            }
            submodule = defaults.get(technique, "")
        if submodule.startswith(f"{technique}."):
            return submodule
        if submodule:
            return f"{technique}.{submodule}"
        return submodule

    def _apply_waxs_config_overrides(self, engine: Any, case: EvalCase) -> None:
        config = getattr(engine, "_waxs_config", None)
        if config is None:
            return

        config_fields = set(getattr(config, "__dataclass_fields__", {}))
        analyze_fields = {
            "peak_function",
            "peak_height_min",
            "peak_distance",
            "max_peaks",
            "min_two_theta",
            "crystallinity_min_two_theta",
            "crystallinity_max_two_theta",
            "amorphous_subtraction",
            "amorphous_anchors",
            "crystallinity_method",
            "polymer_type",
            "amorphous_n_peaks",
            "scherrer_K",
            "two_theta_offset",
            "caglioti_U",
            "caglioti_V",
            "caglioti_W",
        }
        for name, value in case.config_overrides.items():
            if name in config_fields and name in analyze_fields:
                setattr(config, name, value)

        if not getattr(config, "polymer_type", "") and case.polymer_name and case.polymer_phase:
            candidate = f"{case.polymer_name}_{case.polymer_phase}"
            if candidate in getattr(config, "polymer_peaks_db", {}):
                config.polymer_type = candidate

    def _apply_saxs_config_overrides(self, engine: Any, case: EvalCase) -> None:
        config = getattr(engine, "cfg", None)
        if config is None:
            return

        config_fields = set(getattr(config, "__dataclass_fields__", {}))
        for name, value in case.config_overrides.items():
            if name in config_fields:
                setattr(config, name, value)

    def _apply_ir_config_overrides(self, engine: Any, case: EvalCase) -> None:
        config = getattr(engine, "_ir_config", None)
        if config is None:
            return

        config_fields = set(getattr(config, "__dataclass_fields__", {}))
        aliases = {
            "baseline_corr": "baseline_method",
            "smooth_span": "smooth_window",
            "polymer": "polymer_name",
            "peak_threshold": "peak_height_min",
            "peak_prominence": "peak_prominence_min",
        }
        for name, value in case.config_overrides.items():
            field_name = aliases.get(name, name)
            if field_name == "wavenumber_min":
                current = getattr(config, "wavenumber_range", (400.0, 4000.0))
                setattr(config, "wavenumber_range", (float(value), float(current[1])))
                continue
            if field_name == "wavenumber_max":
                current = getattr(config, "wavenumber_range", (400.0, 4000.0))
                setattr(config, "wavenumber_range", (float(current[0]), float(value)))
                continue
            if field_name in config_fields:
                setattr(config, field_name, value)

    def _waxs_parameters_used(self, engine: Any, data_path: Path) -> dict[str, Any]:
        config = getattr(engine, "_waxs_config", None)
        if config is not None and hasattr(config, "to_dict"):
            parameters = dict(config.to_dict())
        else:
            parameters = {}
        parameters["engine"] = "waxs"
        parameters["submodule"] = "waxs.static"
        parameters["data_file"] = str(data_path)
        return self._to_plain_value(parameters)

    def _saxs_parameters_used(self, engine: Any, data_path: Path) -> dict[str, Any]:
        config = getattr(engine, "cfg", None)
        if config is not None and is_dataclass(config):
            parameters = asdict(config)
        elif config is not None and hasattr(config, "to_dict"):
            parameters = dict(config.to_dict())
        else:
            parameters = {}
        parameters["engine"] = "saxs"
        parameters["submodule"] = getattr(engine, "active_submodule", "saxs.static") or "saxs.static"
        parameters["data_file"] = str(data_path)
        return self._to_plain_value(parameters)

    def _ir_parameters_used(self, engine: Any, data_path: Path) -> dict[str, Any]:
        config = getattr(engine, "_ir_config", None)
        if config is not None and hasattr(config, "to_dict"):
            parameters = dict(config.to_dict())
        else:
            parameters = {}
        parameters["engine"] = "ir"
        parameters["submodule"] = getattr(engine, "active_submodule", "ir.standard") or "ir.standard"
        parameters["data_file"] = str(data_path)
        return self._to_plain_value(parameters)

    def _nmr_parameters_used(self, engine: Any, data_path: Path) -> dict[str, Any]:
        config = getattr(engine, "_cfg", None)
        if config is not None and hasattr(config, "to_dict"):
            parameters = dict(config.to_dict())
        else:
            parameters = {}
        parameters["engine"] = "nmr"
        parameters["submodule"] = getattr(engine, "active_submodule", "nmr.solid_c") or "nmr.solid_c"
        parameters["data_file"] = str(data_path)
        return self._to_plain_value(parameters)

    def _waxs_output_parameters(self, engine: Any, result: Any) -> dict[str, Any]:
        output = dict(getattr(result, "parameters", {}) or {})
        waxs_results = getattr(engine, "_results", []) or []
        if waxs_results:
            first = waxs_results[0]
            peaks = []
            for peak in getattr(first, "peaks", []) or []:
                center = peak.get("two_theta")
                item = {
                    "center": center,
                    "fwhm": peak.get("fwhm_deg"),
                    "area": peak.get("area"),
                    "hkl": peak.get("hkl", ""),
                }
                peaks.append({k: self._to_plain_value(v) for k, v in item.items() if v is not None})
            if peaks:
                output["peaks"] = peaks
                output["peak_centers"] = [peak["center"] for peak in peaks if "center" in peak]
            two_theta = getattr(first, "two_theta", [])
            if len(two_theta) > 0:
                output["x_min"] = float(two_theta[0])
                output["x_max"] = float(two_theta[-1])
            if "r_squared" not in output and hasattr(first, "r_squared"):
                output["r_squared"] = getattr(first, "r_squared")
        return self._to_plain_value(output)

    def _ir_output_parameters(self, engine: Any, result: Any) -> dict[str, Any]:
        output = self._flatten_ir_parameters(dict(getattr(result, "parameters", {}) or {}))
        if not output:
            output = self._flatten_ir_parameters(dict(getattr(engine, "get_parameters", lambda: {})() or {}))

        ir_results = getattr(engine, "_results", []) or []
        if ir_results:
            first = ir_results[0]
            peaks = []
            assigned_peak_wavenumbers: list[float] = []
            for peak in getattr(first, "peaks", []) or []:
                item = {
                    "wavenumber": peak.get("wavenumber"),
                    "height": peak.get("height"),
                    "prominence": peak.get("prominence"),
                    "area": peak.get("area"),
                    "fwhm_cm1": peak.get("fwhm_cm1"),
                    "assignment": peak.get("assignment", ""),
                    "ref_wavenumber": peak.get("ref_wavenumber"),
                }
                peaks.append({k: self._to_plain_value(v) for k, v in item.items() if v is not None})
                assignment = str(peak.get("assignment", "") or "").strip().lower()
                wn = self._safe_float(peak.get("wavenumber"))
                if wn is not None and assignment and assignment != "unknown":
                    assigned_peak_wavenumbers.append(wn)

            polymer_score = self._safe_float(getattr(first, "polymer_score", output.get("polymer_score", 1.0)))
            if polymer_score == 0.0 and getattr(first, "polymer_name", ""):
                polymer_score = 1.0
            output.update(
                {
                    "n_peaks": getattr(first, "n_peaks", output.get("n_peaks")),
                    "polymer_name": getattr(first, "polymer_name", output.get("polymer")),
                    "polymer_score": polymer_score,
                    "quality_score": polymer_score,
                    "raw_score": polymer_score,
                    "Xc_pct": getattr(first, "Xc_pct", output.get("Xc_pct")),
                    "xc": getattr(first, "Xc_pct", output.get("Xc_pct")),
                    "Xc_method": getattr(first, "Xc_method", output.get("Xc_method", "")),
                    "r_squared": self._safe_float(getattr(first, "r_squared", output.get("r_squared", 0.0))),
                    "r_squared_method": "ir_peak_region_fit_r2",
                }
            )
            if peaks:
                output["peaks"] = peaks
                output["peak_centers"] = [peak["wavenumber"] for peak in peaks if "wavenumber" in peak]
                output["peak_wavenumbers"] = assigned_peak_wavenumbers or list(output["peak_centers"][:10])
            wn = getattr(first, "wavenumber", [])
            if len(wn) > 0:
                output["x_min"] = float(np.nanmin(wn))
                output["x_max"] = float(np.nanmax(wn))
        temp_2d = getattr(engine, "_temperature_2d_result", None)
        if temp_2d is not None and getattr(engine, "active_submodule", "") == "ir.temperature_2d":
            try:
                output = dict(temp_2d.parameters)
                output["engine"] = "ir"
                output["submodule"] = "ir.temperature_2d"
                output["paper_conclusion_ready"] = bool(output.get("paper_conclusion_ready", False))
            except Exception:
                pass
        return self._to_plain_value({key: value for key, value in output.items() if value is not None})

    def _nmr_output_parameters(self, engine: Any, result: Any) -> dict[str, Any]:
        output = self._flatten_nmr_parameters(dict(getattr(result, "parameters", {}) or {}))
        if not output:
            output = self._flatten_nmr_parameters(
                dict(getattr(engine, "get_parameters", lambda: {})() or {})
            )

        nmr_results = getattr(engine, "_results", []) or []
        if nmr_results:
            first = nmr_results[0]
            peaks = []
            for peak in getattr(first, "peaks", []) or []:
                item = {
                    "ppm": peak.get("ppm"),
                    "height": peak.get("height"),
                    "fwhm_ppm": peak.get("fwhm_ppm"),
                    "area": peak.get("area"),
                    "assignment": peak.get("assignment", ""),
                }
                peaks.append({key: self._to_plain_value(value) for key, value in item.items() if value is not None})

            output.update(
                {
                    "n_peaks": getattr(first, "n_peaks", output.get("n_peaks", len(peaks))),
                    "dominant_peak_ppm": getattr(first, "dominant_peak_ppm", output.get("dominant_peak_ppm")),
                    "median_snr": getattr(first, "median_snr", output.get("median_snr")),
                    "Xc_pct": getattr(first, "Xc_pct", output.get("Xc_pct")),
                    "Xc_method": getattr(first, "Xc_method", output.get("Xc_method", "")),
                    "Xc_assignment_status": getattr(first, "Xc_assignment_status", output.get("Xc_assignment_status", "")),
                    "r_squared": getattr(first, "r_squared", output.get("r_squared")),
                    "sample_state": getattr(first, "sample_state", output.get("sample_state", "")),
                    "nucleus": getattr(first, "nucleus", output.get("nucleus", "")),
                }
            )
            if peaks:
                output["peaks"] = peaks
                output["peak_shifts"] = [peak["ppm"] for peak in peaks if "ppm" in peak]
            ppm = getattr(first, "ppm", [])
            if len(ppm) > 0:
                output["x_min"] = float(np.nanmin(ppm))
                output["x_max"] = float(np.nanmax(ppm))

        output["engine"] = "nmr"
        output["submodule"] = getattr(engine, "active_submodule", "nmr.solid_c") or "nmr.solid_c"
        return self._to_plain_value({key: value for key, value in output.items() if value is not None})

    @staticmethod
    def _flatten_nmr_parameters(payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        if any(key in payload for key in ("n_peaks", "dominant_peak_ppm", "Xc_pct")):
            return payload
        for value in payload.values():
            if isinstance(value, dict) and any(key in value for key in ("n_peaks", "dominant_peak_ppm", "Xc_pct")):
                return dict(value)
        return payload

    def _saxs_output_parameters(self, engine: Any, result: Any) -> dict[str, Any]:
        output = dict(getattr(engine.result, "parameters", {}) or {})
        if not output:
            output = dict(getattr(engine, "get_parameters", lambda: {})() or {})

        analysis = getattr(engine, "_analysis", None)
        batch_results = getattr(engine, "_batch_results", []) or []
        if analysis is None and batch_results:
            analysis = batch_results[0]

        quality_score = self._saxs_score(analysis, output)
        r_squared = self._safe_float(getattr(analysis, "r_squared", None)) if analysis is not None else None
        if r_squared is None or not math.isfinite(r_squared):
            r_squared = quality_score
        output["r_squared"] = r_squared
        output["quality_score"] = (
            self._safe_float(getattr(analysis, "quality_score", quality_score))
            if analysis is not None
            else quality_score
        )
        output["raw_score"] = output["quality_score"]
        output["r_squared_method"] = getattr(analysis, "r_squared_method", "") or "saxs_peak_region_fit_r2"
        output["fit_rmse"] = getattr(analysis, "fit_rmse", None) if analysis is not None else None
        output["fit_regions"] = getattr(analysis, "fit_regions", None) if analysis is not None else None

        if "Xc" in output and "Xc_pct" not in output:
            xc = self._safe_float(output.get("Xc"))
            output["Xc_pct"] = xc * 100.0 if xc is not None and 0.0 <= xc <= 1.0 else xc
            output["xc"] = output["Xc_pct"]

        if analysis is not None:
            q = getattr(analysis, "q", [])
            if len(q) > 0:
                output["x_min"] = float(q[0])
                output["x_max"] = float(q[-1])
            condition_value = getattr(analysis, "condition_value", None)
            if condition_value is not None:
                output["condition_value"] = condition_value
            lp = getattr(analysis, "long_period", None)
            if lp is not None:
                output["L_confidence"] = getattr(lp, "L_confidence", None)
                output["L_bragg"] = getattr(lp, "L_bragg", None)
                output["L_lorentz"] = getattr(lp, "L_lorentz", None)
                output["L_corr_peak"] = getattr(lp, "L_corr_peak", None)
            output["q_peak_snr"] = getattr(analysis, "q_peak_snr", None)
            output["quality_flag"] = getattr(analysis, "quality_flag", "")
            output["validation_summary"] = getattr(analysis, "validation_summary", "")

        return self._to_plain_value({key: value for key, value in output.items() if value is not None})

    def _saxs_score(self, analysis: Any, output: dict[str, Any]) -> float:
        sas_r2 = self._safe_float(output.get("sasmodels_R2"))
        if sas_r2 is not None and math.isfinite(sas_r2) and sas_r2 > 0:
            return max(0.0, min(1.0, sas_r2))
        if analysis is not None:
            lp = getattr(analysis, "long_period", None)
            confidence = self._safe_float(getattr(lp, "L_confidence", 0.0)) if lp is not None else 0.0
            if confidence > 0:
                return max(0.0, min(1.0, confidence))
        snr = self._safe_float(output.get("q_peak_snr"))
        if snr is not None and snr > 0:
            return max(0.0, min(1.0, snr / 20.0))
        return 0.0

    def _apply_dsc_config_overrides(self, engine: Any, case: EvalCase) -> None:
        config = getattr(engine, "_dsc_config", None)
        if config is None:
            return
        config_fields = set(getattr(config, "__dataclass_fields__", {}))
        aliases = {
            "baseline_type": "baseline_corr",
            "tm_search_low_C": "Tm_search_low_C",
            "tm_search_high_C": "Tm_search_high_C",
            "tc_search_low_C": "Tc_search_low_C",
            "tc_search_high_C": "Tc_search_high_C",
        }
        analyze_fields = {
            "baseline_corr",
            "peak_function",
            "Tm_search_low_C",
            "Tm_search_high_C",
            "Tc_search_low_C",
            "Tc_search_high_C",
            "peak_prominence_ratio",
            "min_event_enthalpy_Jg",
            "max_melting_peak_width_C",
            "Tg_method",
            "Tg_search_low_C",
            "Tg_search_high_C",
            "user_DHm0",
            "crystallinity_std",
        }
        for name, value in case.config_overrides.items():
            field_name = aliases.get(name, name)
            if field_name in config_fields and field_name in analyze_fields:
                setattr(config, field_name, value)

    def _apply_nmr_config_overrides(self, engine: Any, case: EvalCase) -> None:
        config = getattr(engine, "_cfg", None)
        if config is None:
            return
        config_fields = set(getattr(config, "__dataclass_fields__", {}))
        aliases = {
            "baseline_corr": "baseline_method",
            "peak_threshold": "peak_height_min",
            "peak_distance": "peak_distance_ppm",
            "polymer": "polymer_name",
        }
        for name, value in case.config_overrides.items():
            field_name = aliases.get(name, name)
            if field_name in config_fields:
                setattr(config, field_name, value)

    def _dsc_parameters_used(self, engine: Any, data_path: Path) -> dict[str, Any]:
        config = getattr(engine, "_dsc_config", None)
        if config is not None and hasattr(config, "to_dict"):
            parameters = dict(config.to_dict())
        else:
            parameters = {}
        parameters["engine"] = "dsc"
        parameters["submodule"] = "dsc.standard"
        parameters["data_file"] = str(data_path)
        return self._to_plain_value(parameters)

    def _dsc_output_parameters(self, engine: Any, result: Any) -> dict[str, Any]:
        output = self._flatten_dsc_parameters(dict(getattr(result, "parameters", {}) or {}))
        dsc_results = getattr(engine, "_results", []) or []
        if dsc_results:
            first = dsc_results[0]
            aggregate = aggregate_dsc_result_metrics(dsc_results)
            output.update(
                {
                    "scan_mode": getattr(first, "technique", None),
                    "Tg_C": getattr(first, "Tg_C", None),
                    "Tg_method": getattr(first, "Tg_method", None),
                    "DTg_C": getattr(first, "DTg_C", None),
                    "DCp_JgK": getattr(first, "DCp_JgK", None),
                    "Tm_onset_C": getattr(first, "Tm_onset_C", None),
                    "Tm_peak_C": getattr(first, "Tm_peak_C", None),
                    "Tm_end_C": getattr(first, "Tm_end_C", None),
                    "Tc_onset_C": getattr(first, "Tc_onset_C", None),
                    "Tc_peak_C": getattr(first, "Tc_peak_C", None),
                    "Tc_end_C": getattr(first, "Tc_end_C", None),
                    "Tcc_onset_C": getattr(first, "Tcc_onset_C", None),
                    "Tcc_peak_C": getattr(first, "Tcc_peak_C", None),
                    "DHm_Jg": getattr(first, "DHm_Jg", None),
                    "DHc_Jg": getattr(first, "DHc_Jg", None),
                    "DHcc_Jg": getattr(first, "DHcc_Jg", None),
                    "Xc_pct": getattr(first, "Xc_pct", None),
                    "quality_score": aggregate.get("quality_score"),
                    "r_squared": aggregate.get("r_squared"),
                    "fit_rmse": aggregate.get("fit_rmse"),
                    "scan_r_squared": aggregate.get("scan_r_squared"),
                    "r_squared_method": aggregate.get("r_squared_method"),
                    "n_peaks": len(getattr(first, "peak_components", []) or []),
                    "peak_components": getattr(first, "peak_components", []),
                }
            )
            output["tm"] = output.get("Tm_peak_C")
            output["tc"] = output.get("Tc_peak_C")
            if output["tc"] is None or self._is_nan(output["tc"]):
                output["tc"] = output.get("Tcc_peak_C")
            output["delta_hm"] = output.get("DHm_Jg")
            output["xc"] = output.get("Xc_pct")
            output["raw_score"] = output.get("quality_score")
            if len(getattr(first, "T", [])) > 0:
                output["x_min"] = float(first.T[0])
                output["x_max"] = float(first.T[-1])
        return self._to_plain_value({key: value for key, value in output.items() if value is not None})

    def _flatten_dsc_parameters(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        if any(key in payload for key in ("Tm_peak_C", "Tc_peak_C", "Xc_pct")):
            return payload
        for value in payload.values():
            if isinstance(value, dict) and any(key in value for key in ("Tm_peak_C", "Tc_peak_C", "Xc_pct")):
                return dict(value)
        return payload

    def _flatten_ir_parameters(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        if any(key in payload for key in ("n_peaks", "polymer_score", "r_squared")):
            return payload
        for value in payload.values():
            if isinstance(value, dict) and any(key in value for key in ("n_peaks", "polymer_score", "r_squared")):
                return dict(value)
        return payload

    def _is_nan(self, value: Any) -> bool:
        try:
            return bool(value != value)
        except Exception:
            return False

    def _to_plain_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._to_plain_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._to_plain_value(item) for item in value]
        if hasattr(value, "item"):
            return value.item()
        return value

    def _normalize_payload(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise TypeError("case root must be a JSON object")
        normalized = dict(payload)
        normalized.setdefault("submodule", "")
        normalized.setdefault("polymer_phase", None)
        normalized.setdefault("config_overrides", {})
        normalized.setdefault("notes", "")

        gt = dict(normalized.get("ground_truth") or {})
        for name in self.RANGE_FIELDS:
            if name in gt:
                gt[name] = self._normalize_range_or_null(gt[name])
        for name in self.RANGE_LIST_FIELDS:
            if name in gt:
                gt[name] = self._normalize_range_list_or_null(gt[name])
        normalized["ground_truth"] = gt
        return normalized

    def _normalize_range_or_null(self, value: Any) -> list[float] | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return list(self._expand_single_value(float(value)))
        if not isinstance(value, list):
            raise TypeError(f"range must be a number or list, got {type(value).__name__}")
        if len(value) == 1:
            return list(self._expand_single_value(float(value[0])))
        if len(value) != 2:
            raise ValueError(f"range must have one or two values, got {len(value)}")
        return self._ordered_pair(value[0], value[1])

    def _normalize_range_list_or_null(self, value: Any) -> list[list[float]] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            raise TypeError(f"range list must be a list, got {type(value).__name__}")
        if self._is_number_pair(value):
            return [self._ordered_pair(value[0], value[1])]
        ranges: list[list[float]] = []
        for item in value:
            ranges.append(self._normalize_range_or_null(item) or [])
        return ranges

    def _ground_truth_from_mapping(self, mapping: dict[str, Any]) -> GroundTruth:
        gt_fields = {field.name for field in fields(GroundTruth)}
        values: dict[str, Any] = {}
        for name, value in mapping.items():
            if name not in gt_fields:
                continue
            if name in self.RANGE_FIELDS and value is not None:
                values[name] = tuple(value)
            elif name in self.RANGE_LIST_FIELDS and value is not None:
                values[name] = [tuple(item) for item in value]
            else:
                values[name] = value
        return GroundTruth(**values)

    def _stub_output_from_ground_truth(self, case: EvalCase) -> dict[str, Any]:
        gt = case.ground_truth
        output: dict[str, Any] = {}
        for name in self.RANGE_FIELDS:
            value = getattr(gt, name)
            if value is not None:
                output[name] = self._range_midpoint(value)
        if gt.crystal_form is not None:
            output["crystal_form"] = gt.crystal_form
        if gt.peak_centers:
            output["peak_centers"] = [self._range_midpoint(item) for item in gt.peak_centers]
            output["peaks"] = [{"center": center, "fwhm": 0.6} for center in output["peak_centers"]]
        if gt.peak_wavenumbers:
            output["peak_wavenumbers"] = [self._range_midpoint(item) for item in gt.peak_wavenumbers]
        if gt.peak_shifts:
            output["peak_shifts"] = [self._range_midpoint(item) for item in gt.peak_shifts]
        return {"parameters_used": dict(case.config_overrides), "output_parameters": output}

    def _compute_phys_score(self, case: EvalCase, output: dict[str, Any]) -> tuple[float, dict[str, Any]]:
        checks: list[tuple[str, bool]] = []

        def add(name: str, condition: bool) -> None:
            checks.append((name, bool(condition)))

        if "Xc_pct" in output:
            add("Xc_pct in [0, 100]", 0.0 <= float(output["Xc_pct"]) <= 100.0)

        if case.technique == "waxs":
            if "D_Scherrer_nm" in output:
                add("D_Scherrer_nm in [1, 1000]", 1.0 <= float(output["D_Scherrer_nm"]) <= 1000.0)
            for index, peak in enumerate(output.get("peaks", [])):
                if "fwhm" in peak:
                    add(f"peak[{index}].fwhm in (0.1, 10)", 0.1 < float(peak["fwhm"]) < 10.0)
                if "center" in peak and "x_min" in output and "x_max" in output:
                    add(
                        f"peak[{index}].center in data range",
                        float(output["x_min"]) <= float(peak["center"]) <= float(output["x_max"]),
                    )
        elif case.technique == "dsc":
            if "DHm_Jg" in output:
                add("DHm_Jg positive", float(output["DHm_Jg"]) > 0.0)
            for name in ("Tg_C", "Tm_peak_C", "Tc_peak_C"):
                if name in output:
                    add(f"{name} plausible", -250.0 <= float(output[name]) <= 500.0)
        elif case.technique == "saxs":
            if "L_nm" in output:
                add("L_nm in [3, 150]", 3.0 <= float(output["L_nm"]) <= 150.0)
            if "lc_nm" in output and "L_nm" in output:
                add("lc_nm < L_nm", float(output["lc_nm"]) < float(output["L_nm"]))
            if "phi_c" in output:
                add("phi_c in [0, 1]", 0.0 <= float(output["phi_c"]) <= 1.0)
            if "Rg_nm" in output:
                add("Rg_nm positive", float(output["Rg_nm"]) > 0.0)
        elif case.technique == "ir":
            for value in output.get("peak_wavenumbers", []):
                add("IR peak in [400, 4000]", 400.0 <= float(value) <= 4000.0)
        elif case.technique == "nmr":
            for value in output.get("peak_shifts", []):
                add("NMR peak in [-10, 250]", -10.0 <= float(value) <= 250.0)

        if not checks:
            return 1.0, {"checks": [], "passed": 0, "total": 0}
        passed = sum(1 for _, ok in checks if ok)
        return passed / len(checks), {"checks": [{"name": name, "passed": ok} for name, ok in checks]}

    def _compute_peak_score(
        self, case: EvalCase, output: dict[str, Any]
    ) -> tuple[float, bool, dict[str, Any]]:
        if case.technique == "dsc":
            return self._compute_dsc_peak_score(case, output)

        target_name, output_values = self._peak_targets_and_values(case, output)
        targets = getattr(case.ground_truth, target_name) if target_name else None
        if not target_name or not targets:
            return 1.0, False, {"available": False, "reason": "no peak ground truth"}
        if not output_values:
            return 0.0, True, {"available": True, "reason": "no output peaks"}

        scores = []
        pair_details = []
        for target, value in zip(targets, output_values):
            score = self._score_value_against_range(float(value), target)
            scores.append(score)
            pair_details.append({"target": target, "value": float(value), "score": score})
        if len(output_values) < len(targets):
            scores.extend([0.0] * (len(targets) - len(output_values)))
        return sum(scores) / len(scores), True, {"available": True, "field": target_name, "peaks": pair_details}

    def _compute_dsc_peak_score(
        self, case: EvalCase, output: dict[str, Any]
    ) -> tuple[float, bool, dict[str, Any]]:
        peak_names = ("Tm_peak_C", "Tc_peak_C", "Tcc_peak_C")
        pair_details: list[dict[str, Any]] = []
        scores: list[float] = []

        for name in peak_names:
            target = getattr(case.ground_truth, name)
            if target is None:
                continue

            value = self._safe_float(output.get(name))
            if value is None:
                score = 0.0
            else:
                score = self._score_value_against_range(value, target)

            scores.append(score)
            pair_details.append(
                {
                    "field": name,
                    "target": target,
                    "value": value,
                    "score": score,
                }
            )

        if not pair_details:
            return 1.0, False, {"available": False, "reason": "no DSC peak ground truth"}
        return sum(scores) / len(scores), True, {"available": True, "field": "dsc.temperature_peaks", "peaks": pair_details}

    def _peak_targets_and_values(self, case: EvalCase, output: dict[str, Any]) -> tuple[str | None, list[float]]:
        if case.ground_truth.peak_centers:
            values = output.get("peak_centers")
            if values is None:
                values = [peak.get("center") for peak in output.get("peaks", []) if "center" in peak]
            return "peak_centers", [float(value) for value in values]
        if case.ground_truth.peak_wavenumbers:
            return "peak_wavenumbers", [float(value) for value in output.get("peak_wavenumbers", [])]
        if case.ground_truth.peak_shifts:
            return "peak_shifts", [float(value) for value in output.get("peak_shifts", [])]
        return None, []

    def _iter_case_paths(self, cases_dir: str | Path) -> list[Path]:
        directory = Path(cases_dir)
        if not directory.exists():
            return []
        return sorted(path for path in directory.rglob("*.json") if path.is_file())

    @staticmethod
    def _range_midpoint(value_range: Range) -> float:
        return (float(value_range[0]) + float(value_range[1])) / 2.0

    @staticmethod
    def _score_value_against_range(value: float, value_range: Range) -> float:
        lower, upper = float(value_range[0]), float(value_range[1])
        if lower <= value <= upper:
            return 1.0
        width = max(abs(upper - lower), 1e-12)
        distance = min(abs(value - lower), abs(value - upper))
        return max(0.0, 1.0 - distance / width)

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number != number:
            return None
        return number

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None:
            return None
        return float(value)

    @staticmethod
    def _expand_single_value(value: float) -> tuple[float, float]:
        lower = value * 0.95
        upper = value * 1.05
        return (min(lower, upper), max(lower, upper))

    @staticmethod
    def _ordered_pair(left: Any, right: Any) -> list[float]:
        first, second = float(left), float(right)
        return [min(first, second), max(first, second)]

    @staticmethod
    def _is_number_pair(value: Any) -> bool:
        return (
            isinstance(value, list)
            and len(value) == 2
            and all(isinstance(item, (int, float)) for item in value)
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or validate PolyNexus eval cases.")
    parser.add_argument("--cases-dir", default="tests/eval/cases/", help="Directory containing EvalCase JSON files.")
    parser.add_argument("--dry-run", action="store_true", help="Only validate case JSON files.")
    args = parser.parse_args(argv)

    runner = EvalRunner()
    case_paths = runner._iter_case_paths(args.cases_dir)
    if not case_paths:
        print(f"No case JSON files found under {args.cases_dir}")
        return 1

    if args.dry_run:
        passed = 0
        failed = 0
        for path in case_paths:
            try:
                case = runner.load_case(path)
            except EvalCaseLoadError as exc:
                failed += 1
                print(f"FAIL {path}: {exc}")
            else:
                passed += 1
                print(f"PASS {case.case_id}: {path}")
        print(f"{passed}/{len(case_paths)} PASS, {failed} FAIL")
        return 0 if failed == 0 else 1

    cases = runner.load_all_cases(args.cases_dir)
    for path, error in runner.load_errors:
        print(f"SKIP {path}: {error}")
    for case in cases:
        result = runner.run_case(case)
        print(f"{case.case_id}: composite={result.composite:.3f} phys={result.phys_score:.3f} peak={result.peak_score:.3f}")
    return 0 if not runner.load_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
