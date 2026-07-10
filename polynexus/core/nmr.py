"""NMR spectroscopy analysis engine."""

from __future__ import annotations
import logging
logger = logging.getLogger(__name__)


import os
from typing import Any, Dict, List

import numpy as np

from .engine import BaseEngine, EngineCategory, register_technique
from .submodule_registry import SubModuleSpec, register_submodule
from .nmr_engine import (
    NMRConfig,
    NMRRelaxation,
    NMRResult,
    NMRSpectrum,
    ComputedShift,
    analyze_spectrum,
    generate_all_figures,
    load_computed_shifts,
    load_project,
    load_relaxation,
    preprocess_pipeline,
)
from .nmr_engine.io import (
    infer_nucleus, infer_sample_state,
    NMR_EXTS, NMR_OUTPUT_DIRS,
)  # fmt: off


def _expected_from_submodule(submodule_id: str | None) -> tuple[str | None, str | None]:
    mapping = {
        "nmr.liquid_h": ("liquid", "1H"),
        "nmr.liquid_c": ("liquid", "13C"),
        "nmr.solid_h": ("solid", "1H"),
        "nmr.solid_c": ("solid", "13C"),
    }
    return mapping.get(submodule_id or "", (None, None))


def _normalise_nucleus(value: str | None) -> str:
    text = str(value or "").upper()
    if text in {"H", "1H", "PROTON"}:
        return "1H"
    if text in {"C", "13C", "CARBON", "CARBON13"}:
        return "13C"
    return text


def _strong_state_hint(path: str) -> str | None:
    state = infer_sample_state(path, fallback="")
    return state if state in {"liquid", "solid"} else None


def _nucleus_hint_from_file(path: str) -> str | None:
    ext = os.path.splitext(path)[1].lower()
    text_hint = _normalise_nucleus(infer_nucleus(path, fallback=""))
    if ext in {".jdf", ".bin"}:
        try:
            with open(path, "rb") as fh:
                head = fh.read(4096).decode("latin1", errors="ignore").lower()
            if "carbon13" in head or "carbon" in head:
                return "13C"
            if "proton" in head:
                return "1H"
        except OSError:
            pass
    return text_hint or None


def _has_nmr_files(filepath: str) -> list[str]:
    """Quick shallow scan for NMR-compatible files (no recursive walk).

    Returns a list of matching filenames (up to 8) for nucleus hint scanning.
    """
    if not os.path.isdir(filepath):
        base = os.path.basename(filepath).lower()
        if base == "fid" or os.path.splitext(base)[1] in NMR_EXTS:
            return [filepath]
        return []
    matches: list[str] = []
    try:
        for entry in os.scandir(filepath):
            if entry.is_dir():
                continue
            name = entry.name.lower()
            if name == "fid" or os.path.splitext(name)[1] in NMR_EXTS:
                matches.append(entry.path)
                if len(matches) >= 8:
                    break
        return matches
    except OSError:
        return []


def _nmr_schema(nucleus: str, sample_state: str) -> Dict[str, Dict[str, Any]]:
    peak_distance = 0.08 if nucleus == "1H" and sample_state == "liquid" else 1.0
    if nucleus == "1H" and sample_state == "solid":
        peak_distance = 0.25
    peak_shape = "lorentzian" if sample_state == "liquid" else "mixed"
    default_height = 0.03 if nucleus == "13C" else 0.04
    default_max_peaks = 18 if nucleus == "13C" else (12 if sample_state == "liquid" else 24)
    default_baseline = "simple_polynomial" if sample_state == "liquid" else "polynomial"
    return {
        "baseline_method": {
            "type": "choice",
            "options": ["polynomial", "spline", "linear", "simple_polynomial"],
            "default": default_baseline,
            "label": "Baseline",
        },
        "deconvolution_method": {
            "type": "choice",
            "options": ["gaussian", "lorentzian", "mixed"],
            "default": peak_shape,
            "label": "Peak shape",
        },
        "peak_height_min": {
            "type": "float",
            "min": 0.005,
            "max": 0.2,
            "default": default_height,
            "decimals": 3,
            "label": "Peak threshold",
        },
        "peak_distance_ppm": {
            "type": "float",
            "min": 0.01,
            "max": 5.0,
            "default": peak_distance,
            "decimals": 3,
            "label": "Min peak distance",
        },
        "max_peaks": {
            "type": "int",
            "min": 4,
            "max": 60,
            "default": default_max_peaks,
            "label": "Max peaks",
        },
        "polymer_name": {
            "type": "string",
            "default": "",
            "label": "Polymer",
        },
        "allow_unscoped_polymer_db_match": {
            "type": "bool",
            "default": False,
            "label": "Use full polymer DB",
        },
    }


@register_technique("nmr")
@register_submodule(SubModuleSpec(
    id="nmr.liquid_h",
    parent_technique="nmr",
    label="Liquid 1H NMR",
    icon="H",
    description="Liquid-state proton NMR from raw FID or table spectra",
    priority=40,
    accepted_formats=["directory", "fid", "*.csv", "*.txt", "*.dat"],
    input_mode="single",
    config_schema=_nmr_schema("1H", "liquid"),
    output_parameters=[
        {"key": "n_peaks", "label": "Peaks", "format": "d"},
        {"key": "dominant_peak_ppm", "label": "Main peak (ppm)", "format": ".2f"},
        {"key": "median_snr", "label": "Median SNR", "format": ".1f"},
        {"key": "mean_fwhm_ppm", "label": "Mean FWHM", "format": ".3f"},
    ],
    figure_types=["spectrum", "deconvolution"],
))
@register_submodule(SubModuleSpec(
    id="nmr.liquid_c",
    parent_technique="nmr",
    label="Liquid 13C NMR",
    icon="C",
    description="Liquid-state carbon NMR from raw FID or table spectra",
    priority=30,
    accepted_formats=["directory", "fid", "*.csv", "*.txt", "*.dat"],
    input_mode="single",
    config_schema=_nmr_schema("13C", "liquid"),
    output_parameters=[
        {"key": "n_peaks", "label": "Peaks", "format": "d"},
        {"key": "dominant_peak_ppm", "label": "Main peak (ppm)", "format": ".2f"},
        {"key": "median_snr", "label": "Median SNR", "format": ".1f"},
        {"key": "mean_fwhm_ppm", "label": "Mean FWHM", "format": ".3f"},
    ],
    figure_types=["spectrum", "deconvolution"],
))
@register_submodule(SubModuleSpec(
    id="nmr.solid_h",
    parent_technique="nmr",
    label="Solid 1H NMR",
    icon="H",
    description="Solid-state proton NMR, including JEOL.NMR containers",
    priority=20,
    accepted_formats=["directory", "*.jdf", "*.bin", "*.csv", "*.txt", "*.dat"],
    input_mode="single",
    config_schema=_nmr_schema("1H", "solid"),
    output_parameters=[
        {"key": "n_peaks", "label": "Peaks", "format": "d"},
        {"key": "dominant_peak_ppm", "label": "Main peak (ppm)", "format": ".2f"},
        {"key": "median_snr", "label": "Median SNR", "format": ".1f"},
        {"key": "mean_fwhm_ppm", "label": "Mean FWHM", "format": ".3f"},
    ],
    figure_types=["spectrum", "deconvolution"],
))
@register_submodule(SubModuleSpec(
    id="nmr.solid_c",
    parent_technique="nmr",
    label="Solid 13C NMR",
    icon="C",
    description="Solid-state carbon CP/MAS NMR with phase assignment and Xc estimate",
    priority=10,
    accepted_formats=["directory", "*.jdf", "*.bin", "*.csv", "*.txt", "*.dat"],
    input_mode="single",
    config_schema=_nmr_schema("13C", "solid"),
    output_parameters=[
        {"key": "n_peaks", "label": "Peaks", "format": "d"},
        {"key": "dominant_peak_ppm", "label": "Main peak (ppm)", "format": ".2f"},
        {"key": "median_snr", "label": "Median SNR", "format": ".1f"},
        {"key": "mean_fwhm_ppm", "label": "Mean FWHM", "format": ".3f"},
        {"key": "Xc_pct", "label": "Xc (%)", "format": ".1f"},
    ],
    figure_types=["cp_mas_spectrum", "deconvolution", "phase_composition"],
))
class NMREngine(BaseEngine):
    """NMR spectroscopy analysis engine."""

    name = "nmr"
    label = "NMR"
    icon = "NMR"
    category = EngineCategory.HYBRID
    description = "NMR spectroscopy: liquid/solid 1H and 13C analysis"

    def __init__(self, config=None, log_fn=None):
        super().__init__(config=config, log_fn=log_fn)
        if isinstance(config, NMRConfig):
            self._cfg = config
        else:
            self._cfg = NMRConfig.with_defaults(**(config or {}))
        self._spectra: List[NMRSpectrum] = []
        self._results: List[NMRResult] = []
        self._computed: List[ComputedShift] = []
        self._relax: NMRRelaxation | None = None
        self._user_config_keys = set(config.keys()) if isinstance(config, dict) else set()
        if isinstance(config, dict):
            self.set_config(**config)

    def _apply_submodule_defaults(self):
        defaults = self._cfg.SUBMODULE_DEFAULTS.get(getattr(self, "active_submodule", ""))
        if not defaults:
            return
        for key, value in defaults.items():
            if key not in self._user_config_keys:
                setattr(self._cfg, key, value)

    def _filter_spectra_for_active_submodule(self, filepath: str) -> bool:
        expected_state, expected_nucleus = _expected_from_submodule(self.active_submodule)
        if not expected_state or not expected_nucleus:
            return bool(self._spectra)

        kept: list[NMRSpectrum] = []
        skipped: list[str] = []
        for spec in self._spectra:
            spec_nucleus = _normalise_nucleus(spec.nucleus)
            source_path = str(spec.metadata.get("filename") or filepath)
            source_state = _strong_state_hint(source_path)
            state_ok = source_state is None or source_state == expected_state
            nucleus_ok = spec_nucleus == expected_nucleus
            if state_ok and nucleus_ok:
                spec.metadata["sample_state"] = expected_state
                spec.nucleus = expected_nucleus
                kept.append(spec)
            else:
                reason = []
                if not nucleus_ok:
                    reason.append(f"{spec_nucleus or 'unknown'} != {expected_nucleus}")
                if not state_ok:
                    reason.append(f"{source_state} != {expected_state}")
                skipped.append(f"{spec.label} ({', '.join(reason)})")

        if skipped:
            self.log("Skipped incompatible NMR spectra for current partition:")
            for item in skipped[:6]:
                self.log(f"  - {item}")
            if len(skipped) > 6:
                self.log(f"  ... {len(skipped) - 6} more")

        self._spectra = kept
        if not self._spectra:
            self.log(
                f"No spectra match {self.active_submodule}: expected "
                f"{expected_state} {expected_nucleus}. Please choose the matching NMR partition."
            )
            return False
        return True

    def load(self, filepath):
        try:
            self._apply_submodule_defaults()
            ok, msg = self.check_file_compatibility(filepath)
            if not ok:
                self.log(msg)
                return False
            state = self._cfg.sample_state if self.active_submodule else None
            nucleus = self._cfg.nucleus if self.active_submodule else None
            self._spectra = load_project(filepath, sample_state=state, nucleus=nucleus)
            if not self._spectra:
                self.log("No NMR data")
                return False
            if not self._filter_spectra_for_active_submodule(filepath):
                return False
            if not self.active_submodule:
                first = self._spectra[0]
                self._cfg.nucleus = first.nucleus or self._cfg.nucleus
                self._cfg.sample_state = first.metadata.get("sample_state", self._cfg.sample_state)
            for spec in self._spectra:
                state_label = spec.metadata.get("sample_state", self._cfg.sample_state)
                fmt = spec.metadata.get("format", "unknown")
                self.log(
                    f"  {spec.label} ({len(spec.ppm)} pts, "
                    f"{state_label} {spec.nucleus}, format={fmt})"
                )
            return True
        except Exception as exc:
            self.log(f"Load failed: {exc}")
            logger.warning("NMR load failed.", exc_info=True)
            return False

    def load_computed(self, filepath):
        try:
            self._computed = load_computed_shifts(filepath)
            self.log(f"Loaded {len(self._computed)} computed shifts")
            return len(self._computed) > 0
        except Exception as exc:
            self.log(f"Comp load failed: {exc}")
            logger.warning("NMR computed shifts load failed.", exc_info=True)
            return False

    def load_relaxation(self, dirpath, rtype="T1"):
        try:
            self._relax = load_relaxation(dirpath, rtype)
            self.log(f"Relaxation: {len(self._relax.delay_values)} delays")
            return True
        except Exception as exc:
            self.log(f"Relax load failed: {exc}")
            logger.warning("NMR relaxation load failed.", exc_info=True)
            return False

    def preprocess(self):
        if not self._spectra:
            self.log("No data")
            return False
        for idx, spec in enumerate(self._spectra):
            try:
                self._spectra[idx] = preprocess_pipeline(spec, self._cfg)
                self.log(f"  [{spec.label}] baseline={self._cfg.baseline_method}")
            except Exception as exc:
                self.log(f"  [{spec.label}] prep failed: {exc}")
                logger.warning("NMR preprocessing failed.", exc_info=True)
                return False
        return True

    def analyze(self):
        if not self._spectra:
            self.log("No preprocessed data")
            return False
        self._results = []
        for spec in self._spectra:
            result = analyze_spectrum(
                spec,
                self._cfg,
                label=spec.label,
                computed_shifts=self._computed if self._computed else None,
                relaxation_data=self._relax,
            )
            self._results.append(result)
            xc = f" Xc={result.Xc_pct:.1f}" if np.isfinite(result.Xc_pct) else ""
            snr = f" SNR={result.median_snr:.1f}" if np.isfinite(result.median_snr) else ""
            main = (
                f" main={result.dominant_peak_ppm:.2f} ppm"
                if np.isfinite(result.dominant_peak_ppm) else ""
            )
            self.log(
                f"  [{result.label}] {result.sample_state} {result.nucleus} "
                f"peaks={result.n_peaks}{main}{snr}{xc}"
            )

        first = self._spectra[0]
        self.result.raw_data["ppm"] = np.asarray(first.ppm, dtype=float)
        self.result.raw_data["intensity"] = np.asarray(first.intensity, dtype=float)
        self.result.raw_data["label"] = first.label or "NMR"
        self.result.metadata.update({
            "submodule": getattr(self, "active_submodule", "") or "auto",
            "nucleus": first.nucleus,
            "sample_state": first.metadata.get("sample_state", self._cfg.sample_state),
            "spectra_count": str(len(self._results)),
        })
        if self._results:
            first_result = self._results[0]
            if np.isfinite(first_result.dominant_peak_ppm):
                self.result.metadata["dominant_peak_ppm"] = f"{first_result.dominant_peak_ppm:.6g}"
            if np.isfinite(first_result.median_snr):
                self.result.metadata["median_snr"] = f"{first_result.median_snr:.6g}"
        return True

    def build_figure_definitions(self):
        """Return scientific figure definitions without publishing assets."""

        from .nmr_engine.figure_provider import build_nmr_figure_definitions

        return build_nmr_figure_definitions(tuple(self._results))

    def plot(self, output_dir=""):
        if not self._results:
            self.log("No results")
            return {}
        out = output_dir or self._cfg.output_dir or "nmr_output"
        figs = generate_all_figures(self._results, out, config=self._cfg)
        for _, path in figs.items():
            self.log(f"  Figure: {path}")
        return figs

    def get_parameters(self):
        if not self._results:
            return {}
        return {result.label: result.parameters for result in self._results}

    def check_file_compatibility(self, filepath: str) -> tuple[bool, str]:
        if not os.path.exists(filepath):
            return False, f"File not found: {filepath}"
        files = _has_nmr_files(filepath)
        if not files:
            return False, "NMR expects fid, JEOL .jdf/.bin, or two-column table files."

        expected_state, expected_nucleus = _expected_from_submodule(self.active_submodule)
        if not expected_state or not expected_nucleus:
            return True, ""

        state_hint = _strong_state_hint(filepath)
        if state_hint and state_hint != expected_state:
            return (
                False,
                f"Current NMR partition is {expected_state} {expected_nucleus}, "
                f"but the selected path looks like {state_hint} NMR. "
                "Please switch to the matching liquid/solid H/C partition.",
            )

        nucleus_hints = {
            hint for hint in (_nucleus_hint_from_file(f) for f in files)
            if hint
        }
        if nucleus_hints and expected_nucleus not in nucleus_hints:
            return (
                False,
                f"Current NMR partition is {expected_state} {expected_nucleus}, "
                f"but the selected data looks like {', '.join(sorted(nucleus_hints))}. "
                "Please switch to the matching H/C partition.",
            )
        return True, ""

    def _validate_results(self) -> bool:
        for result in self._results:
            if result.n_peaks <= 0:
                self.add_quality_flag(f"{result.label}/NMR_peaks", "WARN")
            else:
                self.add_quality_flag(f"{result.label}/NMR_peaks", "OK")
            if np.isfinite(result.median_snr):
                if result.median_snr < 5.0:
                    self.add_quality_flag(f"{result.label}/NMR_SNR", "WARN")
                else:
                    self.add_quality_flag(f"{result.label}/NMR_SNR", "OK")
            if np.isfinite(result.mean_fwhm_ppm):
                state = str(result.sample_state).lower()
                nuc = str(result.nucleus).upper()
                warn_fwhm = 0.35 if state == "liquid" and nuc in {"1H", "H"} else None
                if warn_fwhm is not None and result.mean_fwhm_ppm > warn_fwhm:
                    self.add_quality_flag(f"{result.label}/NMR_linewidth", "WARN")
                else:
                    self.add_quality_flag(f"{result.label}/NMR_linewidth", "OK")
            if np.isfinite(result.r_squared):
                if result.r_squared < -10.0:
                    self.add_quality_flag(f"{result.label}/NMR_fit_R2", "ERROR")
                elif result.r_squared < 0.5:
                    self.add_quality_flag(f"{result.label}/NMR_fit_R2", "WARN")
                else:
                    self.add_quality_flag(f"{result.label}/NMR_fit_R2", "OK")
            if np.isfinite(result.Xc_pct):
                if result.Xc_pct < 0 or result.Xc_pct > 100:
                    self.add_quality_flag(f"{result.label}/Xc_NMR", "ERROR")
                else:
                    self.add_quality_flag(f"{result.label}/Xc_NMR", "OK")
            elif (
                str(result.sample_state).lower() == "solid"
                and str(result.nucleus).upper() in {"13C", "C"}
                and result.Xc_method == "requires_crystalline_amorphous_assignment"
            ):
                self.add_quality_flag(f"{result.label}/Xc_NMR_assignment", "WARN")
        return self.result.validation_passed

    def set_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self._cfg, key):
                setattr(self._cfg, key, value)

    @property
    def results(self):
        return self._results
