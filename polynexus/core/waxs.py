"""WAXS analysis engine.

Wraps the modular waxs_engine sub-package while conforming to the
BaseEngine interface (load -> preprocess -> analyze -> plot).
"""
import logging
logger = logging.getLogger(__name__)

import numpy as np
from typing import Dict, Any, List, Optional

from .engine import BaseEngine, EngineCategory, register_technique
from .submodule_registry import SubModuleSpec, register_submodule
from .waxs_engine import (
    WAXSConfig, WAXSDataset, WAXSResult,
    load_project, preprocess_pipeline, analyze_scan, generate_all_figures,
    WAXSStrainSeriesResult, analyze_strain_series, generate_strain_figures,
    export_strain_csv,
    WAXSTempResult, analyze_temperature_series, fig_waxs_temperature,
    generate_temperature_figures, export_temperature_csv,
)

@register_technique("waxs")
@register_submodule(SubModuleSpec(
    id="waxs.static", parent_technique="waxs", label="静态 WAXS", icon="💎",
    description="峰分解，结晶度，Scherrer 晶粒尺寸",
    required_polymer_families=["polyolefin", "polyester", "polyamide", "fluoropolymer"],
    accepted_formats=["*.dat", "*.txt", "*.csv", "*.xlsx"], input_mode="single",
    config_schema={
        "peak_function": {"type": "choice", "options": ["pseudo_voigt","gaussian","lorentzian"], "default": "pseudo_voigt", "label": "峰函数"},
        "background": {"type": "choice", "options": ["polynomial","spline","linear"], "default": "polynomial", "label": "背景扣除"},
        "amorphous_model": {"type": "choice", "options": ["spline","polynomial","manual"], "default": "spline", "label": "非晶模型"},
    },
    output_parameters=[
        {"key": "Xc_pct", "label": "结晶度 Xc (%)", "format": ".1f"},
        {"key": "D_Scherrer_nm", "label": "晶粒尺寸 D (nm)", "format": ".2f"},
        {"key": "n_peaks", "label": "衍射峰数", "format": "d"},
    ],
    figure_types=["diffraction_profile", "peak_deconvolution", "crystallinity_bar"],
))
@register_submodule(SubModuleSpec(
    id="waxs.temperature", parent_technique="waxs", label="原位变温 WAXS", icon="💎",
    description="晶型转变，结晶度-温度曲线",
    priority=10, required_polymer_families=["polyolefin", "polyester", "polyamide"],
    accepted_formats=["directory"], input_mode="sequence",
    output_parameters=[
        {"key": "Xc_pct", "label": "结晶度 Xc (%)", "format": ".1f"},
        {"key": "crystal_form", "label": "主导晶型", "format": "s"},
    ],
    figure_types=["temperature_waterfall", "crystallinity_vs_T"],
))
@register_submodule(SubModuleSpec(
    id="waxs.strain",
    parent_technique="waxs",
    label="原位拉伸 WAXS",
    icon="💎",
    description="应变依赖：取向演化，晶型转变，应力诱导结晶，晶格应变",
    priority=10,
    required_polymer_families=["polyolefin", "polyester", "polyamide"],
    accepted_formats=["directory"],
    input_mode="sequence",
    output_parameters=[
        {"key": "Xc_pct", "label": "结晶度 Xc (%)", "format": ".1f"},
        {"key": "D_Scherrer_nm", "label": "晶粒尺寸 D (nm)", "format": ".2f"},
        {"key": "f_Herman_avg", "label": "平均 Herman 取向因子", "format": ".3f"},
        {"key": "polymorph_transition", "label": "晶型转变", "format": "s"},
    ],
    figure_types=["diffraction_waterfall", "strain_parameters", "lattice_strain"],
))
class WAXSEngine(BaseEngine):
    """Wide-Angle X-ray Scattering analysis engine."""

    name = "waxs"
    label = "WAXS"
    icon = "🔷"
    category = EngineCategory.EXPERIMENTAL
    description = (
        "Wide-Angle X-ray Scattering: crystallinity, peak fitting, "
        "Scherrer / Williamson-Hall size, crystal system ID"
    )

    def __init__(self, config=None, log_fn=None):
        super().__init__(config=config, log_fn=log_fn)
        self._waxs_config = WAXSConfig()
        self._dataset: Optional[WAXSDataset] = None
        self._results: List[WAXSResult] = []
        self._temperature_result: Optional[WAXSTempResult] = None
        self._strain_result: Optional[WAXSStrainSeriesResult] = None

    def load(self, filepath: str) -> bool:
        try:
            self._dataset = load_project(filepath)
            if not self._dataset or len(self._dataset.scans) == 0:
                self.log(f"No valid WAXS data found in: {filepath}")
                return False
            self.log(f"Loaded {len(self._dataset.scans)} scan(s)")
            for s in self._dataset.scans:
                has_img = " + image" if s.image is not None else ""
                has_1d = f" ({len(s.two_theta_deg)} pts)" if len(s.two_theta_deg) > 0 else ""
                self.log(f"  {s.label}{has_img}{has_1d}")
            return True
        except Exception as e:
            self.log(f"Failed to load data: {e}")
            logger.warning("WAXS load failed.", exc_info=True)
            return False

    def preprocess(self) -> bool:
        if not self._dataset or not self._dataset.scans:
            self.log("No data loaded")
            return False
        cfg = self._waxs_config
        if getattr(self, 'active_submodule', '') == 'waxs.strain':
            cfg.do_sector_integration = True
        for i, scan in enumerate(self._dataset.scans):
            try:
                self._dataset.scans[i] = preprocess_pipeline(scan, cfg)
                self.log(f"  [{scan.label}] bg={cfg.background_method}, smooth={cfg.smooth_method}")
            except Exception as e:
                self.log(f"  [{scan.label}] preprocessing failed: {e}")
                logger.warning("WAXS preprocessing failed.", exc_info=True)
                return False
        self.log(f"Preprocessed {len(self._dataset.scans)} scan(s)")
        return True

    def analyze(self) -> bool:
        sub = getattr(self, 'active_submodule', '')
        if sub == 'waxs.strain':
            self._waxs_config.do_sector_integration = True
            n = len(self._dataset.scans)
            strains = self._sequence_values("strain", default_start=0.0, default_step=10.0)
            result = self.analyze_strain(strains)
            return result is not None
        elif sub == 'waxs.temperature':
            temps = self._sequence_values("temperature", default_start=25.0, default_step=10.0)
            result = self.analyze_temperature(temps)
            return result is not None
        if not self._dataset or not self._dataset.scans:
            self.log("No preprocessed data")
            return False
        cfg = self._waxs_config
        self._results = []
        for scan in self._dataset.scans:
            result = analyze_scan(scan, cfg, label=scan.label)
            self._results.append(result)
            self.log(
                f"  [{result.label}] "
                + (f"peaks={result.n_peaks} " if result.n_peaks > 0 else "no peaks ")
                + (f"Xc={result.Xc_pct:.1f}% " if not np.isnan(result.Xc_pct) else "")
                + (f"D={result.D_Scherrer_nm:.1f}nm" if not np.isnan(result.D_Scherrer_nm) else "")
            )
        if self._results:
            r0 = self._results[0]
            if len(r0.two_theta) > 0 and len(r0.I) > 0:
                self.result.raw_data["two_theta"] = r0.two_theta
                self.result.raw_data["I"] = r0.I
        return True

    def plot(self, output_dir: str = "") -> Dict[str, str]:
        if not self._results:
            self.log("No analysis results to plot")
            return {}
        out = output_dir or self._waxs_config.output_dir or "waxs_output"
        sub = getattr(self, 'active_submodule', '')
        if sub == 'waxs.temperature' and self._temperature_result is not None:
            figures = generate_temperature_figures(
                self._temperature_result, self._dataset.scans if self._dataset else None,
                out, config=self._waxs_config,
            )
        elif sub == 'waxs.strain' and self._strain_result is not None:
            figures = generate_strain_figures(
                self._strain_result, self._dataset.scans if self._dataset else None,
                out, config=self._waxs_config,
            )
        else:
            figures = generate_all_figures(self._results, out, config=self._waxs_config)
        for name, path in figures.items():
            self.log(f"  Figure saved: {path}")
        return figures

    def analyze_strain(self, strains: list, output_dir: str = "") -> Optional[WAXSStrainSeriesResult]:
        if not self._dataset or not self._dataset.scans:
            self.log("No data loaded for strain analysis")
            return None
        n_scans = len(self._dataset.scans)
        if len(strains) != n_scans:
            if len(strains) > n_scans:
                strains = strains[:n_scans]
            else:
                strains = list(strains) + [strains[-1] + (i+1)*10 for i in range(n_scans - len(strains))]
        cfg = self._waxs_config
        result = analyze_strain_series(
            strains=strains, scans=self._dataset.scans, config=cfg,
        )
        self._strain_result = result
        self._results = [p.waxs_result for p in result.point_results if p.waxs_result is not None]
        if output_dir:
            out = output_dir or cfg.output_dir or "waxs_strain_output"
            generate_strain_figures(result, self._dataset.scans, out, config=cfg)
            export_strain_csv(result, out)
        return result

    def analyze_temperature(self, temperatures: list, output_dir: str = "") -> Optional[WAXSTempResult]:
        if not self._dataset or not self._dataset.scans:
            self.log("No data loaded for temperature analysis")
            return None
        n_scans = len(self._dataset.scans)
        if len(temperatures) != n_scans:
            if len(temperatures) > n_scans:
                temperatures = temperatures[:n_scans]
            else:
                temperatures = list(temperatures) + [temperatures[-1] + (i+1)*10 for i in range(n_scans - len(temperatures))]
        cfg = self._waxs_config
        result = analyze_temperature_series(temperatures=temperatures, scans=self._dataset.scans, config=cfg)
        self._temperature_result = result
        self._results = list(result.results)
        for T, r in zip(result.temperatures, result.results):
            self.log(
                f"  [T={T:.0f}C] "
                + (f"peaks={r.n_peaks} " if r.n_peaks > 0 else "no peaks ")
                + (f"Xc={r.Xc_pct:.1f}% " if not np.isnan(r.Xc_pct) else "")
                + (f"D={r.D_Scherrer_nm:.1f}nm" if not np.isnan(r.D_Scherrer_nm) else "")
            )
        if result.results:
            first = result.results[0]
            self.result.raw_data["two_theta"] = first.two_theta
            self.result.raw_data["I"] = first.I
            self.result.raw_data["temperature"] = np.asarray(result.temperatures, dtype=float)
            self.result.raw_data["Xc_vs_T"] = np.asarray(result.Xc_vs_T, dtype=float)
        if output_dir:
            out = output_dir or cfg.output_dir or "waxs_temp_output"
            generate_temperature_figures(result, self._dataset.scans, out, config=cfg)
        return result

    def _sequence_values(self, kind: str, default_start: float, default_step: float) -> List[float]:
        n = len(self._dataset.scans) if self._dataset else 0
        values = []
        if self._dataset and self._dataset.conditions:
            for cond in self._dataset.conditions[:n]:
                if cond.get("type") == kind:
                    try:
                        val = float(cond.get("value"))
                    except (TypeError, ValueError):
                        val = np.nan
                    values.append(val)
        if len(values) == n and all(np.isfinite(v) for v in values):
            return values
        return [float(default_start + i * default_step) for i in range(n)]

    def get_parameters(self) -> Dict[str, Any]:
        if getattr(self, 'active_submodule', '') == 'waxs.temperature' and self._temperature_result is not None:
            tr = self._temperature_result
            params: Dict[str, Any] = dict(tr.parameters)
            params["frame_count"] = len(tr.results)
            params["temperature_summary_frame"] = tr.results[0].label if tr.results else ""
            if tr.results:
                first = tr.results[0]
                params["Xc_pct"] = round(float(first.Xc_pct), 3) if np.isfinite(first.Xc_pct) else np.nan
                params["D_Scherrer_nm"] = round(float(first.D_Scherrer_nm), 3) if np.isfinite(first.D_Scherrer_nm) else np.nan
                params["n_peaks"] = int(first.n_peaks)
                params["r_squared"] = round(float(first.r_squared), 6) if np.isfinite(first.r_squared) else np.nan
                params["crystal_system"] = first.crystal_system or ""
                params["Xc_method"] = first.Xc_method or ""
                params["peak_positions"] = [float(pk.get("two_theta", np.nan)) for pk in first.peaks]
                params["peak_widths"] = [float(pk.get("fwhm_deg", np.nan)) for pk in first.peaks]
                params["peak_areas"] = [float(pk.get("area", np.nan)) for pk in first.peaks]
                params["peaks"] = [dict(pk) for pk in first.peaks]
            return params
        if not self._results:
            return {}
        r0 = self._results[0]
        params: Dict[str, Any] = {}
        if not np.isnan(r0.Xc_pct):
            params["Xc_pct"] = round(float(r0.Xc_pct), 1)
        if not np.isnan(r0.D_Scherrer_nm):
            params["D_Scherrer_nm"] = round(float(r0.D_Scherrer_nm), 2)
        if r0.n_peaks > 0:
            params["n_peaks"] = r0.n_peaks
        if r0.crystal_system:
            params["crystal_system"] = r0.crystal_system
        if hasattr(r0, 'sector_used'):
            params["sector_used"] = r0.sector_used
        if len(self._results) > 1:
            params["batch_frames"] = len(self._results)
            xc_vals = [r.Xc_pct for r in self._results if not np.isnan(r.Xc_pct)]
            if xc_vals:
                params["Xc_range"] = f"{min(xc_vals):.1f}-{max(xc_vals):.1f}%"
        return params

    def export(self, output_dir: str) -> bool:
        if not self._results:
            return False
        from .waxs_engine import export_parameters_csv
        try:
            export_parameters_csv(self._results, output_dir)
            return True
        except Exception as e:
            self.log(f"Export failed: {e}")
            logger.warning("WAXS export failed.", exc_info=True)
            return False
