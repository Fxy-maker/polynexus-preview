"""DSC analysis engine.

Wraps the modular dsc_engine sub-package while conforming to the
BaseEngine interface (load → preprocess → analyze → plot).

Module-level architecture:
    dsc_engine/
        config.py        — DSCConfig
        io.py            — load_scan, load_project
        preprocess.py    — preprocess_pipeline
        core.py          — analyze_scan, DSCResult
        dsc_kinetics.py  — Avrami, Ozawa, Kissinger, Friedman, Mo
        dsc_output.py    — SCI figure generation
"""

import logging
import copy
import math
import numpy as np
from typing import Dict, Any, List

from .submodule_registry import SubModuleSpec, register_submodule
from .engine import BaseEngine, EngineCategory, register_technique
from .analysis_evidence_handoff import refresh_analysis_evidence
from .dsc_engine import (
    DSCConfig,
    DSCScan,
    DSCResult,
    load_project,
    normalise_scan,
    preprocess_pipeline,
    analyze_scan,
    analyze_kinetics,
    analyze_nonisothermal_scans,
    AvramiResult,
)
from .dsc_engine.dsc_kinetics import (
    IsothermalKineticsResult,
    IsothermalSegment,
    avrami_from_dsc,
    avrami_candidates_from_dsc,
)
from .dsc_engine.figure_provider import build_dsc_figure_definitions

logger = logging.getLogger(__name__)


def _json_safe_parameters(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe_parameters(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe_parameters(item) for item in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(float(value)) else None
    return value


@register_technique("dsc")
@register_submodule(SubModuleSpec(
    id="dsc.standard", parent_technique="dsc", label="标准 DSC", icon="🔥",
    description="Tg/Tm/Tc检测，结晶度，多峰分解",
    required_polymer_families=["polyolefin", "polyester", "polyamide", "fluoropolymer", "elastomer"],
    accepted_formats=["*.001", "*.csv", "*.xlsx", "*.txt"], input_mode="single",
    config_schema={
        "baseline_corr": {"type": "choice", "options": ["linear","tangential","sigmoid"], "default": "tangential", "label": "基线校正"},
        "Tg_method": {"type": "choice", "options": ["half_height","inflection","onset"], "default": "half_height", "label": "Tg 方法"},
    },
    output_parameters=[
        {"key": "Tg_C", "label": "Tg (C)", "format": ".1f"},
        {"key": "Tm_peak_C", "label": "Tm (C)", "format": ".1f"},
        {"key": "DHm_Jg", "label": "焓值 (J/g)", "format": ".2f"},
        {"key": "Xc_pct", "label": "结晶度 Xc (%)", "format": ".1f"},
    ],
    figure_types=["thermogram", "tg_zoom", "peak_deconvolution"],
))
@register_submodule(SubModuleSpec(
    id="dsc.isothermal", parent_technique="dsc", label="等温动力学", icon="⏱️",
    description="Avrami 等温结晶动力学",
    priority=10, required_polymer_families=["polyolefin", "polyester", "polyamide"],
    accepted_formats=["directory"], input_mode="sequence",
    output_parameters=[
        {"key": "Avrami_n", "label": "Avrami 指数 n", "format": ".2f"},
        {"key": "Avrami_k", "label": "Avrami 速率常数 k", "format": ".4e"},
    ],
    figure_types=["isothermal_curves", "avrami_plot"],
))
@register_submodule(SubModuleSpec(
    id="dsc.nonisothermal", parent_technique="dsc", label="非等温动力学", icon="📈",
    description="Ozawa/Mo/Kissinger/Friedman 非等温动力学",
    priority=10, required_polymer_families=["polyolefin", "polyester", "polyamide"],
    accepted_formats=["directory"], input_mode="sequence",
    output_parameters=[
        {"key": "activation_energy", "label": "活化能 Ea (kJ/mol)", "format": ".1f"},
    ],
    figure_types=["ozawa_plot", "kissinger_plot", "friedman_plot"],
))
class DSCEngine(BaseEngine):
    """Differential Scanning Calorimetry analysis engine.

    Supports:
        - Glass transition Tg (inflection / half-height / onset / fictive)
        - Melting Tm (onset / peak / end) + enthalpy
        - Cold crystallisation Tcc + enthalpy
        - Crystallinity Xc (database-driven)
        - Multi-peak deconvolution (Gaussian / Lorentzian / Voigt)
        - Isothermal kinetics:  Avrami
        - Non-isothermal kinetics: Ozawa, Mo, Kissinger, Friedman
        - SCI-quality figures: 6 standard figure types
    """

    name = "dsc"
    label = "DSC"
    icon = "🔥"
    category = EngineCategory.EXPERIMENTAL
    description = (
        "Differential Scanning Calorimetry: Tm, Tc, Tg, crystallinity, "
        "Avrami/Ozawa/Kissinger kinetics"
    )

    # ------------------------------------------------------------------
    #  Lifecycle
    # ------------------------------------------------------------------

    def __init__(self, config=None, log_fn=None):
        super().__init__(config=config, log_fn=log_fn)
        self._dsc_config = config if isinstance(config, DSCConfig) else DSCConfig.from_dict(config or {})
        self._scans: List[DSCScan] = []
        self._raw_scans: List[DSCScan] = []
        self._results: List[DSCResult] = []
        self._kinetics_data: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    #  BaseEngine interface
    # ------------------------------------------------------------------

    def load(self, filepath: str) -> bool:
        """Load DSC data from file or directory.

        Parameters
        ----------
        filepath : str
            Path to a DSC data file (TA .001, CSV, Excel, etc.) or
            a directory containing multiple DSC runs (isothermal series).
        """
        try:
            self._scans = load_project(filepath)
            if not self._scans:
                self.log(f"No valid DSC data found in: {filepath}")
                return False

            for i in range(len(self._scans)):
                self._scans[i] = normalise_scan(self._scans[i])
            self._raw_scans = copy.deepcopy(self._scans)

            summary = ", ".join(
                f"{s.label} ({len(s.T_C)} pts)" for s in self._scans
            )
            self.log(f"Loaded {len(self._scans)} scan(s): {summary}")
            return True
        except Exception as e:
            self.log(f"Failed to load data: {e}")
            logger.warning("DSC load failed.", exc_info=True)
            return False

    def preprocess(self) -> bool:
        """Preprocess all scans: calibrate, baseline correct, smooth.

        Applies DSCConfig settings.
        """
        if not self._scans:
            self.log("No data loaded")
            return False

        cfg = self._dsc_config

        for i, scan in enumerate(self._scans):
            try:
                self._scans[i] = preprocess_pipeline(scan, cfg)
                self.log(
                    f"  [{scan.label}] baseline={cfg.baseline_corr}, "
                    f"smooth={cfg.smooth_method}"
                )
            except Exception as e:
                self.log(f"  [{scan.label}] preprocessing failed: {e}")
                logger.warning("DSC preprocessing failed.", exc_info=True)
                return False

        self.log(f"Preprocessed {len(self._scans)} scan(s)")
        return True

    def analyze(self) -> bool:
        """Run core DSC analysis on all scans.

        Detects Tg, Tm, cold crystallisation, computes crystallinity,
        and deconvolves overlapping peaks.
        """
        if not self._scans:
            self.log("No preprocessed data")
            return False

        cfg = self._dsc_config
        self._results = []

        for scan in self._scans:
            DHm0 = cfg.get_crystallinity_ref(scan.label)
            result = analyze_scan(
                scan.T_C, scan.HF_Wg, cfg,
                label=scan.label,
                DHm0_override=DHm0,
                fit_observed_HF=scan.metadata.get('HF_pre_smooth'),
            )
            self._results.append(result)

            self.log(
                f"  [{result.label}] "
                + (f"Tg={result.Tg_C:.1f}°C " if not np.isnan(result.Tg_C) else "")
                + (f"Tm={result.Tm_peak_C:.1f}°C " if not np.isnan(result.Tm_peak_C) else "")
                + (f"Xc={result.Xc_pct:.1f}%" if not np.isnan(result.Xc_pct) else "")
            )

        if getattr(self, 'active_submodule', '') == 'dsc.isothermal':
            self.run_kinetics(mode='isothermal')
        elif getattr(self, 'active_submodule', '') == 'dsc.nonisothermal':
            self.run_kinetics(mode='non_isothermal')

        self._populate_diagnostic_raw_data()

        refresh_analysis_evidence(self)

        return True

    def build_figure_definitions(self):
        """Return mode-specific editable DSC publication definitions."""

        return build_dsc_figure_definitions(self)

    def plot(self, output_dir: str = "") -> Dict[str, str]:
        """Generate SCI-quality DSC figures.

        Returns dict of figure_name → filepath.
        """
        if not self._results:
            self.log("No analysis results to plot")
            return {}

        out = output_dir or self._dsc_config.output_dir or "dsc_output"
        definitions = tuple(self.build_figure_definitions())
        if definitions:
            dsc_publication_prefixes = (
                "dsc.standard.",
                "dsc.comparison.",
                "dsc.isothermal.",
                "dsc.nonisothermal.",
            )
            profile_id = (
                "dsc_publication"
                if any(
                    item.figure_id.startswith(dsc_publication_prefixes)
                    for item in definitions
                )
                else "paper_complete"
            )
            figures = self.publish_figure_definitions(
                out,
                definitions=definitions,
                profile_id=profile_id,
            )
        else:
            self.log("No figure definitions available")
            return {}

        for name, path in figures.items():
            self.log(f"  Figure saved: {path}")

        return figures

    def get_parameters(self) -> Dict[str, Any]:
        """Return merged parameters from all scans."""
        sub = getattr(self, 'active_submodule', '')
        if self._kinetics_data.get('thermal_program_segments'):
            rows: Dict[str, Any] = {
                'thermal_program_segments': list(self._kinetics_data['thermal_program_segments']),
            }
            for result in self._results:
                rows[result.label] = result.parameters
            if self._kinetics_data.get('avrami') is not None:
                a = self._kinetics_data['avrami']
                rows['best_avrami'] = self._avrami_parameter_row(a)
            for index, av in enumerate(self._kinetics_data.get('avrami_series', ()), start=1):
                label = f"segment_{index:02d}"
                if np.isfinite(getattr(av, 'temperature_C', np.nan)):
                    label += f"_{av.temperature_C:.1f}C"
                rows[label] = self._avrami_parameter_row(av)
            if self._kinetics_data.get('non_isothermal') is not None:
                rows.update(self._nonisothermal_parameter_rows())
            rows.update(self._validation_parameter_payload())
            return rows
        if sub == 'dsc.isothermal' and self._kinetics_data:
            rows: Dict[str, Any] = {}
            best = self._kinetics_data.get('avrami')
            if best is not None:
                rows['best_avrami'] = self._avrami_parameter_row(best)
            for i, av in enumerate(self._kinetics_data.get('avrami_series', []), start=1):
                label = f"segment_{i:02d}"
                if np.isfinite(getattr(av, 'temperature_C', np.nan)):
                    label += f"_{av.temperature_C:.1f}C"
                rows[label] = self._avrami_parameter_row(av)
            if rows:
                rows.update(self._validation_parameter_payload())
                return rows

        if sub == 'dsc.nonisothermal' and self._kinetics_data.get('non_isothermal') is not None:
            rows = self._nonisothermal_parameter_rows()
            rows.update(self._validation_parameter_payload())
            return rows

        if not self._results:
            return self._validation_parameter_payload()

        merged = {}
        for r in self._results:
            merged[r.label] = r.parameters
        if self._kinetics_data.get('avrami') is not None:
            a = self._kinetics_data['avrami']
            merged['isothermal_kinetics'] = {
                'Avrami_n': a.n,
                'Avrami_k': a.k,
                'Avrami_log_k': a.log_k,
                't_half_min': a.t_half_min,
                'T_iso_C': a.temperature_C,
                'DHc_iso_Jg': a.crystallisation_enthalpy_Jg,
                'Avrami_R2': a.r_squared,
                'n_segments': len(self._kinetics_data.get('avrami_series', [])),
            }
        if self._kinetics_data.get('non_isothermal') is not None:
            series = self._kinetics_data['non_isothermal']
            k = self._kinetics_data.get('kissinger')
            o = self._kinetics_data.get('ozawa')
            m = self._kinetics_data.get('mo')
            f = self._kinetics_data.get('friedman')
            friedman_vals = list(getattr(f, 'friedman_Ea', {}).values()) if f is not None else []
            merged['nonisothermal_kinetics'] = {
                'activation_energy': getattr(k, 'kissinger_Ea_kJmol', np.nan) if k is not None else np.nan,
                'Kissinger_Ea_kJmol': getattr(k, 'kissinger_Ea_kJmol', np.nan) if k is not None else np.nan,
                'Kissinger_R2': getattr(k, 'r_squared', np.nan) if k is not None else np.nan,
                'Ozawa_n': getattr(o, 'ozawa_n', np.nan) if o is not None else np.nan,
                'Ozawa_R2': getattr(o, 'r_squared', np.nan) if o is not None else np.nan,
                'Mo_a': getattr(m, 'mo_a', np.nan) if m is not None else np.nan,
                'Mo_F_T': getattr(m, 'mo_F_T', np.nan) if m is not None else np.nan,
                'Mo_R2': getattr(m, 'r_squared', np.nan) if m is not None else np.nan,
                'Friedman_Ea_mean_kJmol': float(np.nanmean(friedman_vals)) if friedman_vals else np.nan,
                'Friedman_Ea_by_X': getattr(f, 'friedman_Ea', {}) if f is not None else {},
                'n_curves': len(getattr(series, 'curves', [])),
                'rates_K_min': [c.rate_K_per_min for c in getattr(series, 'curves', [])],
                'Tp_C_list': [c.Tp_C for c in getattr(series, 'curves', [])],
                'DHc_Jg_list': [c.crystallisation_enthalpy_Jg for c in getattr(series, 'curves', [])],
                'quality_flags': getattr(series, 'quality_flags', []),
            }
        merged.update(self._validation_parameter_payload())
        return merged

    @staticmethod
    def _avrami_parameter_row(a: AvramiResult) -> Dict[str, Any]:
        return {
            'source': a.label,
            'Avrami_n': a.n,
            'Avrami_k': a.k,
            'Avrami_log_k': a.log_k,
            't_half_min': a.t_half_min,
            'T_iso_C': a.temperature_C,
            'DHc_iso_Jg': a.crystallisation_enthalpy_Jg,
            'Avrami_R2': a.r_squared,
            'candidate_id': a.candidate_id,
            'candidate_kind': a.candidate_kind,
            'integration_start_index': a.integration_start_index,
            'integration_end_index': a.integration_end_index,
            'transient_excluded': a.transient_excluded,
            'fit_Xt_min': a.fit_xt_range[0],
            'fit_Xt_max': a.fit_xt_range[1],
            'event_candidate_count': len(a.event_candidates),
            'event_candidates': a.event_candidates,
            'quality_flags': ", ".join(a.quality_flags),
        }

    def _nonisothermal_parameter_rows(self) -> Dict[str, Any]:
        series = self._kinetics_data['non_isothermal']
        k = self._kinetics_data.get('kissinger')
        o = self._kinetics_data.get('ozawa')
        m = self._kinetics_data.get('mo')
        f = self._kinetics_data.get('friedman')
        friedman_vals = list(getattr(f, 'friedman_Ea', {}).values()) if f is not None else []
        rows: Dict[str, Any] = {
            'nonisothermal_summary': {
                'Kissinger_Ea_kJmol': getattr(k, 'kissinger_Ea_kJmol', np.nan) if k is not None else np.nan,
                'Kissinger_R2': getattr(k, 'r_squared', np.nan) if k is not None else np.nan,
                'Ozawa_n': getattr(o, 'ozawa_n', np.nan) if o is not None else np.nan,
                'Ozawa_R2': getattr(o, 'r_squared', np.nan) if o is not None else np.nan,
                'Mo_a': getattr(m, 'mo_a', np.nan) if m is not None else np.nan,
                'Mo_F_T': getattr(m, 'mo_F_T', np.nan) if m is not None else np.nan,
                'Mo_R2': getattr(m, 'r_squared', np.nan) if m is not None else np.nan,
                'Friedman_Ea_mean_kJmol': float(np.nanmean(friedman_vals)) if friedman_vals else np.nan,
                'n_curves': len(getattr(series, 'curves', [])),
                'quality_flags': ", ".join(getattr(series, 'quality_flags', [])),
            }
        }
        for curve in getattr(series, 'curves', []):
            rows[f"cooling_{curve.rate_K_per_min:g}K_min"] = {
                'source': curve.label,
                'rate_K_min': curve.rate_K_per_min,
                'Tp_C': curve.Tp_C,
                'T_onset_C': curve.T_onset_C,
                'T_end_C': curve.T_end_C,
                'DHc_Jg': curve.crystallisation_enthalpy_Jg,
                'n_points': len(curve.Xt),
                'quality_flags': ", ".join(curve.quality_flags),
            }
        return rows

    def _populate_diagnostic_raw_data(self):
        """Populate optional AnalysisResult.raw_data for diagnostics."""
        rd = self.result.raw_data
        rd.clear()
        sub = getattr(self, 'active_submodule', '')

        if sub == 'dsc.isothermal':
            avrami = self._kinetics_data.get('avrami')
            if avrami is not None and len(getattr(avrami, 't_data', [])) > 0:
                rd['mode'] = 'isothermal_kinetics'
                rd['time_min'] = np.asarray(avrami.t_data, dtype=float)
                rd['relative_crystallinity'] = np.asarray(avrami.Xt_data, dtype=float)
                if len(getattr(avrami, 'Xt_fit', [])) > 0:
                    rd['relative_crystallinity_fit'] = np.asarray(avrami.Xt_fit, dtype=float)
                rd['label'] = avrami.label or 'Avrami'
                rd['temperature_C'] = avrami.temperature_C
                return

        if sub == 'dsc.nonisothermal':
            series = self._kinetics_data.get('non_isothermal')
            curves = getattr(series, 'curves', []) if series is not None else []
            if curves:
                first = curves[0]
                rd['mode'] = 'nonisothermal_kinetics'
                rd['temperature'] = np.asarray(first.T_xt_C, dtype=float)
                rd['relative_crystallinity'] = np.asarray(first.Xt, dtype=float)
                rd['time_min'] = np.asarray(first.t_xt_min, dtype=float)
                rd['label'] = first.label or 'Non-isothermal'
                rd['rates_K_min'] = [c.rate_K_per_min for c in curves]
                rd['curves'] = [
                    {
                        'label': c.label,
                        'rate_K_min': c.rate_K_per_min,
                        'temperature': np.asarray(c.T_xt_C, dtype=float),
                        'time_min': np.asarray(c.t_xt_min, dtype=float),
                        'relative_crystallinity': np.asarray(c.Xt, dtype=float),
                    }
                    for c in curves
                ]
                return

        if not self._scans:
            return

        scan = self._scans[0]
        if len(scan.T_C) > 0 and len(scan.HF_Wg) > 0:
            rd['mode'] = 'thermogram'
            rd['temperature'] = np.asarray(scan.T_C, dtype=float)
            rd['heat_flow'] = np.asarray(scan.HF_Wg, dtype=float)
            if len(scan.t_min) == len(scan.T_C):
                rd['time_min'] = np.asarray(scan.t_min, dtype=float)
            rd['label'] = scan.label or 'DSC'

    # ── v4.0 Validation ──────────────────────────────────────────────

    def _validate_results(self) -> bool:
        """DSC-specific post-analysis validation."""
        for r in self._results:
            had_range_issue = False
            had_range_issue |= self._check_param_range(r, "Tg_C",           -150, 300,   "Tg")
            had_range_issue |= self._check_param_range(r, "Tm_peak_C",       50,  400,   "Tm")
            had_range_issue |= self._check_param_range(r, "Xc_pct",           0,  100,   "Xc")
            had_range_issue |= self._check_param_range(r, "DHm_Jg",           0, 500,    "DHm")
            if r.Tm_peak_C > 0 and r.Xc_pct > 0.1:
                self.add_quality_flag(f"{r.label}/Xc", "OK")
            if had_range_issue or getattr(r, "quality_flags", []):
                self.add_quality_flag(f"{r.label}/validation", "WARN")
        self._refresh_result_validation_summary()
        return self.result.validation_passed

    def _refresh_result_validation_summary(self) -> None:
        """Mirror DSC validation state into the public result payload."""
        params = dict(getattr(self.result, "parameters", {}) or {})
        params.update(self._validation_parameter_payload())
        self.result.parameters = params

    def _validation_parameter_payload(self) -> Dict[str, Any]:
        """Return a compact validation snapshot for external consumers."""
        quality_flags = dict(getattr(self.result, "quality_flags", {}) or {})
        validation_warnings = list(getattr(self.result, "validation_warnings", []) or [])
        warn_items = [
            str(key)
            for key, flag in quality_flags.items()
            if str(flag).upper() == "WARN" and str(key).strip()
        ]
        error_items = [
            str(key)
            for key, flag in quality_flags.items()
            if str(flag).upper() == "ERROR" and str(key).strip()
        ]

        validation_warnings = list(dict.fromkeys(str(item) for item in validation_warnings if str(item).strip()))
        if not validation_warnings and warn_items:
            validation_warnings = warn_items

        if error_items:
            detail_items = error_items
            severity = "ERROR"
        elif validation_warnings:
            detail_items = validation_warnings
            severity = "WARN"
        else:
            detail_items = []
            severity = ""

        if severity:
            detail_text = ", ".join(detail_items[:6])
            suffix = f": {detail_text}" if detail_text else ""
            summary = f"{severity}: {len(detail_items)} issue(s){suffix}"
        else:
            summary = "All checks passed"

        return {
            "quality_flags": quality_flags,
            "validation_warnings": validation_warnings,
            "validation_summary": summary,
        }

    def _check_param_range(self, r, attr: str, lo: float, hi: float, label: str):
        val = getattr(r, attr, np.nan)
        if np.isnan(val):
            return False
        if val < lo or val > hi:
            self.add_quality_flag(f"{r.label}/{label}", "WARN")
            return True
        return False

    # ------------------------------------------------------------------
    #  Extended API  (not part of BaseEngine)
    # ------------------------------------------------------------------

    def set_config(self, **kwargs):
        """Update DSCConfig from keyword arguments.

        Example:
            engine.set_config(baseline_corr='tangential', Tg_method='half_height')
        """
        for k, v in kwargs.items():
            if hasattr(self._dsc_config, k):
                setattr(self._dsc_config, k, v)
            else:
                self.log(f"Warning: unknown config key '{k}'")

    def run_kinetics(self, mode: str = 'auto') -> Dict[str, Any]:
        """Run crystallisation kinetics analysis.

        Parameters
        ----------
        mode : str
            'isothermal', 'non_isothermal', 'auto'

        Returns
        -------
        dict with keys: avrami, ozawa, kissinger, friedman, mo
        """
        data = {}
        source_scans = self._raw_scans or self._scans
        if mode in ('isothermal', 'non_isothermal', 'auto') and source_scans:
            data['scans'] = source_scans
        if mode in ('isothermal', 'auto') and source_scans:
            data['isothermal_kwargs'] = {
                'min_duration_min': getattr(self._dsc_config, 'isothermal_min_duration_min', 1.0),
                'temp_tolerance_C': getattr(self._dsc_config, 'isothermal_temp_tolerance_C', 0.35),
                'max_drift_C_per_min': getattr(self._dsc_config, 'isothermal_max_drift_C_per_min', 0.12),
                'min_enthalpy_Jg': getattr(self._dsc_config, 'isothermal_min_enthalpy_Jg', 0.01),
            }
        if mode in ('non_isothermal', 'auto') and source_scans:
            data['nonisothermal_kwargs'] = {
                'min_delta_T_C': getattr(self._dsc_config, 'nonisothermal_min_delta_T_C', 20.0),
                'min_points': getattr(self._dsc_config, 'nonisothermal_min_points', 80),
                'min_enthalpy_Jg': getattr(self._dsc_config, 'nonisothermal_min_enthalpy_Jg', 0.01),
            }

        self._kinetics_data = analyze_kinetics(data, mode=mode)

        if 'avrami' in self._kinetics_data:
            a = self._kinetics_data['avrami']
            temp = f" at {a.temperature_C:.1f}C" if not np.isnan(a.temperature_C) else ""
            self.log(f"Avrami{temp}: n={a.n:.2f}, k={a.k:.2e}, t1/2={a.t_half_min:.2f} min")
        if 'avrami_series' in self._kinetics_data:
            n_valid = sum(1 for a in self._kinetics_data['avrami_series'] if not np.isnan(a.n))
            self.log(f"Isothermal segments fitted: {n_valid}/{len(self._kinetics_data['avrami_series'])}")
        if 'kissinger' in self._kinetics_data:
            k = self._kinetics_data['kissinger']
            if np.isfinite(k.kissinger_Ea_kJmol):
                self.log(f"Kissinger Ea={k.kissinger_Ea_kJmol:.1f} kJ/mol")
        if 'non_isothermal' in self._kinetics_data:
            series = self._kinetics_data['non_isothermal']
            curves = getattr(series, 'curves', [])
            if curves:
                rates = ", ".join(f"{c.rate_K_per_min:g}" for c in curves)
                self.log(f"Non-isothermal cooling curves fitted: {len(curves)} rate(s): {rates} K/min")

        return self._kinetics_data

    def run_thermal_program_template(self, template: Any) -> Dict[str, Any]:
        """Execute all role-tagged segments from one thermal-program template.

        Heating and cooling segments use the standard thermal-event analysis;
        qualified isothermal holds use the existing Avrami implementation.
        """
        from .canonical_experiments import CanonicalExperiment

        if not isinstance(template, CanonicalExperiment):
            raise TypeError("DSC canonical execution requires a CanonicalExperiment")
        validated_template = CanonicalExperiment.from_dict(template.to_dict())
        if validated_template.template_id not in {"dsc.isothermal.v1", "thermal_program.v1"}:
            raise ValueError("DSC canonical execution requires dsc.isothermal.v1 or thermal_program.v1")
        payload = validated_template.payload
        segments = payload.get("segments") if isinstance(payload, dict) else payload.get("segments")
        if not isinstance(segments, tuple) or not segments:
            raise ValueError("DSC canonical template has no thermal-program segments")
        sample = payload.get("sample", {})
        mass_value = sample.get("mass_mg")
        if mass_value is None:
            raise ValueError("DSC canonical template has no sample mass")
        mass_mg = float(mass_value)
        if not np.isfinite(mass_mg) or mass_mg <= 0:
            raise ValueError("DSC canonical template has an invalid sample mass")

        scans: List[DSCScan] = []
        isothermal_scans: List[DSCScan] = []
        thermal_roles: list[dict[str, str]] = []
        for segment in segments:
            role = str(segment.get("role", ""))
            if role not in {"heating", "cooling", "isothermal_crystallization"}:
                raise ValueError("DSC canonical template contains an unsupported segment role")
            time_s = np.asarray(segment.get("time_s", ()), dtype=float)
            temperature = np.asarray(segment.get("sample_temperature_C", ()), dtype=float)
            heat_flow_mw = np.asarray(segment.get("heat_flow_mW", ()), dtype=float)
            if len(time_s) < 2 or len(time_s) != len(temperature) or len(time_s) != len(heat_flow_mw):
                raise ValueError("DSC canonical segment has inconsistent arrays")
            if not (
                np.all(np.isfinite(time_s))
                and np.all(np.isfinite(temperature))
                and np.all(np.isfinite(heat_flow_mw))
                and np.all(np.diff(time_s) > 0)
            ):
                raise ValueError("DSC canonical segment arrays are invalid")
            if (
                role == "isothermal_crystallization"
                and validated_template.template_id == "dsc.isothermal.v1"
                and not self._canonical_segment_is_qualified(
                    time_s, temperature, segment.get("setpoint_C")
                )
            ):
                raise ValueError("DSC canonical segment does not meet canonical kinetic qualification")
            quality_warnings = list(segment.get("quality_warnings", ()))
            quality_warnings.extend(
                self._canonical_segment_quality_warnings(
                    time_s, temperature, segment.get("setpoint_C")
                )
            )
            quality_warnings = list(dict.fromkeys(str(item) for item in quality_warnings))
            scan = DSCScan(
                    label=str(segment.get("segment_id", "isothermal")),
                    T_C=temperature,
                    HF_mW=heat_flow_mw,
                    HF_Wg=heat_flow_mw / mass_mg,
                    t_min=time_s / 60.0,
                    mass_mg=mass_mg,
                    rate_K_per_min=float(segment.get("rate_K_per_min", 0.0)),
                    metadata={
                        "canonical_template_id": validated_template.template_id,
                        "source_range": dict(segment.get("source_range", {})),
                        "quality_warnings": quality_warnings,
                    },
                )
            scans.append(scan)
            thermal_roles.append({"segment_id": scan.label, "role": role})
            if role == "isothermal_crystallization":
                isothermal_scans.append(scan)

        roles_present = {item["role"] for item in thermal_roles}
        self.active_submodule = (
            "dsc.isothermal"
            if roles_present == {"isothermal_crystallization"}
            else "dsc.standard"
        )
        self._scans = scans
        self._raw_scans = copy.deepcopy(scans)
        self._results = []
        for scan, role_info in zip(scans, thermal_roles):
            if role_info["role"] in {"heating", "cooling"}:
                self._results.append(
                    analyze_scan(
                        scan.T_C,
                        scan.HF_Wg,
                        self._dsc_config,
                        label=scan.label,
                        DHm0_override=self._dsc_config.get_crystallinity_ref(scan.label),
                    )
                )
        kinetics = IsothermalKineticsResult()
        min_enthalpy = getattr(self._dsc_config, "isothermal_min_enthalpy_Jg", 0.01)
        for scan in isothermal_scans:
            segment = IsothermalSegment(
                label=scan.label,
                temperature_C=float(np.nanmedian(scan.T_C)),
                start_index=0,
                end_index=len(scan.T_C) - 1,
                start_time_min=float(scan.t_min[0]),
                end_time_min=float(scan.t_min[-1]),
                duration_min=float(scan.t_min[-1] - scan.t_min[0]),
                T_C=scan.T_C.copy(),
                HF_Wg=scan.HF_Wg.copy(),
                t_min=scan.t_min.copy(),
            )
            candidates = avrami_candidates_from_dsc(segment.t_min, segment.HF_Wg)
            if not candidates:
                candidates = [avrami_from_dsc(segment.t_min, segment.HF_Wg)]
            for avrami in candidates:
                avrami.label = segment.label
                avrami.temperature_C = segment.temperature_C
                if np.isnan(avrami.start_time_min):
                    avrami.start_time_min = segment.start_time_min
                if np.isnan(avrami.end_time_min):
                    avrami.end_time_min = segment.end_time_min
                for warning in scan.metadata.get("quality_warnings", ()):
                    if warning not in avrami.quality_flags:
                        avrami.quality_flags.append(warning)
                if (
                    np.isfinite(avrami.crystallisation_enthalpy_Jg)
                    and avrami.crystallisation_enthalpy_Jg < min_enthalpy
                ):
                    avrami.quality_flags.append("low_crystallisation_enthalpy")
                kinetics.avrami_results.append(avrami)
            kinetics.segments.append(segment)
        valid = [
            item for item in kinetics.avrami_results
            if np.isfinite(item.n)
            and np.isfinite(item.r_squared)
            and "low_crystallisation_enthalpy" not in item.quality_flags
        ]
        if valid:
            kinetics.best = max(
                valid,
                key=lambda item: (
                    len(item.quality_flags) == 0,
                    item.r_squared,
                    item.crystallisation_enthalpy_Jg
                    if np.isfinite(item.crystallisation_enthalpy_Jg)
                    else 0.0,
                ),
            )
        else:
            kinetics.quality_flags.append("no_valid_avrami_fit")
        self._kinetics_data = {
            "thermal_program_segments": thermal_roles,
            "isothermal": kinetics,
            "avrami_series": kinetics.avrami_results,
        }
        cooling_scans = [
            scan for scan, role_info in zip(scans, thermal_roles)
            if role_info["role"] == "cooling"
        ]
        if len(cooling_scans) >= 3:
            nonisothermal = analyze_nonisothermal_scans(
                cooling_scans,
                min_delta_T_C=getattr(self._dsc_config, "nonisothermal_min_delta_T_C", 20.0),
                min_points=getattr(self._dsc_config, "nonisothermal_min_points", 80),
                min_enthalpy_Jg=getattr(self._dsc_config, "nonisothermal_min_enthalpy_Jg", 0.01),
            )
            self._kinetics_data["non_isothermal"] = nonisothermal
            self._kinetics_data["ozawa"] = nonisothermal.ozawa
            self._kinetics_data["mo"] = nonisothermal.mo
            self._kinetics_data["friedman"] = nonisothermal.friedman
            self._kinetics_data["kissinger"] = nonisothermal.kissinger
        if np.isfinite(kinetics.best.n):
            self._kinetics_data["avrami"] = kinetics.best
        output = self._kinetics_data
        output["canonical_provenance"] = {
            "template_id": validated_template.template_id,
            "template_hash": validated_template.content_hash,
            "conversion_hash": validated_template.conversion_record.conversion_hash,
            "source_artifact_id": validated_template.source_artifact_id,
        }
        self.result.parameters = _json_safe_parameters(self.get_parameters())
        return output

    def run_isothermal_template(self, template: Any) -> Dict[str, Any]:
        """Backward-compatible alias for the unified thermal-program executor."""
        return self.run_thermal_program_template(template)

    def _canonical_segment_is_qualified(
        self,
        time_s: np.ndarray,
        temperature_C: np.ndarray,
        setpoint_C: Any,
    ) -> bool:
        """Validate already-mapped holds without re-segmenting their provenance."""
        try:
            float(setpoint_C)
        except (TypeError, ValueError):
            return False
        min_points = 30
        min_duration_s = float(getattr(self._dsc_config, "isothermal_min_duration_min", 1.0)) * 60.0
        if len(time_s) < min_points or float(time_s[-1] - time_s[0]) < min_duration_s:
            return False
        return True

    @staticmethod
    def _canonical_segment_quality_warnings(
        time_s: np.ndarray,
        temperature_C: np.ndarray,
        setpoint_C: Any,
    ) -> list[str]:
        """Report temperature quality observations without blocking analysis."""
        try:
            setpoint = float(setpoint_C)
        except (TypeError, ValueError):
            return ["setpoint_unavailable"]
        warnings: list[str] = []
        if np.max(np.abs(temperature_C - setpoint)) > 0.5:
            warnings.append("sample_temperature_outside_stability_tolerance")
        if float(np.ptp(temperature_C)) > 0.5:
            warnings.append("sample_temperature_span_exceeds_tolerance")
        if float(np.std(temperature_C)) > 0.05:
            warnings.append("sample_temperature_noise_exceeds_tolerance")
        if len(time_s) > 1:
            slope_C_per_min = abs(float(np.polyfit(time_s, temperature_C, 1)[0])) * 60.0
            if slope_C_per_min > 0.12:
                warnings.append("sample_temperature_drift_exceeds_tolerance")
        return warnings

    @property
    def results(self) -> List[DSCResult]:
        """Access raw DSCResult objects."""
        return self._results

    @property
    def scans(self) -> List[DSCScan]:
        """Access raw DSCScan objects."""
        return self._scans

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    def _ensure_exo_up(self, scan: DSCScan) -> DSCScan:
        """Ensure the scan uses exo-up convention (IUPAC).

        Auto-detects and flips if the data appears to be exo-down.
        """
        if len(scan.HF_Wg) < 10:
            return scan

        # Heuristic: crystallisation exotherm should be positive
        # In heating curves, the dominant endotherm (melting) pushes mean negative
        # If mean is positive, it's likely exo-down on a cooling curve → flip
        dHF = np.gradient(scan.HF_Wg)

        # Priority: already declared by the reader
        if scan.exo_up:
            return scan

        if np.min(dHF) < -3 * np.std(dHF) and np.mean(scan.HF_Wg) < 0:
            scan.exo_up = True
            return scan

        # If the largest positive derivative dominates, check if it's crystallisation
        # In exo-up, crystallisation = positive peak → flip if negative peaks dominate
        neg_energy = np.trapezoid(np.abs(scan.HF_Wg[scan.HF_Wg < 0]),
                                   scan.T_C[scan.HF_Wg < 0])
        pos_energy = np.trapezoid(scan.HF_Wg[scan.HF_Wg > 0],
                                   scan.T_C[scan.HF_Wg > 0])

        # Flip only if positive energy clearly dominates (ratio > 1.5 avoids false positives)
        if pos_energy > 1.5 * neg_energy and neg_energy > 1e-6:
            scan.HF_mW = -scan.HF_mW
            scan.HF_Wg = -scan.HF_Wg
            scan.exo_up = True
            self.log("Detected exo-down convention → flipped to exo-up")

        return scan
