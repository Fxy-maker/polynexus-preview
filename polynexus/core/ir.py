"""IR spectroscopy analysis engine.

Wraps the modular ir_engine sub-package while conforming to the
BaseEngine interface (load -> preprocess -> analyze -> plot).

Supports:
    - Experimental IR spectrum loading (CSV, SPA, DPT)
    - Rubberband / ALS baseline correction
    - ATR penetration depth correction
    - Peak detection & Lorentzian fitting
    - Peak assignment against polymer database (7 polymers)
    - Spectrum simulation from DFT-computed modes
    - Experimental-computational comparison
    - Crystallinity index (band ratio method)
    - Gaussian / ORCA frequency output parsing
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional

from .engine import BaseEngine, EngineCategory, register_technique
from .submodule_registry import SubModuleSpec, register_submodule
from .ir_engine import (
    IRConfig,
    IRSpectrum,
    ComputedMode,
    IRResult,
    load_project,
    load_computed_modes,
    preprocess_pipeline,
    analyze_spectrum,
    IRTemp2DResult,
    detect_temperature_2d,
    analyze_temperature_2d_series,
)


logger = logging.getLogger(__name__)


@register_technique("ir")
@register_submodule(SubModuleSpec(
    id="ir.temperature_2d", parent_technique="ir", label="原位变温二维 IR", icon="🌡️",
    description="温度-波数二维图、Noda 2D-COS 同步/异步相关谱和 PA6 特征带追踪",
    priority=20, required_polymer_families=["polyamide"],
    accepted_formats=["directory", "*.csv", "*.spa", "*.dpt", "*.txt", "*.dat"],
    input_mode="sequence",
    detect_experiment_type=detect_temperature_2d,
    config_schema={
        "baseline_corr": {"type": "choice", "options": ["rubberband", "linear", "none"], "default": "rubberband", "label": "基线校正"},
        "smooth_window": {"type": "int", "min": 3, "max": 31, "default": 7, "label": "平滑窗口"},
        "polymer_name": {"type": "string", "default": "PA6", "label": "聚合物"},
    },
    output_parameters=[
        {"key": "n_frames", "label": "序列帧数", "format": "d"},
        {"key": "T_range_C", "label": "温度范围", "format": "s"},
        {"key": "max_sync_autocorr", "label": "最大同步自相关", "format": ".4g"},
        {"key": "top_async_cross_peak_cm1", "label": "最强异步交叉峰", "format": "s"},
    ],
    figure_types=[
        "temperature_heatmap", "temperature_waterfall", "band_tracking",
        "2dcos_synchronous", "2dcos_asynchronous",
    ],
))
@register_submodule(SubModuleSpec(
    id="ir.standard", parent_technique="ir", label="标准 IR", icon="〰️",
    description="峰识别，特征官能团鉴定，结晶度指数",
    required_polymer_families=["polyolefin", "polyester", "polyamide", "fluoropolymer", "elastomer"],
    accepted_formats=["*.spa", "*.csv", "*.txt", "*.dat"], input_mode="single",
    config_schema={
        "baseline_corr": {"type": "choice", "options": ["rubberband","linear","none"], "default": "rubberband", "label": "基线校正"},
        "smooth_window": {"type": "int", "min": 3, "max": 31, "default": 5, "label": "平滑窗口"},
    },
    output_parameters=[
        {"key": "n_peaks", "label": "吸收峰数", "format": "d"},
        {"key": "crystallinity_index", "label": "结晶度指数", "format": ".3f"},
    ],
    figure_types=["absorbance_spectrum", "peak_assignments"],
))
@register_submodule(SubModuleSpec(
    id="ir.mapping", parent_technique="ir", label="IR 面扫", icon="🗺️",
    description="微区化学成像，组成分布分析",
    priority=10, required_polymer_families=["polyolefin", "polyester", "polyamide"],
    accepted_formats=["directory"], input_mode="sequence",
    output_parameters=[
        {"key": "n_spectra", "label": "光谱数", "format": "d"},
    ],
    figure_types=["heatmap", "composition_distribution"],
))
class IREngine(BaseEngine):
    """Infrared Spectroscopy analysis engine."""

    name = "ir"
    label = "IR"
    icon = "🔴"
    category = EngineCategory.HYBRID
    description = (
        "Infrared Spectroscopy: experimental spectrum + DFT vibrational mode comparison"
    )

    def __init__(self, config=None, log_fn=None):
        super().__init__(config=config, log_fn=log_fn)
        self._ir_config = config if isinstance(config, IRConfig) else IRConfig()
        self._spectra: List[IRSpectrum] = []
        self._results: List[IRResult] = []
        self._computed_modes: List[ComputedMode] = []
        self._temperature_2d_result: Optional[IRTemp2DResult] = None
        if isinstance(config, dict):
            self.set_config(**config)

    def load(self, filepath: str) -> bool:
        try:
            self._spectra = load_project(filepath, self._ir_config.wavenumber_range)
            if not self._spectra:
                self.log(f"No valid IR data found in: {filepath}")
                return False
            for s in self._spectra:
                if len(s.wavenumber):
                    self.log(
                        f"  {s.label} ({len(s.wavenumber)} pts, "
                        f"{np.nanmax(s.wavenumber):.1f}-{np.nanmin(s.wavenumber):.1f} cm-1, "
                        f"source={s.source})"
                    )
                else:
                    self.log(f"  {s.label} ({len(s.wavenumber)} pts, source={s.source})")
            return True
        except Exception as e:
            self.log(f"Failed to load: {e}")
            logger.warning("IR load failed.", exc_info=True)
            return False

    def load_computed(self, filepath: str) -> bool:
        try:
            self._computed_modes = load_computed_modes(
                filepath, self._ir_config.freq_correction_factor)
            self.log(f"Loaded {len(self._computed_modes)} computed modes")
            return len(self._computed_modes) > 0
        except Exception as e:
            self.log(f"Failed to load computed modes: {e}")
            logger.warning("IR computed modes load failed.", exc_info=True)
            return False

    def preprocess(self) -> bool:
        if not self._spectra:
            self.log("No data loaded")
            return False
        cfg = self._ir_config
        for i, spec in enumerate(self._spectra):
            try:
                self._spectra[i] = preprocess_pipeline(spec, cfg)
                self.log(f"  [{spec.label}] baseline={cfg.baseline_method}")
            except Exception as e:
                self.log(f"  [{spec.label}] preprocessing failed: {e}")
                logger.warning("IR preprocessing failed.", exc_info=True)
                return False
        return True

    def analyze(self) -> bool:
        if not self._spectra:
            self.log("No preprocessed data")
            return False
        cfg = self._ir_config
        self._results = []
        self._temperature_2d_result = None
        if self.active_submodule == "ir.temperature_2d":
            temp_result = analyze_temperature_2d_series(
                self._spectra, cfg, label="IR temperature 2D series")
            self._temperature_2d_result = temp_result
            self._results = temp_result.results
            temps = [t for t in temp_result.temperatures if np.isfinite(t)]
            stages = sorted(set(temp_result.stages))
            self.log(
                "  Temperature 2D IR "
                f"frames={len(temp_result.frames)} "
                f"stages={','.join(stages)} "
                + (f"T={min(temps):.0f}-{max(temps):.0f} C " if temps else "")
                + f"matrix={temp_result.absorbance_matrix.shape} "
                + f"2D-COS={temp_result.sync_corr.shape}"
            )
            self.result.raw_data["wavenumber"] = np.asarray(temp_result.wavenumber, dtype=float)
            self.result.raw_data["absorbance_matrix"] = np.asarray(
                temp_result.absorbance_matrix, dtype=float)
            self.result.raw_data["temperature_C"] = np.asarray(temp_result.temperatures, dtype=float)
            self.result.parameters = dict(temp_result.parameters)
            self.result.analysis_evidence = {}
            return True

        for spec in self._spectra:
            result = analyze_spectrum(spec, cfg, label=spec.label,
                                      computed_modes=self._computed_modes
                                      if self._computed_modes else None,
                                      polymer_name=cfg.polymer_name)
            self._results.append(result)
            self.log(
                f"  [{result.label}] "
                + (f"peaks={result.n_peaks} " if result.n_peaks > 0 else "")
                + (f"polymer={result.polymer_name} " if result.polymer_name else "")
                + (f"Xc={result.Xc_pct:.1f}" if not np.isnan(result.Xc_pct) else "")
                + (f" matches={len(result.matches)}" if result.matches else "")
            )
        if self._spectra:
            spec = self._spectra[0]
            self.result.raw_data["wavenumber"] = np.asarray(spec.wavenumber, dtype=float)
            self.result.raw_data["absorbance"] = np.asarray(spec.absorbance, dtype=float)
            self.result.raw_data["label"] = spec.label or "IR"
        self.result.parameters = dict(self.get_parameters())
        return True

    def build_figure_definitions(self):
        """Return scientific figure definitions without publishing assets."""

        from .ir_engine.figure_provider import build_ir_figure_definitions

        return build_ir_figure_definitions(
            tuple(self._results),
            temperature_2d_result=self._temperature_2d_result,
        )

    def plot(self, output_dir: str = "") -> Dict[str, str]:
        definitions = tuple(self.build_figure_definitions())
        if not definitions:
            self.log("No figure definitions available")
            return {}
        default_output = (
            "ir_temperature_2d_output"
            if self.active_submodule == "ir.temperature_2d"
            else "ir_output"
        )
        out = output_dir or self._ir_config.output_dir or default_output
        figures = self.publish_figure_definitions(out, definitions)
        for path in figures.values():
            self.log(f"  Figure saved: {path}")
        return figures

    def get_parameters(self) -> Dict[str, Any]:
        if self.active_submodule == "ir.temperature_2d" and self._temperature_2d_result:
            return self._temperature_2d_result.parameters
        if not self._results:
            return {}
        merged = {}
        for r in self._results:
            merged[r.label] = r.parameters
        return merged

    def _validate_results(self) -> bool:
        """IR range checks: Xc, peak count."""
        if self.active_submodule == "ir.temperature_2d":
            tr = self._temperature_2d_result
            if tr is None or not tr.frames:
                self.add_quality_flag("temperature_2d/frames", "ERROR")
                return self.result.validation_passed
            self.add_quality_flag(
                "temperature_2d/frames",
                "OK" if len(tr.frames) >= 3 else "WARN",
            )
            self.add_quality_flag(
                "temperature_2d/matrix",
                "OK" if tr.absorbance_matrix.shape[0] == len(tr.frames) else "ERROR",
            )
            self.add_quality_flag(
                "temperature_2d/2dcos",
                "OK" if tr.sync_corr.size and tr.async_corr.size else "WARN",
            )
            if tr.neg_fraction > 0.01:
                self.add_quality_flag(
                    "temperature_2d/neg_fraction",
                    "WARN",
                )
            return self.result.validation_passed

        for r in self._results:
            if r.n_peaks <= 0:
                self.add_quality_flag(f"{r.label}/IR_peaks", "ERROR")
            else:
                self.add_quality_flag(f"{r.label}/IR_peaks", "OK")
            if not r.polymer_name:
                self.add_quality_flag(f"{r.label}/polymer_assignment", "WARN")
            if not np.isnan(r.Xc_pct):
                if r.Xc_pct < 0 or r.Xc_pct > 100:
                    self.add_quality_flag(f"{r.label}/Xc_IR", "WARN")
                else:
                    self.add_quality_flag(f"{r.label}/Xc_IR", "OK")
        return self.result.validation_passed

    def set_config(self, **kwargs):
        aliases = {
            "baseline_corr": "baseline_method",
            "smooth_span": "smooth_window",
            "polymer": "polymer_name",
        }
        for k, v in kwargs.items():
            k = aliases.get(k, k)
            if hasattr(self._ir_config, k):
                setattr(self._ir_config, k, v)

    @property
    def results(self) -> List[IRResult]:
        return self._results
