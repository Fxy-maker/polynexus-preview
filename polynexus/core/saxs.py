"""SAXS analysis engine wrapper for PolyNexus.

This module keeps the technique registry and BaseEngine-facing entry point
thin, while delegating real analysis work to `polynexus.core.saxs_engine`.
"""

# This compatibility wrapper intentionally retains legacy re-exports and
# single-letter intensity names; keep those baseline diagnostics scoped here.
# ruff: noqa: E741, F401, F841

from __future__ import annotations

import logging
import os
from copy import deepcopy
from dataclasses import replace
from typing import Any, Dict, List, Optional

import numpy as np

from .engine import BaseEngine, EngineCategory, register_technique
from .submodule_registry import SubModuleSpec, register_submodule
from .saxs_engine import (
    SAXSConfig,
    ExperimentCondition,
    read_image,
    read_1d_profile,
    extract_geometry_from_header,
    scan_experiment_dir,
    assemble_dataset,
    recover_condition_axis,
    preprocess_pipeline,
    _integrate_pyfai_shadow,
    analyze_single,
    ensemble_long_period,
    compute_structure_params,
    scattering_invariant,
    correlation_function,
    idf_analysis,
    porod_analysis,
    kratky_analysis,
    sasmodels_fit,
    analyze_strain_series,
    check_invariant_conservation,
    StrainSeriesResult,
    analyze_temperature_series,
    gibbs_thomson_analysis,
    avrami_kinetics,
    detect_melting_from_saxs,
    TempSeriesResult,
    analyze_anisotropy,
    AnisotropyResult,
    export_parameters_csv,
    export_1d_profile,
    export_strain_series_csv,
    export_temp_series_csv,
)
from . import saxs_batch_helpers as _saxs_batch_helpers
from .saxs_sequence_qa import build_sequence_qa_summary
from .saxs_result_contract import publish_saxs_result_contract
from .saxs_export_bundle import SAXSExportBundle, export_saxs_bundle
from .saxs_engine.processed_profile import ProcessedProfile


logger = logging.getLogger(__name__)


def _float_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _text_or_empty(value: Any) -> str:
    return "" if value is None else str(value)


def _series_metric_evidence_payload(series: Any) -> Dict[str, Any]:
    """Copy an existing series evidence summary for view/persistence transport."""

    evidence = getattr(series, "metric_evidence", None)
    if not isinstance(evidence, dict) or not evidence:
        return {}
    return {
        str(name): deepcopy(summary)
        for name, summary in evidence.items()
    }


@register_technique("saxs")
@register_submodule(SubModuleSpec(
    id="saxs.static",
    parent_technique="saxs",
    label="静态 SAXS",
    icon="\U0001f52c",
    description="全方位角积分，片晶结构，长周期，结晶度",
    priority=0,
    required_polymer_families=["polyolefin", "polyester", "polyamide", "fluoropolymer"],
    accepted_formats=["*.edf", "*.dat", "*.txt", "*.csv"],
    input_mode="single",
    config_schema={
        "baseline_method": {
            "type": "choice",
            "options": ["subtract", "normalize", "none"],
            "default": "normalize",
            "label": "背景处理",
        },
        "smooth_window": {"type": "int", "min": 3, "max": 31, "default": 7, "label": "平滑窗口"},
        "q_range_min": {"type": "float", "min": 0.001, "max": 1.0, "default": 0.01, "decimals": 4, "label": "q 下限"},
        "q_range_max": {"type": "float", "min": 0.1, "max": 10.0, "default": 2.0, "decimals": 2, "label": "q 上限"},
    },
    output_parameters=[
        {"key": "L_nm", "label": "长周期 L (nm)", "format": ".2f"},
        {"key": "lc_nm", "label": "晶层厚度 lc (nm)", "format": ".2f"},
        {"key": "la_nm", "label": "非晶层厚度 la (nm)", "format": ".2f"},
        {"key": "phi_c", "label": "结晶度", "format": ".3f"},
        {"key": "Kp", "label": "Porod 常数", "format": ".4e"},
    ],
    figure_types=["scattering_profile", "correlation_function", "idf", "porod", "kratky", "guinier"],
))
@register_submodule(SubModuleSpec(
    id="saxs.strain",
    parent_technique="saxs",
    label="原位拉伸 SAXS",
    icon="\U0001f4d0",
    description="阶段识别: 弹性→塑性→微纤化，空穴分析",
    priority=10,
    required_polymer_families=["polyolefin", "polyester", "polyamide"],
    accepted_formats=["directory"],
    input_mode="sequence",
    output_parameters=[
        {"key": "orientation_f", "label": "Herman 取向因子", "format": ".3f"},
        {"key": "void_volume_fraction", "label": "空穴体积分数", "format": ".3f"},
        {"key": "fibril_diameter_nm", "label": "微纤直径 (nm)", "format": ".2f"},
    ],
    figure_types=["scattering_waterfall", "structure_evolution", "invariant_conservation"],
))
@register_submodule(SubModuleSpec(
    id="saxs.temperature",
    parent_technique="saxs",
    label="原位变温 SAXS",
    icon="\U0001f321",
    description="熔融/结晶，Gibbs-Thomson，Avrami 动力学",
    priority=10,
    required_polymer_families=["polyolefin", "polyester", "polyamide"],
    accepted_formats=["directory"],
    input_mode="sequence",
    output_parameters=[
        {"key": "Tm_SAXS_C", "label": "SAXS 熔融温度 (C)", "format": ".1f"},
        {"key": "Avrami_n", "label": "Avrami 指数 n", "format": ".2f"},
    ],
    figure_types=["temperature_waterfall", "temperature_parameters", "scattering_heatmap", "avrami"],
))
class SAXSEngine(BaseEngine):
    """Thin BaseEngine wrapper for the modular SAXS engine."""

    name = "saxs"
    label = "SAXS"
    icon = "\U0001f52c"
    category = EngineCategory.EXPERIMENTAL
    description = (
        "Small-Angle X-ray Scattering: lamellar structure, long period, "
        "crystallinity, in-situ strain/temperature, anisotropy"
    )

    def __init__(self, config=None, log_fn=None):
        super().__init__(config=config, log_fn=log_fn)
        self.cfg = config if isinstance(config, SAXSConfig) else SAXSConfig(experiment_type="static")
        if not isinstance(self.cfg, SAXSConfig):
            self.cfg = SAXSConfig(experiment_type="static")
        self._q = None
        self._I = None
        self._I_smooth = None
        self._I_merid = None
        self._I_equat = None
        self._img = None
        self._header = None
        self._analysis = None
        self._results: List[Any] = []
        self._batch_results: List[Any] = []
        self._batch_params: List[Dict[str, Any]] = []
        self._temperature_result: Optional[TempSeriesResult] = None
        self._strain_result: Optional[StrainSeriesResult] = None

        self._file_list: List[str] = []
        self._q_list: List[np.ndarray] = []
        self._I_list: List[np.ndarray] = []
        self._I_merid_list: List[np.ndarray | None] = []
        self._I_equat_list: List[np.ndarray | None] = []
        self._q_pyfai_list: List[np.ndarray] = []
        self._I_pyfai_list: List[np.ndarray] = []
        self._conditions: List[float] = []
        self._condition_keys: List[object] = []
        self._condition_sources: List[str] = []
        self._condition_source_keys: List[str] = []
        self._condition_source_texts: List[str] = []
        self._condition_confidences: List[float] = []
        self._condition_type: str = ""
        self._processed_profile: Optional[ProcessedProfile] = None
        self._processed_list: List[ProcessedProfile] = []
        self._sequence_qa_summary: Dict[str, Any] = {}
        self._geometry_sources: List[str] = []
        self._geometry_confidences: List[float] = []
        self._skipped_files: List[Dict[str, Any]] = []

    @staticmethod
    def _processed_profile_from_payload(
        payload: Dict[str, Any],
        *,
        source: str,
        filepath: str | None = None,
    ) -> ProcessedProfile | None:
        """Build the stable profile projection while preserving legacy arrays."""
        q = payload.get("q")
        raw = payload.get("Iq", payload.get("I"))
        if q is None or raw is None:
            return None

        q_array = np.atleast_1d(np.asarray(q, dtype=float))
        raw_array = np.atleast_1d(np.asarray(raw, dtype=float))
        diagnostics: Dict[str, Any] = {}
        if len(q_array) != len(raw_array):
            diagnostics["length_mismatch"] = {
                "q": len(q_array),
                "raw": len(raw_array),
            }
        for name in (
            "Iq_corrected", "Iq_norm", "Iq_smooth",
            "Iq_merid", "Iq_merid_corrected", "Iq_merid_norm", "Iq_merid_smooth",
            "Iq_equat", "Iq_equat_corrected", "Iq_equat_norm", "Iq_equat_smooth",
        ):
            value = payload.get(name)
            if value is not None:
                layer_array = np.asarray(value)
                layer_length = layer_array.size if layer_array.ndim == 0 else len(layer_array)
                if layer_length != len(q_array):
                    diagnostics.setdefault("layer_length_mismatch", {})[name] = layer_length

        return ProcessedProfile(
            q=q_array,
            raw=raw_array,
            corrected=payload.get("Iq_corrected"),
            normalized=payload.get("Iq_norm"),
            smoothed=payload.get("Iq_smooth"),
            meridional_raw=payload.get("Iq_merid"),
            meridional_corrected=payload.get("Iq_merid_corrected"),
            meridional_normalized=payload.get("Iq_merid_norm"),
            meridional_smoothed=payload.get("Iq_merid_smooth"),
            equatorial_raw=payload.get("Iq_equat"),
            equatorial_corrected=payload.get("Iq_equat_corrected"),
            equatorial_normalized=payload.get("Iq_equat_norm"),
            equatorial_smoothed=payload.get("Iq_equat_smooth"),
            provenance={"source": source, **({"file": filepath} if filepath else {})},
            quality_status="WARN" if diagnostics else "OK",
            diagnostics=diagnostics,
        )

    def _publish_processed_profile(self, profile: ProcessedProfile | None) -> None:
        self._processed_profile = profile
        if profile is not None:
            self.result.raw_data["processed_profile"] = profile
            self.result.metadata["processed_profile_provenance"] = dict(profile.provenance)

    @property
    def processed_profile(self) -> ProcessedProfile | None:
        return self._processed_profile

    @property
    def processed_profiles(self) -> tuple[ProcessedProfile, ...]:
        return tuple(self._processed_list)

    @property
    def sequence_qa_summary(self) -> Dict[str, Any]:
        return dict(self._sequence_qa_summary)

    def _validate_results(self) -> bool:
        """Run generic validation and publish the SAXS result contract."""
        base_valid = super()._validate_results()
        publish_saxs_result_contract(self)
        return bool(base_valid and self.result.validation_passed)

    def run_pipeline(
        self,
        filepath: str,
        output_dir: str = "",
        skip_to: str | None = None,
    ) -> Any:
        """Publish SAXS evidence even when load or preprocessing exits early."""
        result = super().run_pipeline(filepath, output_dir=output_dir, skip_to=skip_to)
        publish_saxs_result_contract(self)
        return result

    def _apply_submodule_defaults(self) -> None:
        submodule = getattr(self, "active_submodule", "") or ""
        experiment_type = str(getattr(self.cfg, "experiment_type", "") or "").lower()
        current_label = str(getattr(self.cfg, "condition_label", "") or "").strip()

        is_strain = submodule == "saxs.strain" or experiment_type == "strain"
        is_temperature = submodule == "saxs.temperature" or experiment_type == "temperature"

        if is_strain:
            self.cfg.experiment_type = "strain"
            if not current_label or current_label.lower() == "condition":
                self.cfg.condition_label = "Strain"
            self.cfg.condition_unit = "%"
            self.cfg.do_stretching = True
        elif is_temperature:
            self.cfg.experiment_type = "temperature"
            if not current_label or current_label.lower() == "condition":
                self.cfg.condition_label = "Temperature"
            self.cfg.condition_unit = "C"
        else:
            if not getattr(self.cfg, "experiment_type", ""):
                self.cfg.experiment_type = "static"
            if not getattr(self.cfg, "condition_label", ""):
                self.cfg.condition_label = "Condition"
            if not getattr(self.cfg, "condition_unit", ""):
                self.cfg.condition_unit = ""
            if not hasattr(self.cfg, "do_stretching"):
                self.cfg.do_stretching = False

    def _looks_like_strain_series(self) -> bool:
        import re
        dir_name = os.path.basename(os.path.dirname(str(self._file_list[0]))) if getattr(self, "_file_list", None) else ""
        name_hints = " ".join([dir_name, " ".join(os.path.basename(str(p)) for p in getattr(self, "_file_list", []))]).lower()
        names = [os.path.basename(str(p)) for p in getattr(self, "_file_list", [])]
        if not names:
            return False
        if any(token in name_hints for token in ("temp", "temperature", "变温", "升温", "降温")):
            return False
        if any(token in name_hints for token in ("strain", "tensile", "stretch", "拉伸")):
            return True
        hit_count = sum(1 for name in names if re.search(r"-(\d+)-[Ss]_", name))
        return hit_count >= max(2, len(names) // 2)

    def _looks_like_temperature_series(self) -> bool:
        import re
        dir_name = os.path.basename(os.path.dirname(str(self._file_list[0]))) if getattr(self, "_file_list", None) else ""
        name_hints = " ".join([dir_name, " ".join(os.path.basename(str(p)) for p in getattr(self, "_file_list", []))]).lower()
        names = [os.path.basename(str(p)) for p in getattr(self, "_file_list", [])]
        if not names:
            return False
        if any(token in name_hints for token in ("temp", "temperature", "thermal", "heat", "cool", "变温", "升温", "降温")):
            return True
        hits = 0
        for name in names:
            if re.search(r"(?:^|[_-])(?:t|temp)[_-]?\d{2,4}(?:c|deg|k)?(?:[_-]|\.|$)", name, re.IGNORECASE):
                hits += 1
                continue
            if re.search(r"(?:^|[_-])\d{2,4}[cC](?:[_-]|\.|$)", name):
                hits += 1
        return hits >= max(2, len(names) // 2)

    def load(self, filepath: str) -> bool:
        self._apply_submodule_defaults()
        if not os.path.exists(filepath):
            self.log(f"File not found: {filepath}")
            return False

        if os.path.isdir(filepath):
            return self._load_directory(filepath)

        if filepath.lower().endswith(".edf"):
            self._img, self._header = read_image(filepath)
            if self._img is None:
                self.log("Failed to read EDF file")
                return False
            self.cfg = extract_geometry_from_header(self._header, self.cfg)
            self._processed_profile = None
            self._processed_list = []
            self.log(f"EDF loaded: {self._img.shape}, SDD={self.cfg.sdd_m:.3f}m")
            return True

        if filepath.lower().endswith((".dat", ".txt", ".csv")):
            q, I, meta = read_1d_profile(filepath)
            if q is None or len(q) < 5:
                self.log("Failed to read 1D profile")
                return False
            self._q = q
            self._I = I
            self._img = None
            self._header = meta
            self.cfg = extract_geometry_from_header(meta, self.cfg)
            self._processed_profile = None
            self._processed_list = []
            self.log(f"1D profile loaded: {len(q)} points, q=[{q[0]:.3f}, {q[-1]:.3f}]")
            return True

        self.log(f"Unsupported format: {filepath}")
        return False

    def _load_directory(self, dirpath: str) -> bool:
        conditions = scan_experiment_dir(dirpath, self.cfg)
        if not conditions:
            self.log("No supported files found in directory")
            return False

        self._condition_type = self.cfg.experiment_type
        self._conditions = []
        self._q_list = []
        self._I_list = []
        self._I_merid_list = []
        self._I_equat_list = []
        self._q_pyfai_list = []
        self._I_pyfai_list = []
        self._file_list = []
        self._condition_keys = []
        self._condition_sources = []
        self._condition_source_keys = []
        self._condition_source_texts = []
        self._condition_confidences = []
        self._processed_profile = None
        self._processed_list = []
        self._sequence_qa_summary = {}
        self._geometry_sources = []
        self._geometry_confidences = []
        self._skipped_files = []

        total_loaded = 0
        for cond in conditions:
            for filepath in cond.files[:10]:
                if total_loaded >= 48:
                    break
                try:
                    img, header = read_image(str(filepath))
                    cfg_copy = extract_geometry_from_header(header, self.cfg)
                    if img is None:
                        q, I, _ = read_1d_profile(str(filepath))
                        pp = {"q": q, "Iq": I, "Iq_smooth": I}
                        I_merid, I_equat = None, None
                    else:
                        pp = preprocess_pipeline(img, cfg_copy)
                        q = pp["q"]
                        I = pp["Iq_smooth"]
                        I_merid = pp.get("Iq_merid_smooth")
                        I_equat = pp.get("Iq_equat_smooth")

                    self._q_list.append(q)
                    self._I_list.append(I)
                    self._I_merid_list.append(I_merid)
                    self._I_equat_list.append(I_equat)
                    profile = self._processed_profile_from_payload(
                        pp, source="directory_load", filepath=str(filepath)
                    )
                    if profile is not None:
                        self._processed_list.append(profile)
                    if img is not None:
                        q_pf, I_pf = _integrate_pyfai_shadow(img, cfg_copy)
                        self._q_pyfai_list.append(q_pf if len(q_pf) > 0 else np.array([]))
                        self._I_pyfai_list.append(I_pf if len(q_pf) > 0 else np.array([]))
                    else:
                        self._q_pyfai_list.append(np.array([]))
                        self._I_pyfai_list.append(np.array([]))
                    self._file_list.append(str(filepath))
                    self._conditions.append(cond.value)
                    condition_key = getattr(cond, "condition_key", None)
                    self._condition_keys.append(cond.value if condition_key is None else condition_key)
                    metadata = cond.metadata if isinstance(getattr(cond, "metadata", None), dict) else {}
                    self._condition_sources.append(_text_or_empty(metadata.get("condition_source", "")))
                    self._condition_source_keys.append(_text_or_empty(metadata.get("condition_source_key", "")))
                    self._condition_source_texts.append(_text_or_empty(metadata.get("condition_source_text", "")))
                    conf = metadata.get("condition_confidence")
                    try:
                        conf = float(conf)
                    except (TypeError, ValueError):
                        conf = np.nan
                    self._condition_confidences.append(conf)
                    self._geometry_sources.append("header" if header else "config_default")
                    self._geometry_confidences.append(0.95 if header else 0.5)
                    total_loaded += 1
                except Exception as e:
                    self._skipped_files.append({"file": str(filepath), "reason": "load_failed", "error": str(e)})
                    self.log(f"Warning: failed to load {os.path.basename(str(filepath))}: {e}")
                    logger.warning("SAXS batch file load failed.", exc_info=True)
            if total_loaded >= 48:
                break

        if total_loaded <= 1 and os.path.isdir(dirpath):
            import glob
            all_edf = sorted(glob.glob(os.path.join(dirpath, "*.edf")))
            if len(all_edf) > total_loaded:
                self._q_list = []
                self._I_list = []
                self._I_merid_list = []
                self._I_equat_list = []
                self._file_list = []
                self._conditions = []
                self._condition_keys = []
                self._condition_sources = []
                self._condition_source_keys = []
                self._condition_source_texts = []
                self._condition_confidences = []
                self._processed_list = []
                self._geometry_sources = []
                self._geometry_confidences = []
                for edf in all_edf[:48]:
                    try:
                        img, header = read_image(edf)
                        cfg_copy = extract_geometry_from_header(header, self.cfg)
                        if img is not None:
                            pp = preprocess_pipeline(img, cfg_copy)
                            self._q_list.append(pp["q"])
                            self._I_list.append(pp["Iq_smooth"])
                            self._I_merid_list.append(pp.get("Iq_merid_smooth"))
                            self._I_equat_list.append(pp.get("Iq_equat_smooth"))
                            q_pf, I_pf = _integrate_pyfai_shadow(img, cfg_copy)
                            self._q_pyfai_list.append(q_pf if len(q_pf) > 0 else np.array([]))
                            self._I_pyfai_list.append(I_pf if len(q_pf) > 0 else np.array([]))
                        else:
                            q, I, _ = read_1d_profile(edf)
                            pp = {"q": q, "Iq": I, "Iq_smooth": I}
                            self._q_list.append(q)
                            self._I_list.append(I)
                            self._I_merid_list.append(None)
                            self._I_equat_list.append(None)
                            self._q_pyfai_list.append(np.array([]))
                            self._I_pyfai_list.append(np.array([]))
                        profile = self._processed_profile_from_payload(
                            pp, source="directory_fallback", filepath=edf
                        )
                        if profile is not None:
                            self._processed_list.append(profile)
                        self._file_list.append(edf)
                        self._conditions.append(np.nan)
                        self._condition_keys.append(f"unresolved::{os.path.basename(str(edf))}")
                        self._condition_sources.append("unresolved")
                        self._condition_source_keys.append("")
                        self._condition_source_texts.append(os.path.basename(str(edf)))
                        self._condition_confidences.append(0.0)
                        self._geometry_sources.append("header" if header else "config_default")
                        self._geometry_confidences.append(0.95 if header else 0.5)
                    except Exception as e:
                        self._skipped_files.append({"file": edf, "reason": "fallback_load_failed", "error": str(e)})
                        self.log(f"Warning: failed to load {os.path.basename(edf)}: {e}")
                        logger.warning("SAXS EDF fallback load failed.", exc_info=True)
                if not self._condition_type:
                    self._condition_type = "static"

        if self._condition_type == "static" and self._looks_like_temperature_series():
            self.cfg.experiment_type = "temperature"
            self.cfg.condition_label = "Temperature"
            self.cfg.condition_unit = "C"
            self._condition_type = "temperature"
            recovered = [recover_condition_axis(p, self.cfg) for p in self._file_list]
            self._conditions = [item.get("value", np.nan) for item in recovered]
            self._condition_keys = [item.get("condition_key", np.nan) for item in recovered]
            self._condition_sources = [str(item.get("source", "") or "") for item in recovered]
            self._condition_source_keys = [str(item.get("source_key", "") or "") for item in recovered]
            self._condition_source_texts = [str(item.get("source_text", "") or "") for item in recovered]
            self._condition_confidences = [float(item.get("confidence", 0.0) or 0.0) for item in recovered]
            self.log("Directory pattern suggests temperature series; switched SAXS route to temperature")

        if self._condition_type == "static" and self._looks_like_strain_series():
            self.cfg.experiment_type = "strain"
            self.cfg.condition_label = "Strain"
            self.cfg.condition_unit = "%"
            self.cfg.do_stretching = True
            self._condition_type = "strain"
            self._conditions = [self._parse_strain_from_filename(p) for p in self._file_list]
            self._condition_keys = list(self._conditions)
            self._condition_sources = [
                "path_filename" if np.isfinite(v) else "unresolved"
                for v in self._conditions
            ]
            self._condition_source_keys = [
                "strain_dash_S_suffix" if np.isfinite(v) else ""
                for v in self._conditions
            ]
            self._condition_source_texts = [os.path.basename(str(p)) for p in self._file_list]
            self._condition_confidences = [
                0.62 if np.isfinite(v) else 0.0
                for v in self._conditions
            ]
            self.log("Directory pattern suggests strain series; switched SAXS route to strain")

        finite_conditions = [float(v) for v in self._conditions if np.isfinite(v)]
        if finite_conditions:
            self.log(
                f"Directory loaded: {len(self._q_list)} frames, "
                f"type={self._condition_type}, "
                f"range=[{min(finite_conditions):.1f}, {max(finite_conditions):.1f}]"
            )
        else:
            self.log(
                f"Directory loaded: {len(self._q_list)} frames, "
                f"type={self._condition_type}, range=[unresolved]"
            )

        discovered_files = [
            str(filepath)
            for condition in conditions
            for filepath in getattr(condition, "files", [])
        ]
        loaded_set = set(self._file_list)
        recorded_skips = {str(item.get("file", "")) for item in self._skipped_files}
        for discovered in discovered_files:
            if discovered not in loaded_set and discovered not in recorded_skips:
                self._skipped_files.append({"file": discovered, "reason": "load_limit"})

        self._sequence_qa_summary = build_sequence_qa_summary(
            discovered_files=discovered_files,
            loaded_files=self._file_list,
            skipped_files=self._skipped_files,
            conditions=self._conditions,
            condition_keys=self._condition_keys,
            condition_sources=self._condition_sources,
            condition_source_keys=self._condition_source_keys,
            condition_source_texts=self._condition_source_texts,
            condition_confidences=self._condition_confidences,
            geometry_sources=self._geometry_sources,
            geometry_confidences=self._geometry_confidences,
        )
        self.result.metadata["sequence_qa"] = self._sequence_qa_summary
        self.result.raw_data["processed_profiles"] = tuple(self._processed_list)

        if self._q_list:
            self._q = self._q_list[0]
            self._I = self._I_list[0]
            self._publish_processed_profile(self._processed_list[0] if self._processed_list else None)
        return len(self._q_list) > 0

    def _parse_strain_from_filename(self, filepath: str) -> float:
        import re
        name = os.path.basename(str(filepath))
        match = re.search(r"-(\d+)-[Ss]_", name)
        if match:
            code = match.group(1).zfill(3)
            mapped = getattr(self.cfg, "strain_map", {}).get(code)
            if mapped is not None:
                return float(mapped)
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return np.nan

    def preprocess(self) -> bool:
        if self._q is not None and self._I is not None and self._img is None:
            from .saxs_engine import smooth_profile
            self._I_smooth = smooth_profile(self._q, self._I, self.cfg)
            self.result.raw_data["q"] = self._q
            self.result.raw_data["I"] = self._I
            self.result.raw_data["I_smooth"] = self._I_smooth
            self._publish_processed_profile(
                self._processed_profile_from_payload(
                    {"q": self._q, "Iq": self._I, "Iq_smooth": self._I_smooth},
                    source="static_1d_preprocess",
                )
            )
            self.log(f"1D data smoothed: {len(self._q)} points")
            return True

        if self._img is None:
            self.log("No image data loaded. Use load() first.")
            return False

        if self.config and hasattr(self.config, "saxs"):
            sc = self.config.saxs
            for attr in ["q_min", "q_max", "n_pt", "use_pyfai", "experiment_type"]:
                if hasattr(sc, attr):
                    setattr(self.cfg, attr, getattr(sc, attr))
        self._apply_submodule_defaults()

        pp = preprocess_pipeline(self._img, self.cfg)
        self._q = pp["q"]
        self._I = pp["Iq"]
        self._I_smooth = pp.get("Iq_smooth", self._I)
        self._I_merid = pp.get("Iq_merid_smooth")
        self._I_equat = pp.get("Iq_equat_smooth")
        self.result.raw_data["q"] = self._q
        self.result.raw_data["I"] = self._I
        self.result.raw_data["I_smooth"] = self._I_smooth
        self.result.raw_data["img"] = self._img
        self.result.raw_data["sector_data"] = pp.get("sector_data", {})
        self.result.metadata.update(pp.get("metadata", {}))
        self._publish_processed_profile(
            self._processed_profile_from_payload(pp, source="static_image_preprocess")
        )
        self.log(f"Preprocessed: q=[{self._q[0]:.3f}, {self._q[-1]:.3f}], n={len(self._q)}")
        return True

    def analyze(self) -> bool:
        self._apply_submodule_defaults()
        if getattr(self, "_condition_type", "") == "static" and self.cfg.experiment_type != "static":
            self._condition_type = self.cfg.experiment_type

        if self._q is None:
            self.log("No data. Run load() and preprocess() first.")
            return False

        has_multi = hasattr(self, "_q_list") and hasattr(self, "_I_list") and len(self._q_list) > 1
        if has_multi and self._condition_type == "temperature":
            return self._run_temperature_pipeline()
        if has_multi and self._condition_type == "strain":
            return self._run_strain_pipeline()
        return self._run_static_pipeline(has_multi)

    def _apply_batch_params_to_results(self) -> None:
        if not getattr(self, "_batch_results", None) or not getattr(self, "_batch_params", None):
            return

        def _num(value):
            try:
                if value is None:
                    return np.nan
                return float(value)
            except (TypeError, ValueError):
                return np.nan

        def _first_finite(*values):
            for value in values:
                number = _num(value)
                if np.isfinite(number):
                    return number
            return np.nan

        for index, (result, params) in enumerate(zip(self._batch_results, self._batch_params)):
            if not isinstance(params, dict):
                continue
            if result is None:
                self._batch_params[index] = dict(params)
                continue

            lp = result.long_period
            sp = result.structure
            raw_lp = replace(lp) if lp is not None else None
            raw_sp = replace(sp) if sp is not None else None
            result.raw_long_period = raw_lp
            result.raw_structure = raw_sp
            preserve_core_structure = str(getattr(self.cfg, "experiment_type", "") or "").lower() == "temperature"

            file_name = params.get("file")
            if file_name:
                result.label = os.path.splitext(str(file_name))[0]

            L = _num(params.get("L_nm"))
            lc = _first_finite(params.get("lc_nm"), params.get("lc_nm_calibrated"))
            la = _first_finite(params.get("la_nm"), params.get("la_nm_calibrated"))
            Xc = _first_finite(params.get("Xc"), params.get("Xc_calibrated"))
            lc_conf = _first_finite(params.get("lc_confidence"), params.get("lc_confidence_calibrated"))
            Q_star = _num(params.get("Q_star"))
            L_raw = _num(getattr(raw_lp, "L_best", np.nan) if raw_lp is not None else None)
            lc_raw = _num(getattr(raw_sp, "lc", np.nan) if raw_sp is not None else None)
            la_raw = _num(getattr(raw_sp, "la", np.nan) if raw_sp is not None else None)
            Xc_raw = _num(getattr(raw_sp, "phi_c", np.nan) if raw_sp is not None else None)
            lc_conf_raw = _num(getattr(raw_sp, "confidence_lc", np.nan) if raw_sp is not None else None)
            Q_star_raw = _num(getattr(raw_sp, "Q_invariant", np.nan) if raw_sp is not None else None)

            if not preserve_core_structure:
                if lp is not None and np.isfinite(L):
                    lp.L_best = L
                if raw_lp is not None and np.isfinite(L_raw):
                    raw_lp.L_best = L_raw
                if sp is not None:
                    if np.isfinite(L):
                        sp.L = L
                    if np.isfinite(lc):
                        sp.lc = lc
                    if np.isfinite(la):
                        sp.la = la
                    elif np.isfinite(L) and np.isfinite(lc):
                        sp.la = L - lc
                    if np.isfinite(Xc):
                        sp.phi_c = Xc
                    elif np.isfinite(L) and np.isfinite(lc) and L > 0:
                        sp.phi_c = lc / L
                    if np.isfinite(lc_conf):
                        sp.confidence_lc = lc_conf
                    if np.isfinite(Q_star):
                        sp.Q_invariant = Q_star
                if raw_sp is not None:
                    if np.isfinite(L_raw):
                        raw_sp.L = L_raw
                    elif raw_lp is not None and np.isfinite(getattr(raw_lp, "L_best", np.nan)):
                        raw_sp.L = raw_lp.L_best
                    if np.isfinite(lc_raw):
                        raw_sp.lc = lc_raw
                    if np.isfinite(la_raw):
                        raw_sp.la = la_raw
                    elif np.isfinite(raw_sp.L) and np.isfinite(lc_raw):
                        raw_sp.la = raw_sp.L - lc_raw
                    if np.isfinite(Xc_raw):
                        raw_sp.phi_c = Xc_raw
                    elif np.isfinite(raw_sp.L) and np.isfinite(lc_raw) and raw_sp.L > 0:
                        raw_sp.phi_c = lc_raw / raw_sp.L
                    if np.isfinite(lc_conf_raw):
                        raw_sp.confidence_lc = lc_conf_raw
                    if np.isfinite(Q_star_raw):
                        raw_sp.Q_invariant = Q_star_raw
            else:
                if lp is not None and np.isfinite(L_raw):
                    lp.L_best = L_raw
                if sp is not None:
                    if np.isfinite(L_raw):
                        sp.L = L_raw
                    if np.isfinite(lc_raw):
                        sp.lc = lc_raw
                    if np.isfinite(la_raw):
                        sp.la = la_raw
                    elif np.isfinite(sp.L) and np.isfinite(lc_raw):
                        sp.la = sp.L - lc_raw
                    if np.isfinite(Xc_raw):
                        sp.phi_c = Xc_raw
                    elif np.isfinite(sp.L) and np.isfinite(lc_raw) and sp.L > 0:
                        sp.phi_c = lc_raw / sp.L
                    if np.isfinite(lc_conf_raw):
                        sp.confidence_lc = lc_conf_raw
                    if np.isfinite(Q_star_raw):
                        sp.Q_invariant = Q_star_raw

            raw_snapshot: Dict[str, Any] = {}
            if raw_lp is not None:
                raw_snapshot["long_period"] = {
                    "L_best": getattr(raw_lp, "L_best", np.nan),
                    "L_confidence": getattr(raw_lp, "L_confidence", np.nan),
                    "L_bragg": getattr(raw_lp, "L_bragg", np.nan),
                    "L_lorentz": getattr(raw_lp, "L_lorentz", np.nan),
                    "L_corr_peak": getattr(raw_lp, "L_corr_peak", np.nan),
                    "method_used": getattr(raw_lp, "method_used", ""),
                }
            if raw_sp is not None:
                raw_snapshot["structure"] = {
                    "L": getattr(raw_sp, "L", np.nan),
                    "lc": getattr(raw_sp, "lc", np.nan),
                    "la": getattr(raw_sp, "la", np.nan),
                    "phi_c": getattr(raw_sp, "phi_c", np.nan),
                    "phi_c_invariant": getattr(raw_sp, "phi_c_invariant", np.nan),
                    "confidence_lc": getattr(raw_sp, "confidence_lc", np.nan),
                    "Q_invariant": getattr(raw_sp, "Q_invariant", np.nan),
                }
            result.raw_parameters = raw_snapshot
            if raw_snapshot:
                params["raw_snapshot"] = raw_snapshot
                params["raw_structure_available"] = True

            if np.isfinite(L_raw):
                params["L_nm_raw"] = round(L_raw, 2)
            if np.isfinite(lc_raw):
                params["lc_nm_raw"] = round(lc_raw, 2)
            if np.isfinite(la_raw):
                params["la_nm_raw"] = round(la_raw, 2)
            if np.isfinite(Xc_raw):
                params["Xc_raw"] = round(Xc_raw, 3)
            if np.isfinite(lc_conf_raw):
                params["lc_confidence_raw"] = round(lc_conf_raw, 2)
            if np.isfinite(Q_star_raw):
                params["Q_star_raw"] = round(Q_star_raw, 3)
            params.setdefault("raw_structure_available", bool(raw_snapshot))

            method_key = str(params.get("lc_method", "") or "").lower()
            calibrated_active = method_key in {"calibrated", "qstar_calibrated"}
            params["calibrated_fallback_active"] = calibrated_active
            if method_key == "qstar_calibrated":
                params["calibrated_fallback_reason"] = "temperature_batch_qstar_calibration"
                params["fallback_applied_fields"] = ["lc_nm_calibrated", "la_nm_calibrated", "Xc_calibrated", "lc_confidence_calibrated"]
            elif method_key == "calibrated":
                params["calibrated_fallback_reason"] = "temperature_batch_lc_calibration"
                params["fallback_applied_fields"] = ["lc_nm_calibrated", "la_nm_calibrated", "Xc_calibrated", "lc_confidence_calibrated"]
            elif method_key == "sasmodels":
                params["calibrated_fallback_reason"] = "sasmodels_fit"
                params["fallback_applied_fields"] = ["lc_nm", "la_nm", "Xc"]
            elif method_key == "sasmodels_failed":
                params["calibrated_fallback_reason"] = "sasmodels_fallback_to_raw"
                params["fallback_applied_fields"] = ["raw_structure"]
            elif method_key == "raw":
                params["calibrated_fallback_reason"] = "raw_value_retained"
                params["fallback_applied_fields"] = []
            else:
                params["calibrated_fallback_reason"] = method_key or "unspecified"
                params.setdefault("fallback_applied_fields", [])

            result.raw_parameters = dict(raw_snapshot)
            result.final_parameters = dict(params)
            self._batch_params[index] = dict(params)

    def _reference_crystallinity(self) -> tuple[float | None, str]:
        try:
            ref_xc = float(getattr(self.cfg, "crystallinity", np.nan))
        except (TypeError, ValueError):
            ref_xc = np.nan
        if np.isfinite(ref_xc) and 0 < ref_xc < 1:
            return ref_xc, ""
        return None, "missing_reference_crystallinity"

    def _condition_row_metadata(self, index: int) -> Dict[str, Any]:
        source = self._condition_sources[index] if index < len(self._condition_sources) else ""
        source_key = self._condition_source_keys[index] if index < len(self._condition_source_keys) else ""
        source_text = self._condition_source_texts[index] if index < len(self._condition_source_texts) else ""
        confidence = self._condition_confidences[index] if index < len(self._condition_confidences) else np.nan
        payload: Dict[str, Any] = {}
        if source:
            payload["condition_source"] = source
        if source_key:
            payload["condition_source_key"] = source_key
        if source_text:
            payload["condition_source_text"] = source_text
        if np.isfinite(confidence):
            payload["condition_confidence"] = round(float(confidence), 2)
        return payload

    def _strain_phase_support_score(
        self,
        phase_name: str,
        q_rel: float | None,
        has_voids: bool,
        f_herman: float | None,
        porod_slope: float | None,
    ) -> float:
        phase_key = str(phase_name or "").strip().upper()
        terms: list[float] = []
        if phase_key == "ELASTIC":
            if q_rel is not None and np.isfinite(q_rel):
                terms.append(1.0 if abs(q_rel - 1.0) <= 0.04 else 0.55)
            terms.append(0.95 if not has_voids else 0.25)
            if porod_slope is not None and np.isfinite(porod_slope):
                terms.append(1.0 if porod_slope <= -3.6 else 0.55)
        elif phase_key == "PLASTIC_VOIDING":
            terms.append(1.0 if has_voids else 0.45)
            if q_rel is not None and np.isfinite(q_rel):
                terms.append(1.0 if q_rel >= 1.0 else 0.55)
            if porod_slope is not None and np.isfinite(porod_slope):
                terms.append(1.0 if porod_slope > -3.6 else 0.5)
        elif phase_key == "MICROFIBRILLATION":
            if f_herman is not None and np.isfinite(f_herman):
                terms.append(1.0 if abs(f_herman) >= 0.15 else 0.5)
            if q_rel is not None and np.isfinite(q_rel):
                terms.append(1.0 if q_rel >= 1.02 else 0.55)
            if porod_slope is not None and np.isfinite(porod_slope):
                terms.append(1.0 if porod_slope > -3.7 else 0.5)
        elif phase_key == "FRACTURE":
            if q_rel is not None and np.isfinite(q_rel):
                terms.append(1.0 if q_rel < 0.65 else 0.45)
            terms.append(1.0 if has_voids else 0.5)
            if porod_slope is not None and np.isfinite(porod_slope):
                terms.append(1.0 if porod_slope > -3.7 else 0.55)
        else:
            if q_rel is not None and np.isfinite(q_rel):
                terms.append(0.7 if abs(q_rel - 1.0) <= 0.08 else 0.45)
            terms.append(0.6 if not has_voids else 0.4)
            if f_herman is not None and np.isfinite(f_herman):
                terms.append(0.7 if abs(f_herman) >= 0.10 else 0.5)

        finite_terms = [float(term) for term in terms if term is not None and np.isfinite(term)]
        if not finite_terms:
            return 0.5
        return float(np.clip(np.mean(finite_terms), 0.0, 1.0))

    def _strain_reliability_profile(
        self,
        *,
        strain_pct: float | None,
        condition_confidence: float | None,
        q_rel: float | None,
        q_star_valid: bool,
        has_voids: bool,
        phase_name: str,
        f_herman: float | None,
        porod_slope: float | None,
    ) -> tuple[str, str, bool, bool, bool]:
        reason_bits: list[str] = []
        status = "usable"

        strain_missing = strain_pct is None or not np.isfinite(strain_pct)
        if strain_missing:
            status = "diagnostic_only"
            reason_bits.append("condition_axis_missing")
        elif condition_confidence is None or not np.isfinite(condition_confidence):
            status = "low_confidence"
            reason_bits.append("strain_axis_low_confidence")
        elif condition_confidence < 0.55:
            status = "diagnostic_only"
            reason_bits.append("strain_axis_low_confidence")
        elif condition_confidence < 0.75:
            status = "low_confidence"
            reason_bits.append("strain_axis_low_confidence")

        if not q_star_valid:
            if status == "usable":
                status = "low_confidence"
            reason_bits.append("qstar_rel_without_lamellar_support")

        if has_voids or (porod_slope is not None and np.isfinite(porod_slope) and porod_slope > -3.5):
            if "low_q_void_dominant" not in reason_bits:
                reason_bits.append("low_q_void_dominant")
            if status == "usable":
                status = "low_confidence"
            if condition_confidence is None or condition_confidence < 0.65:
                status = "diagnostic_only"

        if q_rel is not None and np.isfinite(q_rel) and q_rel < 0.8:
            if "lamellar_anchor_lost_under_strain" not in reason_bits:
                reason_bits.append("lamellar_anchor_lost_under_strain")
            if status == "usable":
                status = "low_confidence"

        phase_key = str(phase_name or "").strip().upper()
        if phase_key == "FRACTURE":
            if "phase_ambiguous" not in reason_bits:
                reason_bits.append("phase_ambiguous")
            if status == "usable":
                status = "low_confidence"

        if phase_key == "MICROFIBRILLATION" and f_herman is not None and np.isfinite(f_herman) and abs(f_herman) < 0.08:
            if "orientation_shift_breaks_lamellar_comparison" not in reason_bits:
                reason_bits.append("orientation_shift_breaks_lamellar_comparison")
            if status == "usable":
                status = "low_confidence"

        if phase_key == "PLASTIC_VOIDING" and has_voids and q_rel is not None and np.isfinite(q_rel) and q_rel > 1.12:
            if "strain_void_lamellar_conflict" not in reason_bits:
                reason_bits.append("strain_void_lamellar_conflict")

        if q_rel is not None and np.isfinite(q_rel) and phase_key == "ELASTIC" and abs(q_rel - 1.0) > 0.08:
            if "phase_ambiguous" not in reason_bits:
                reason_bits.append("phase_ambiguous")
            if status == "usable":
                status = "low_confidence"

        if not reason_bits:
            reason_bits.append("stable_structure_support")

        phase_support_score = self._strain_phase_support_score(phase_key, q_rel, has_voids, f_herman, porod_slope)
        phase_ambiguous = phase_support_score < 0.55 or "phase_ambiguous" in reason_bits
        paper_figure_candidate = bool(
            status != "diagnostic_only"
            and q_star_valid
            and phase_support_score >= 0.50
            and (q_rel is None or np.isfinite(q_rel))
        )
        paper_conclusion_candidate = bool(
            status == "usable"
            and q_star_valid
            and phase_support_score >= 0.68
            and not has_voids
            and (q_rel is None or (np.isfinite(q_rel) and 0.88 <= q_rel <= 1.15))
            and phase_key in {"ELASTIC", "PLASTIC_VOIDING", "MICROFIBRILLATION"}
        )
        if not paper_figure_candidate and paper_conclusion_candidate:
            paper_figure_candidate = True

        return (
            status,
            "|".join(dict.fromkeys(reason_bits)),
            paper_figure_candidate,
            paper_conclusion_candidate,
            phase_ambiguous,
        )

    def _build_batch_parameters_payload(
        self,
        base_params: Optional[Dict[str, Any]] = None,
        *,
        batch_params: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return _saxs_batch_helpers._build_batch_parameters_payload(
            getattr(self, "_batch_params", []) if batch_params is None else batch_params,
            base_params=base_params,
            experiment_type=str(getattr(self.cfg, "experiment_type", "") or ""),
        )


    def _run_temperature_pipeline(self) -> bool:
        temps_valid = [float(v) for v in self._conditions if np.isfinite(v)]
        if temps_valid:
            self.log(f"Temperature series: {len(self._q_list)} frames, T=[{min(temps_valid):.0f},{max(temps_valid):.0f}]C")
        else:
            self.log(f"Temperature series: {len(self._q_list)} frames, T=[unresolved]")

        self._batch_results = []
        L_values = []
        _prev_q_star = None

        for i in range(len(self._q_list)):
            try:
                analysis = analyze_single(self._q_list[i], self._I_list[i], self.cfg, q_anchor=_prev_q_star)
                analysis.condition_value = self._conditions[i] if i < len(self._conditions) else np.nan
                lp = analysis.long_period
                if lp is not None and np.isfinite(lp.L_best) and lp.L_best > 0:
                    _prev_q_star = 2 * np.pi / lp.L_best
                self._batch_results.append(analysis)
                L_values.append(float(lp.L_best) if lp and np.isfinite(lp.L_best) else np.nan)
            except Exception as e:
                self.log(f"Frame {i} failed: {e}")
                self._batch_results.append(None)
                L_values.append(np.nan)
                logger.warning("SAXS temperature frame analysis failed.", exc_info=True)

        temps = np.array(self._conditions, dtype=float)
        L_arr = np.array(L_values, dtype=float)
        valid = np.isfinite(temps) & np.isfinite(L_arr) & (L_arr > 0)
        self._temperature_result = None
        temp_points_by_source: Dict[int, Any] = {}

        try:
            temp_result = analyze_temperature_series(
                temperatures=list(temps),
                q_list=self._q_list,
                I_list=self._I_list,
                cfg=self.cfg,
            )
        except Exception as exc:
            self.log(f"Temperature window analysis skipped: {exc}")
            logger.warning("Failed to derive temperature-series statuses.", exc_info=True)
        else:
            self._temperature_result = temp_result
            self._results = list(getattr(temp_result, "temp_points", []))
            temp_points_by_source = {
                int(tp.source_index): tp
                for tp in getattr(temp_result, "temp_points", [])
                if isinstance(getattr(tp, "source_index", None), (int, np.integer))
            }

        def _temperature_status_payload(index: int) -> Dict[str, Any]:
            tp = temp_points_by_source.get(index)
            if tp is None:
                return {
                    "melting_window_status": "undetermined",
                    "melting_window_reason": "temperature_series_status_unavailable",
                    "lc_reliability_status": "diagnostic_only",
                    "lc_reliability_reason": "temperature_series_status_unavailable",
                    "lc_path_status": "diagnostic_only",
                    "lc_path_reason": "temperature_series_status_unavailable",
                    "lc_candidate_selected_nm": np.nan,
                    "lc_candidate_selected_source": "",
                    "lc_candidate_selected_score": np.nan,
                    "lc_candidate_count": 0,
                    "lc_effective_nm": np.nan,
                    "lc_effective_source": "",
                    "lc_effective_score": np.nan,
                }
            candidate_count = _float_or_none(getattr(tp, "lc_candidate_count", np.nan))
            return {
                "melting_window_status": str(getattr(tp, "melting_window_status", "") or "undetermined"),
                "melting_window_reason": str(getattr(tp, "melting_window_reason", "") or "temperature_series_status_unavailable"),
                "lc_reliability_status": str(getattr(tp, "lc_reliability_status", "") or "diagnostic_only"),
                "lc_reliability_reason": str(getattr(tp, "lc_reliability_reason", "") or "temperature_series_status_unavailable"),
                "lc_path_status": str(getattr(tp, "lc_path_status", "") or ""),
                "lc_path_reason": str(getattr(tp, "lc_path_reason", "") or ""),
                "lc_candidate_selected_nm": _float_or_none(getattr(tp, "lc_candidate_selected_nm", np.nan)),
                "lc_candidate_selected_source": str(getattr(tp, "lc_candidate_selected_source", "") or ""),
                "lc_candidate_selected_score": _float_or_none(getattr(tp, "lc_candidate_selected_score", np.nan)),
                "lc_candidate_count": int(candidate_count) if candidate_count is not None and np.isfinite(candidate_count) else 0,
                "lc_effective_nm": _float_or_none(getattr(tp, "lc_effective_nm", np.nan)),
                "lc_effective_source": str(getattr(tp, "lc_effective_source", "") or ""),
                "lc_effective_score": _float_or_none(getattr(tp, "lc_effective_score", np.nan)),
            }

        def _temperature_effective_structure_payload(
            *,
            L_nm: float | None,
            lc_raw: float | None,
            la_raw: float | None,
            Xc_raw: float | None,
            status_payload: Dict[str, Any],
        ) -> Dict[str, Any]:
            path_status = str(status_payload.get("lc_path_status") or "").strip().lower()
            path_reason = str(status_payload.get("lc_path_reason") or "").strip()
            lc_effective = _float_or_none(status_payload.get("lc_effective_nm"))
            lc_status = str(status_payload.get("lc_reliability_status") or "").strip().lower()
            lc_reason = str(status_payload.get("lc_reliability_reason") or "").strip()
            if path_status:
                if path_status in {"diagnostic_only", "no_path"} or not np.isfinite(lc_effective):
                    return {
                        "lc_nm": None,
                        "la_nm": None,
                        "Xc": None,
                        "lc_nm_effective": None,
                        "la_nm_effective": None,
                        "Xc_effective": None,
                        "lamellar_interpretation_mode": "sequence_path_diagnostic_only" if path_status == "diagnostic_only" else "sequence_path_none",
                        "effective_param_reason": path_reason or "lc_path_diagnostic_only",
                    }
                if np.isfinite(L_nm) and L_nm > 0:
                    la_effective = round(float(L_nm) - float(lc_effective), 2)
                    Xc_effective = round(float(lc_effective) / float(L_nm), 3)
                else:
                    la_effective = None
                    Xc_effective = None
                mode = "sequence_path_usable" if path_status == "usable" else "sequence_path_low_confidence" if path_status == "low_confidence" else "sequence_path_selected"
                return {
                    "lc_nm": lc_effective,
                    "la_nm": la_effective,
                    "Xc": Xc_effective,
                    "lc_nm_effective": lc_effective,
                    "la_nm_effective": la_effective,
                    "Xc_effective": Xc_effective,
                    "lamellar_interpretation_mode": mode,
                    "effective_param_reason": path_reason or "sequence_path_selected",
                }

            if lc_status == "diagnostic_only":
                return {
                    "lc_nm": None,
                    "la_nm": None,
                    "Xc": None,
                    "lc_nm_effective": None,
                    "la_nm_effective": None,
                    "Xc_effective": None,
                    "lamellar_interpretation_mode": "diagnostic_only",
                    "effective_param_reason": lc_reason or "lc_reliability_diagnostic_only",
                }
            mode = "raw_low_confidence" if lc_status == "low_confidence" else "raw_measurement"
            reason = "lc_reliability_low_confidence" if lc_status == "low_confidence" else "raw_structure_measurement_retained"
            return {
                "lc_nm": lc_raw,
                "la_nm": la_raw,
                "Xc": Xc_raw,
                "lc_nm_effective": lc_raw,
                "la_nm_effective": la_raw,
                "Xc_effective": Xc_raw,
                "lamellar_interpretation_mode": mode,
                "effective_param_reason": reason,
            }

        self._batch_params = []
        if np.sum(valid) >= 2:
            ref_idx = int(np.argmin(temps[valid]))
            L_ref = L_arr[valid][ref_idx]
            ref_Xc, skip_reason = self._reference_crystallinity()
            lc_cal = round(ref_Xc * L_ref, 2) if ref_Xc is not None else None
            if lc_cal is not None:
                self.log(f"lc calibrated: {lc_cal}nm (Xc_ref={ref_Xc:.2f} L_ref={L_ref:.1f})")
            else:
                self.log("Temperature lc calibration skipped: missing reference crystallinity")
            for i in range(len(self._q_list)):
                analysis = self._batch_results[i] if i < len(self._batch_results) else None
                sp = analysis.structure if analysis else None
                L = round(L_arr[i], 2) if np.isfinite(L_arr[i]) else None
                T = round(float(temps[i]), 1) if i < len(temps) and np.isfinite(temps[i]) else None
                fname = self._file_list[i] if i < len(self._file_list) else f"frame_{i}"
                lc_raw = round(float(sp.lc), 2) if sp and np.isfinite(sp.lc) else None
                la_raw = round(float(sp.la), 2) if sp and np.isfinite(sp.la) else None
                Xc_raw = round(float(sp.phi_c), 3) if sp and np.isfinite(sp.phi_c) else None
                lcc_raw = round(float(sp.confidence_lc), 2) if sp and np.isfinite(sp.confidence_lc) else None
                status_payload = _temperature_status_payload(i)
                effective_payload = _temperature_effective_structure_payload(
                    L_nm=L,
                    lc_raw=lc_raw,
                    la_raw=la_raw,
                    Xc_raw=Xc_raw,
                    status_payload=status_payload,
                )
                row = {
                    "file": os.path.basename(str(fname)),
                    "condition_label": getattr(self.cfg, "condition_label", "Temperature"),
                    "temperature_C": T,
                    "L_nm": L,
                    "lc_nm_raw": lc_raw,
                    "la_nm_raw": la_raw,
                    "Xc_raw": Xc_raw,
                    **effective_payload,
                    "lc_confidence": lcc_raw,
                    "lc_method": "calibrated" if lc_cal is not None else "raw",
                    "Q_star_valid": True,
                    "porod_slope": round(float(analysis.porod.get("slope")), 4) if analysis and isinstance(getattr(analysis, "porod", None), dict) and np.isfinite(_float_or_none(analysis.porod.get("slope"))) else None,
                    **status_payload,
                    **self._condition_row_metadata(i),
                }
                if lc_cal is not None:
                    row.update({
                        "lc_nm_calibrated": lc_cal,
                        "la_nm_calibrated": round(L - lc_cal, 2) if L and L > 0 else None,
                        "Xc_calibrated": round(lc_cal / L, 3) if L and L > 0 else None,
                        "lc_confidence_calibrated": 0.50,
                    })
                else:
                    row["calibration_skipped_reason"] = skip_reason
                self._batch_params.append(row)
        else:
            self.log("Not enough valid frames for lc calibration - using raw values")
            for i in range(len(self._q_list)):
                a = self._batch_results[i] if i < len(self._batch_results) else None
                sp = a.structure if a else None
                lp = a.long_period if a else None
                L = round(float(lp.L_best), 2) if lp and np.isfinite(lp.L_best) else None
                lc = round(float(sp.lc), 2) if sp and np.isfinite(sp.lc) else None
                la = round(float(sp.la), 2) if sp and np.isfinite(sp.la) else None
                pc = round(float(sp.phi_c), 3) if sp and np.isfinite(sp.phi_c) else None
                fn = self._file_list[i] if i < len(self._file_list) else f"frame_{i}"
                lcc = round(float(sp.confidence_lc), 2) if sp and np.isfinite(sp.confidence_lc) else None
                status_payload = _temperature_status_payload(i)
                effective_payload = _temperature_effective_structure_payload(
                    L_nm=L,
                    lc_raw=lc,
                    la_raw=la,
                    Xc_raw=pc,
                    status_payload=status_payload,
                )
                self._batch_params.append({
                    "file": os.path.basename(str(fn)),
                    "condition_label": getattr(self.cfg, "condition_label", "Temperature"),
                    "temperature_C": self._conditions[i] if i < len(self._conditions) else None,
                    "L_nm": L,
                    "lc_nm_raw": lc,
                    "la_nm_raw": la,
                    "Xc_raw": pc,
                    **effective_payload,
                    "lc_confidence": lcc,
                    "lc_method": "raw",
                    **status_payload,
                    **self._condition_row_metadata(i),
                })

        self._apply_batch_params_to_results()
        self.log(f"Temperature: {len(self._batch_params)} frames done")
        return len(self._batch_params) > 0

    def _run_strain_pipeline(self) -> bool:
        has_equat = (
            hasattr(self, "_I_equat_list")
            and len(self._I_equat_list) == len(self._q_list)
            and any(x is not None for x in self._I_equat_list)
        )
        I_use = [
            self._I_equat_list[i] if (has_equat and self._I_equat_list[i] is not None) else self._I_list[i]
            for i in range(len(self._q_list))
        ]

        self.log(f"Strain series: {len(self._q_list)} frames, equatorial={'yes' if has_equat else 'no (fallback)'}")

        strain_cfg = replace(self.cfg)
        strain_cfg.q_bragg_max = max(strain_cfg.q_bragg_max, 1.3)

        self._batch_results = []
        self._batch_params = []
        self._strain_result = None
        _prev_q_star = None
        Q_ref = None
        Xc_ref_tangent = None

        try:
            finite_strains = [float(v) for v in np.asarray(self._conditions, dtype=float) if np.isfinite(v)]
            if len(finite_strains) >= 2:
                self._strain_result = analyze_strain_series(
                    strains=list(self._conditions),
                    q_list=self._q_list,
                    I_list=I_use,
                    cfg=replace(strain_cfg),
                )
        except Exception:
            logger.warning("Failed to derive tensile SAXS strain-series evidence.", exc_info=True)

        for i in range(len(self._q_list)):
            try:
                q_pf = self._q_pyfai_list[i] if i < len(self._q_pyfai_list) else np.array([])
                I_pf = self._I_pyfai_list[i] if i < len(self._I_pyfai_list) else np.array([])
                analysis = analyze_single(
                    self._q_list[i], I_use[i], strain_cfg, q_anchor=_prev_q_star,
                    q_pyfai=(q_pf if len(q_pf) > 0 else None),
                    I_pyfai=(I_pf if len(I_pf) > 0 else None),
                )
                analysis.condition_value = self._conditions[i] if i < len(self._conditions) else np.nan
                lp = analysis.long_period
                self._batch_results.append(analysis)
                sp = analysis.structure
                L_bragg = lp.L_bragg if np.isfinite(lp.L_bragg) else lp.L_best
                if np.isfinite(L_bragg) and L_bragg > 0:
                    _prev_q_star = 2 * np.pi / L_bragg
                L = round(float(L_bragg), 2) if np.isfinite(L_bragg) else None

                lc_tangent = None
                if sp is not None:
                    lct = getattr(sp, "lc_tangent_nm", np.nan)
                    if np.isfinite(lct) and L and 0 < lct < L * 0.7:
                        lc_tangent = round(float(lct), 2)

                lc_raw, la_raw, phi_raw, method, model_used, sas_r2 = self._try_sasmodels_lc(
                    self._q_list[i], I_use[i], L_bragg, sp
                )

                q = self._q_list[i]
                Ii = I_use[i]
                q_min_inv = max(getattr(strain_cfg, "q_min", 0.08), 0.06)
                q_max_inv = min(getattr(strain_cfg, "q_bragg_max", 1.3), q[-1]) if len(q) > 0 else 1.3
                Q_raw = scattering_invariant(q, Ii, q_min=q_min_inv, q_max=q_max_inv)

                if i == 0:
                    Q_ref = Q_raw if (Q_raw and Q_raw > 0) else None
                    if lc_tangent is not None and L and L > 0:
                        Xc_ref_tangent = round(lc_tangent / L, 4)

                Q_rel = round(float(Q_raw) / float(Q_ref), 4) if Q_ref and Q_raw and Q_ref > 0 else None

                if method == "sasmodels":
                    lc, la, phi_c = lc_raw, la_raw, phi_raw
                    method_out = "sasmodels"
                    lc_c = 0.70
                elif lc_tangent is not None and L and L > 0:
                    lc = lc_tangent
                    la = round(L - lc, 2)
                    Xc_t = round(lc / L, 4)
                    phi_c = round(Xc_t, 3)
                    if Q_rel is None or abs(Q_rel - 1.0) <= 0.08:
                        method_out = "tangent_strain"
                        lc_c = 0.50
                    elif Q_rel > 0.40:
                        method_out = "tangent_strain_qstar_warn"
                        lc_c = 0.35
                    else:
                        method_out = "tangent_strain_low_qstar"
                        lc_c = 0.20
                elif lc_raw is not None and np.isfinite(lc_raw):
                    lc, la, phi_c = lc_raw, la_raw, phi_raw
                    method_out = "sasmodels" if method == "sasmodels" else "fallback"
                    lc_c = 0.30
                else:
                    lc = la = phi_c = None
                    method_out = "raw"
                    lc_c = 0.10

                if method_out == "sasmodels":
                    interpretation_mode = "sasmodels_fit"
                    effective_reason = "sasmodels fit passed the strain gate"
                elif method_out == "tangent_strain":
                    interpretation_mode = "tangent_effective"
                    effective_reason = "tangent thickness anchored to the strain long period"
                elif method_out == "tangent_strain_qstar_warn":
                    interpretation_mode = "tangent_effective_warn"
                    effective_reason = "tangent thickness accepted but Q* drift needs review"
                elif method_out == "tangent_strain_low_qstar":
                    interpretation_mode = "tangent_effective_low_qstar"
                    effective_reason = "tangent thickness accepted with low-Q* caution"
                elif method_out == "sasmodels_failed":
                    interpretation_mode = "raw_fallback"
                    effective_reason = "sasmodels fit failed and raw structure was retained"
                else:
                    interpretation_mode = "raw_measurement"
                    effective_reason = "no stronger effective interpretation was available"

                porod_slope = None
                if analysis is not None and isinstance(getattr(analysis, "porod", None), dict):
                    porod_slope = _float_or_none(analysis.porod.get("slope"))
                strain_point = None
                if self._strain_result is not None and i < len(getattr(self._strain_result, "strain_points", [])):
                    strain_point = self._strain_result.strain_points[i]
                phase_name = str(getattr(getattr(strain_point, "phase", None), "name", "") or "").strip().upper()
                if not phase_name:
                    phase_name = "ELASTIC"
                has_voids_proxy = bool(
                    (porod_slope is not None and np.isfinite(porod_slope) and porod_slope > -3.5)
                    or (Q_rel is not None and np.isfinite(Q_rel) and Q_rel > 1.08 and phase_name in {"PLASTIC_VOIDING", "MICROFIBRILLATION"})
                )
                phase_support_score = self._strain_phase_support_score(
                    phase_name,
                    Q_rel,
                    has_voids_proxy,
                    None,
                    porod_slope,
                )
                strain_axis_confidence = self._condition_confidences[i] if i < len(self._condition_confidences) else np.nan
                strain_reliability_status, strain_reliability_reason, paper_figure_candidate, paper_conclusion_candidate, phase_ambiguous = self._strain_reliability_profile(
                    strain_pct=self._conditions[i] if i < len(self._conditions) else None,
                    condition_confidence=float(strain_axis_confidence) if np.isfinite(strain_axis_confidence) else None,
                    q_rel=Q_rel,
                    q_star_valid=bool(Q_rel is None or Q_rel >= 0.3),
                    has_voids=has_voids_proxy,
                    phase_name=phase_name,
                    f_herman=None,
                    porod_slope=porod_slope,
                )

                fname = self._file_list[i] if i < len(self._file_list) else f"frame_{i}"
                self._batch_params.append({
                    "file": os.path.basename(str(fname)),
                    "condition_label": getattr(self.cfg, "condition_label", "Strain"),
                    "strain_pct": self._conditions[i] if i < len(self._conditions) else None,
                    "L_nm": L,
                    "L_nm_measured": L,
                    "Q_star_abs": round(float(Q_raw), 3) if np.isfinite(Q_raw) else None,
                    "Q_star_rel": Q_rel,
                    "lc_nm_raw": round(float(lc_raw), 2) if np.isfinite(lc_raw) else None,
                    "la_nm_raw": round(float(la_raw), 2) if np.isfinite(la_raw) else None,
                    "Xc_raw": round(float(phi_raw), 3) if np.isfinite(phi_raw) else None,
                    "lc_nm": lc,
                    "la_nm": la,
                    "Xc": phi_c,
                    "Q_star": round(float(Q_raw), 3) if np.isfinite(Q_raw) else None,
                    "Q_rel": Q_rel,
                    "lc_nm_effective": lc,
                    "la_nm_effective": la,
                    "Xc_effective": phi_c,
                    "lamellar_interpretation_mode": interpretation_mode,
                    "effective_param_reason": effective_reason,
                    "lc_confidence": lc_c,
                    "lc_method": method_out,
                    "sasmodels_method": model_used,
                    "sasmodels_R2": round(float(sas_r2), 4) if np.isfinite(sas_r2) else None,
                    "Q_star_valid": bool(Q_rel is None or Q_rel >= 0.3),
                    "porod_slope": round(float(porod_slope), 4) if porod_slope is not None else None,
                    "strain_phase": phase_name.lower() if phase_name else None,
                    "phase_name": phase_name.lower() if phase_name else None,
                    "phase_support_score": round(float(phase_support_score), 3),
                    "phase_ambiguous": bool(phase_ambiguous),
                    "strain_reliability_status": strain_reliability_status,
                    "strain_reliability_reason": strain_reliability_reason,
                    "paper_figure_candidate": bool(paper_figure_candidate),
                    "paper_conclusion_candidate": bool(paper_conclusion_candidate),
                    "paper_conclusion_ready": bool(paper_conclusion_candidate),
                    **self._condition_row_metadata(i),
                })
            except Exception as e:
                self.log(f"Frame {i} failed: {e}")
                logger.warning("SAXS tensile frame parameter extraction failed.", exc_info=True)

        self._apply_batch_params_to_results()
        self.log(f"Strain: {len(self._batch_params)} frames done")
        return len(self._batch_params) > 0

    def _try_sasmodels_lc(self, q, I, L_bragg, sp):
        if not getattr(self.cfg, "use_sasmodels_fit", False):
            return (
                round(float(sp.lc), 2) if sp and np.isfinite(sp.lc) else None,
                round(float(sp.la), 2) if sp and np.isfinite(sp.la) else None,
                round(float(sp.phi_c), 3) if sp and np.isfinite(sp.phi_c) else None,
                "raw",
                "",
                np.nan,
            )
        try:
            from .saxs_engine.core import sasmodels_fit_with_fallback
            fit = sasmodels_fit_with_fallback(q, I, L_bragg_guess=L_bragg)
            r2 = fit.get("R2", np.nan)
            model_used = fit.get("model_used", "")
            if np.isfinite(r2) and r2 >= 0.5:
                lc_s = fit.get("lc_nm")
                la_s = fit.get("la_nm")
                Xc_s = fit.get("Xc")
                L_s = fit.get("L_nm")
                if all(np.isfinite(v) for v in [lc_s, la_s, Xc_s, L_s]):
                    if 0.05 < lc_s / L_s < 0.95 and 0.05 < la_s / L_s < 0.95:
                        return round(float(lc_s), 2), round(float(la_s), 2), round(float(Xc_s), 3), "sasmodels", model_used, round(float(r2), 4)
            return (
                round(float(sp.lc), 2) if sp and np.isfinite(sp.lc) else None,
                round(float(sp.la), 2) if sp and np.isfinite(sp.la) else None,
                round(float(sp.phi_c), 3) if sp and np.isfinite(sp.phi_c) else None,
                "sasmodels_failed",
                model_used,
                round(float(r2), 4) if np.isfinite(r2) else np.nan,
            )
        except Exception:
            logger.warning("SAXS sasmodels lamellar fit failed; using raw parameters.", exc_info=True)
        return (
            round(float(sp.lc), 2) if sp and np.isfinite(sp.lc) else None,
            round(float(sp.la), 2) if sp and np.isfinite(sp.la) else None,
            round(float(sp.phi_c), 3) if sp and np.isfinite(sp.phi_c) else None,
            "raw",
            "",
            np.nan,
        )

    def _run_static_pipeline(self, has_multi: bool = False) -> bool:
        if has_multi:
            self.log(f"Static batch: {len(self._q_list)} frames")
            self._batch_results = []
            Q_values = []

            for i in range(len(self._q_list)):
                try:
                    q_pf_s = self._q_pyfai_list[i] if i < len(self._q_pyfai_list) else np.array([])
                    I_pf_s = self._I_pyfai_list[i] if i < len(self._I_pyfai_list) else np.array([])
                    analysis = analyze_single(
                        self._q_list[i], self._I_list[i], self.cfg,
                        q_pyfai=(q_pf_s if len(q_pf_s) > 0 else None),
                        I_pyfai=(I_pf_s if len(I_pf_s) > 0 else None),
                    )
                    analysis.condition_value = self._conditions[i] if i < len(self._conditions) else np.nan
                    self._batch_results.append(analysis)
                    sp = analysis.structure
                    Q_values.append(sp.Q_invariant if sp and np.isfinite(sp.Q_invariant) else np.nan)
                except Exception as e:
                    self.log(f"Frame {i} failed: {e}")
                    self._batch_results.append(None)
                    Q_values.append(np.nan)
                    logger.warning("SAXS static frame analysis failed.", exc_info=True)

            ref_idx = None
            for i, fpath in enumerate(self._file_list):
                fname = os.path.basename(str(fpath)).upper()
                if "PA6" in fname and "C401" not in fname:
                    ref_idx = i
                    break
            if ref_idx is None and len(Q_values) > 0:
                ref_idx = 0

            ref_Xc, skip_reason = self._reference_crystallinity()
            ref_analysis = self._batch_results[ref_idx] if ref_idx is not None and ref_idx < len(self._batch_results) else None
            ref_lp = ref_analysis.long_period if ref_analysis is not None else None
            L_ref = (
                ref_lp.L_bragg
                if ref_lp is not None and np.isfinite(ref_lp.L_bragg)
                else (ref_lp.L_best if ref_lp is not None else np.nan)
            )
            if ref_Xc is not None and (not np.isfinite(L_ref) or L_ref <= 0):
                skip_reason = "invalid_reference_long_period"
            lc_cal = round(ref_Xc * L_ref, 2) if ref_Xc is not None and np.isfinite(L_ref) and L_ref > 0 else None
            Q_ref = Q_values[ref_idx] if ref_idx is not None and ref_idx < len(Q_values) and np.isfinite(Q_values[ref_idx]) else None

            C_ref = None
            if lc_cal is not None:
                self.log(f"Static lc calibrated: ref lc={lc_cal}nm (Xc_ref={ref_Xc:.2f} L_ref={L_ref:.1f} from frame {ref_idx})")
                C_ref = ref_Xc * (1.0 - ref_Xc)
            else:
                self.log(f"Static lc calibration skipped: {skip_reason or 'unavailable_reference'}")

            self._batch_params = []
            for i in range(len(self._q_list)):
                analysis = self._batch_results[i] if i < len(self._batch_results) else None
                lp = analysis.long_period if analysis else None
                sp = analysis.structure if analysis else None
                L_bragg = lp.L_bragg if lp and np.isfinite(lp.L_bragg) else (lp.L_best if lp else np.nan)
                L = round(float(L_bragg), 2) if np.isfinite(L_bragg) else None
                lc, la, phi_c, method, model_used, sas_r2 = self._try_sasmodels_lc(self._q_list[i], self._I_list[i], L_bragg, sp)
                Q_star = Q_values[i] if i < len(Q_values) else None
                Q_rel = round(float(Q_star) / float(Q_ref), 4) if Q_ref is not None and Q_star is not None and Q_ref > 0 and np.isfinite(Q_star) else None
                fname = self._file_list[i] if i < len(self._file_list) else f"frame_{i}"

                if method == "sasmodels":
                    lc_conf = 0.70
                    lc_out, la_out, Xc_out = lc, la, phi_c
                elif lc_cal is not None and C_ref is not None and L and L > 0 and Q_rel is not None:
                    C_i = Q_rel * C_ref
                    disc = 1.0 - 4.0 * C_i
                    Xc_q = (1.0 - disc ** 0.5) / 2.0 if disc >= 0 else np.nan
                    if np.isfinite(Xc_q) and 0 < Xc_q < 0.5:
                        lc_q = round(Xc_q * L, 2)
                        la_q = round(L - lc_q, 2)
                        Xc_q_r = round(Xc_q, 3)
                        lc_out, la_out, Xc_out = lc_q, la_q, Xc_q_r
                        method = "Qstar_calibrated"
                        lc_conf = 0.45
                    else:
                        Xc_cal = round(lc_cal / L, 3)
                        la_cal = round(L - lc_cal, 2)
                        lc_out, la_out, Xc_out = lc_cal, la_cal, Xc_cal
                        method = "calibrated"
                        lc_conf = 0.40
                else:
                    Xc_raw = round(float(sp.phi_c), 3) if sp and np.isfinite(sp.phi_c) else None
                    lc_out, la_out, Xc_out = lc, la, Xc_raw
                    if method not in ("sasmodels", "sasmodels_failed"):
                        method = "raw"
                    lc_conf = round(float(sp.confidence_lc), 2) if sp and np.isfinite(sp.confidence_lc) else None

                row = {
                    "file": os.path.basename(str(fname)),
                    "condition_label": getattr(self.cfg, "condition_label", "Condition"),
                    "condition_value": self._conditions[i] if i < len(self._conditions) else None,
                    "L_nm": L,
                    "lc_nm": lc_out,
                    "la_nm": la_out,
                    "Xc": Xc_out,
                    "Q_star": Q_star,
                    "Q_rel": Q_rel,
                    "lc_confidence": lc_conf,
                    "lc_method": method,
                    "sasmodels_R2": round(float(sas_r2), 4) if np.isfinite(sas_r2) else None,
                    **self._condition_row_metadata(i),
                }
                row.update(_saxs_batch_helpers.copy_saxs_quality_evidence(analysis))
                if lc_cal is None and method != "sasmodels":
                    row["calibration_skipped_reason"] = skip_reason
                self._batch_params.append(row)

            self._apply_batch_params_to_results()
            self.log(f"Static: {len(self._batch_params)} frames done")
            return len(self._batch_params) > 0

        if self._q is None or self._I is None:
            return False

        self._analysis = analyze_single(self._q, self._I, self.cfg)
        self._batch_results = [self._analysis]
        self.result.raw_data["q"] = self._analysis.q
        self.result.raw_data["I"] = self._analysis.I
        self.result.raw_data["I_smooth"] = self._analysis.I_smooth
        self.log("Static single-frame analysis done")
        return True

    def analyze_temperature(self, temperatures: list, output_dir: str = "") -> Optional[TempSeriesResult]:
        if not self._q_list:
            self.log("No data loaded for temperature analysis")
            return None
        result = analyze_temperature_series(temperatures=temperatures, q_list=self._q_list, I_list=self._I_list, cfg=self.cfg)
        self._temperature_result = result
        self._results = list(getattr(result, "temp_points", []))
        if output_dir:
            self.plot(output_dir)
        return result

    def analyze_strain(self, strains: list, output_dir: str = "") -> Optional[StrainSeriesResult]:
        if not self._q_list:
            self.log("No data loaded for strain analysis")
            return None
        result = analyze_strain_series(strains=strains, q_list=self._q_list, I_list=self._I_list, cfg=self.cfg)
        self._strain_result = result
        self._results = list(getattr(result, "strain_points", []))
        if output_dir:
            self.plot(output_dir)
        return result

    def build_figure_definitions(self):
        """Return scientific figure definitions without publishing assets."""

        from .saxs_engine.figure_provider import build_saxs_figure_definitions

        return build_saxs_figure_definitions(self)

    def plot(self, output_dir: str = "") -> Dict[str, str]:
        definitions = tuple(self.build_figure_definitions())
        if not definitions:
            self.log("No figure definitions available")
            return {}
        out = output_dir or self.cfg.output_dir or "saxs_output"
        figures = self.publish_figure_definitions(
            out,
            definitions,
            profile_id="saxs_publication",
        )
        for path in figures.values():
            self.log(f"  Figure saved: {path}")
        return figures

    def get_parameters(self) -> Dict[str, Any]:
        if self._temperature_result is not None:
            tr = self._temperature_result
            temps = [float(v) for v in np.asarray(tr.temperatures, dtype=float) if np.isfinite(v)]
            lc_raw_vals = [float(v) for v in np.ravel(np.asarray(tr.lc_array, dtype=float)) if np.isfinite(v)]
            lc_effective_vals = [float(v) for v in np.ravel(np.asarray(tr.lc_effective_array, dtype=float)) if np.isfinite(v)]
            params: Dict[str, Any] = {"n_temperatures": len(tr.temperatures)}
            metric_evidence = _series_metric_evidence_payload(tr)
            if metric_evidence:
                params["metric_evidence"] = metric_evidence
            for field_name in ("detector_quality_report", "orientation_evidence"):
                copied = _saxs_batch_helpers.copy_saxs_quality_evidence(tr).get(field_name)
                if copied is not None:
                    params[field_name] = copied
            if temps:
                params["T_range_C"] = f"{min(temps):.0f}-{max(temps):.0f}"
            if lc_raw_vals:
                params["lc_range_raw_nm"] = f"{min(lc_raw_vals):.2f}-{max(lc_raw_vals):.2f}"
            if lc_effective_vals:
                params["lc_range_effective_nm"] = f"{min(lc_effective_vals):.2f}-{max(lc_effective_vals):.2f}"
                params["lc_range_nm"] = params["lc_range_effective_nm"]
            elif lc_raw_vals:
                params["lc_range_nm"] = f"{min(lc_raw_vals):.2f}-{max(lc_raw_vals):.2f}"
            if np.isfinite(tr.Tm_onset):
                params["Tm_onset_C"] = round(float(tr.Tm_onset), 1)
            if np.isfinite(tr.Tm_peak):
                params["Tm_peak_C"] = round(float(tr.Tm_peak), 1)
            if np.isfinite(tr.Tm_end):
                params["Tm_end_C"] = round(float(tr.Tm_end), 1)
            if tr.gibbs_thomson and tr.gibbs_thomson.get("valid"):
                params["Tm_inf_C"] = round(float(tr.gibbs_thomson.get("Tm_inf_C")), 1)
            if tr.avrami and tr.avrami.get("valid"):
                params["Avrami_n"] = round(float(tr.avrami.get("n")), 2)
            batch_rows = _saxs_batch_helpers.copy_saxs_series_quality_evidence(
                self._batch_params,
                getattr(tr, "temp_points", ()),
                source_index_attr="source_index",
            )
            return self._build_batch_parameters_payload(params, batch_params=batch_rows)
        if self._strain_result is not None:
            sr = self._strain_result
            strains = [float(v) for v in np.asarray(sr.strains, dtype=float) if np.isfinite(v)]
            params: Dict[str, Any] = {"n_strains": len(sr.strains)}
            metric_evidence = _series_metric_evidence_payload(sr)
            if metric_evidence:
                params["metric_evidence"] = metric_evidence
            for field_name in ("detector_quality_report", "orientation_evidence"):
                copied = _saxs_batch_helpers.copy_saxs_quality_evidence(sr).get(field_name)
                if copied is not None:
                    params[field_name] = copied
            def _first_finite(*values):
                for value in values:
                    try:
                        number = float(value)
                    except (TypeError, ValueError):
                        continue
                    if np.isfinite(number):
                        return number
                return np.nan
            if strains:
                params["strain_range_pct"] = f"{min(strains):.0f}-{max(strains):.0f}"
            if np.any(np.isfinite(sr.L_array)):
                params["L_range_nm"] = f"{np.nanmin(sr.L_array):.2f}-{np.nanmax(sr.L_array):.2f}"
            if np.any(np.isfinite(sr.Q_star_array)):
                params["Q_star_range"] = f"{np.nanmin(sr.Q_star_array):.4g}-{np.nanmax(sr.Q_star_array):.4g}"
            if sr.Q_star_rel_array is not None and np.any(np.isfinite(sr.Q_star_rel_array)):
                valid_qrel = np.asarray(sr.Q_star_rel_array, dtype=float)
                valid_qrel = valid_qrel[np.isfinite(valid_qrel)]
                if valid_qrel.size:
                    params["Q_star_rel_mean"] = round(float(np.mean(valid_qrel)), 4)
                    params["Q_star_rel_span"] = round(float(np.max(valid_qrel) - np.min(valid_qrel)), 4)
                    params["Q_star_rel_range"] = f"{np.min(valid_qrel):.4f}-{np.max(valid_qrel):.4f}"
            if sr.phi_void_array is not None and np.any(np.isfinite(sr.phi_void_array)):
                valid_phi_void = np.asarray(sr.phi_void_array, dtype=float)
                valid_phi_void = valid_phi_void[np.isfinite(valid_phi_void)]
                if valid_phi_void.size:
                    params["phi_void_mean"] = round(float(np.mean(valid_phi_void)), 4)
                    params["phi_void_span"] = round(float(np.max(valid_phi_void) - np.min(valid_phi_void)), 4)
                    params["phi_void_range"] = f"{np.min(valid_phi_void):.4f}-{np.max(valid_phi_void):.4f}"
                    params["void_detected_frames"] = int(np.sum(valid_phi_void > 0))
            if sr.f_herman_array is not None and np.any(np.isfinite(sr.f_herman_array)):
                valid_f_herman = np.asarray(sr.f_herman_array, dtype=float)
                valid_f_herman = valid_f_herman[np.isfinite(valid_f_herman)]
                if valid_f_herman.size:
                    params["f_Herman_mean"] = round(float(np.mean(valid_f_herman)), 4)
                    params["f_Herman_span"] = round(float(np.max(valid_f_herman) - np.min(valid_f_herman)), 4)
                    params["f_Herman_range"] = f"{np.min(valid_f_herman):.4f}-{np.max(valid_f_herman):.4f}"
            phase_names: List[str] = []
            phase_counts: Dict[str, int] = {}
            phase_boundary_candidates: List[Dict[str, Any]] = []
            phase_support_values: List[float] = []
            void_dominant_frame_count = 0
            frame_low_conf_count = 0
            ambiguous_frame_count = 0
            effective_frame_count = 0
            for index, point in enumerate(getattr(sr, "strain_points", []) or []):
                phase_name = str(getattr(getattr(point, "phase", None), "name", "") or "").strip().lower()
                if phase_name:
                    phase_names.append(phase_name)
                    phase_counts[phase_name] = phase_counts.get(phase_name, 0) + 1
                q_rel = _first_finite(getattr(point, "Q_star_rel", np.nan), getattr(point, "Q_star_normalized", np.nan))
                phi_void = _first_finite(getattr(point, "phi_void", np.nan))
                f_herman = _first_finite(getattr(point, "f_herman", np.nan))
                phase_support = self._strain_phase_support_score(
                    phase_name or "ELASTIC",
                    q_rel if np.isfinite(q_rel) else None,
                    bool(getattr(point, "has_voids", False)) or (np.isfinite(phi_void) and phi_void > 0.02),
                    f_herman if np.isfinite(f_herman) else None,
                    None,
                )
                phase_support_values.append(phase_support)
                if bool(getattr(point, "has_voids", False)) or (np.isfinite(phi_void) and phi_void > 0.02):
                    void_dominant_frame_count += 1
                if phase_support < 0.55:
                    ambiguous_frame_count += 1
                point_conf = _first_finite(getattr(point, "confidence", np.nan))
                if np.isfinite(point_conf) and point_conf < 0.55:
                    frame_low_conf_count += 1
                if phase_name and phase_name != "elastic":
                    effective_frame_count += 1
            for index in range(1, len(phase_names)):
                prev_name = phase_names[index - 1]
                curr_name = phase_names[index]
                if curr_name != prev_name:
                    strain_value = _first_finite(sr.strains[index])
                    phase_boundary_candidates.append(
                        {
                            "strain_pct": round(float(strain_value), 3) if np.isfinite(strain_value) else None,
                            "from_phase": prev_name,
                            "to_phase": curr_name,
                        }
                    )
            if phase_counts:
                params["phase_distribution"] = dict(sorted(phase_counts.items()))
                params["dominant_phase"] = max(phase_counts.items(), key=lambda item: item[1])[0]
            if phase_boundary_candidates:
                params["phase_boundary_candidates"] = phase_boundary_candidates
            if phase_support_values:
                params["phase_support_mean"] = round(float(np.mean(phase_support_values)), 3)
                params["phase_support_span"] = round(float(np.max(phase_support_values) - np.min(phase_support_values)), 3) if len(phase_support_values) >= 2 else 0.0
            params["phase_ambiguous_frame_count"] = ambiguous_frame_count
            params["void_dominant_frame_count"] = void_dominant_frame_count
            params["frame_low_conf_count"] = frame_low_conf_count
            params["effective_param_ratio"] = round(float(effective_frame_count / len(sr.strain_points)), 3) if sr.strain_points else 0.0
            strain_axis_conf_values = [float(v) for v in self._condition_confidences if np.isfinite(v)]
            strain_axis_confidence = float(np.mean(strain_axis_conf_values)) if strain_axis_conf_values else np.nan
            if np.isfinite(strain_axis_confidence):
                params["strain_axis_confidence"] = round(float(strain_axis_confidence), 2)
            params["strain_reliability_status"] = "usable" if frame_low_conf_count == 0 and ambiguous_frame_count == 0 else ("low_confidence" if frame_low_conf_count <= max(1, len(sr.strain_points) // 3) else "diagnostic_only")
            reason_bits: list[str] = []
            if frame_low_conf_count > 0:
                reason_bits.append("strain_axis_low_confidence")
            if void_dominant_frame_count > 0:
                reason_bits.append("low_q_void_dominant")
            if ambiguous_frame_count > 0:
                reason_bits.append("phase_ambiguous")
            if not reason_bits:
                reason_bits.append("stable_structure_support")
            params["strain_reliability_reason"] = "|".join(dict.fromkeys(reason_bits))
            params["paper_figure_candidate"] = bool(len(sr.strain_points) > 0 and frame_low_conf_count <= max(1, len(sr.strain_points) // 2))
            params["paper_conclusion_candidate"] = bool(
                params["paper_figure_candidate"]
                and params["strain_reliability_status"] == "usable"
                and ambiguous_frame_count == 0
                and void_dominant_frame_count <= max(1, len(sr.strain_points) // 3)
            )
            params["paper_conclusion_ready"] = params["paper_conclusion_candidate"]
            batch_rows = _saxs_batch_helpers.copy_saxs_series_quality_evidence(
                self._batch_params,
                getattr(sr, "strain_points", ()),
            )
            return self._build_batch_parameters_payload(params, batch_params=batch_rows)
        if self._batch_params:
            # Temperature/strain results have dedicated branches above.  If
            # neither series result exists, the aligned batch rows are the
            # only surviving transport boundary; do not let a stale mode
            # label discard frame-level evidence from those results.
            if len(self._batch_params) > 1:
                base_params: Dict[str, Any] = {
                    "metric_evidence_scope": _saxs_batch_helpers.batch_metric_evidence_scope(
                        getattr(self.cfg, "experiment_type", "")
                    ),
                }
                metric_evidence = _saxs_batch_helpers.build_static_batch_metric_evidence(
                    self._batch_results,
                )
                if metric_evidence:
                    base_params["metric_evidence"] = metric_evidence
                base_params.update(
                    _saxs_batch_helpers.build_static_batch_2d_quality_evidence(
                        self._batch_results,
                    )
                )
                aligned_rows = []
                for index, row in enumerate(self._batch_params):
                    aligned = dict(row)
                    if index < len(self._batch_results):
                        aligned.update(
                            _saxs_batch_helpers.copy_saxs_quality_evidence(
                                self._batch_results[index],
                            )
                        )
                    aligned_rows.append(aligned)
                return self._build_batch_parameters_payload(
                    base_params,
                    batch_params=aligned_rows,
                )
            return self._build_batch_parameters_payload()
        if self._analysis is not None and self._analysis.structure is not None:
            sp = self._analysis.structure
            params: Dict[str, Any] = {}
            if np.isfinite(sp.L):
                params["L_nm"] = round(float(sp.L), 2)
            if np.isfinite(sp.lc):
                params["lc_nm"] = round(float(sp.lc), 2)
            if np.isfinite(sp.la):
                params["la_nm"] = round(float(sp.la), 2)
            if np.isfinite(sp.phi_c):
                params["phi_c"] = round(float(sp.phi_c), 3)
            if np.isfinite(sp.Q_invariant):
                params["Q_star"] = round(float(sp.Q_invariant), 4)
            params.update(_saxs_batch_helpers.copy_saxs_quality_evidence(self._analysis))
            return params
        if self._q is not None and self._I is not None:
            result = analyze_single(self._q, self._I, self.cfg)
            sp = result.structure
            params: Dict[str, Any] = {}
            if sp and np.isfinite(sp.L):
                params["L_nm"] = round(float(sp.L), 2)
            if sp and np.isfinite(sp.lc):
                params["lc_nm"] = round(float(sp.lc), 2)
            if sp and np.isfinite(sp.la):
                params["la_nm"] = round(float(sp.la), 2)
            if sp and np.isfinite(sp.phi_c):
                params["phi_c"] = round(float(sp.phi_c), 3)
            params.update(_saxs_batch_helpers.copy_saxs_quality_evidence(result))
            return params
        return {}

    def export_bundle(self, output_dir: str) -> SAXSExportBundle:
        """Write the reproducible SAXS bundle without hiding legacy writers."""
        bundle = export_saxs_bundle(self, output_dir)
        self.result.metadata["saxs_export_status"] = bundle.status
        self.result.metadata["saxs_export_root"] = bundle.root
        return bundle

    def export(self, output_dir: str) -> bool:
        has_results = bool(
            self._batch_results
            or self._analysis is not None
            or self._temperature_result is not None
            or self._strain_result is not None
            or self._processed_list
        )
        if not has_results:
            return False
        legacy_ok = False
        try:
            results = self._batch_results if self._batch_results else [self._analysis]
            if results and results[0] is not None:
                export_parameters_csv(results, output_dir)
                legacy_ok = True
        except Exception as e:
            self.log(f"Export failed: {e}")
            logger.warning("SAXS export failed.", exc_info=True)
        bundle = self.export_bundle(output_dir)
        return bool(legacy_ok or bundle.succeeded)
