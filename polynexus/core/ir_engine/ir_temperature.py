"""In-situ temperature 2D IR analysis.

Builds a condition-by-wavenumber matrix from a sequence of ordinary IR
spectra, then tracks band indices and representative band intensities.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .config import IRConfig
from .core import IRResult, analyze_spectrum, measure_band_height
from .io import IRSpectrum
from .preprocess import baseline_mute_zone
from .names import normalize_ir_polymer_database, normalize_ir_polymer_name
from ..plot_edits import savefig_with_edits


PA6_TRACKED_BANDS = {
    "N-H": 3298.0,
    "CH2_asym": 2931.0,
    "CH2_sym": 2860.0,
    "amide_I": 1637.0,
    "amide_II": 1541.0,
    "CH2_bend": 1463.0,
    "amide_III": 1263.0,
    "cryst_1200": 1200.0,
    "skeletal_1120": 1120.0,
    "amide_V_929": 929.0,
}


@dataclass
class IRTempFrame:
    label: str = ""
    stage: str = "sequence"
    sequence_order_source: str = "index"
    temperature_C: float = np.nan
    time_min: float = np.nan
    time_estimated: bool = False
    order: float = 0.0
    spectrum: Optional[IRSpectrum] = None
    result: Optional[IRResult] = None


@dataclass
class IRTemp2DResult:
    label: str = "IR temperature series"
    frames: List[IRTempFrame] = field(default_factory=list)
    wavenumber: np.ndarray = field(default_factory=lambda: np.array([]))
    absorbance_matrix: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    band_names: List[str] = field(default_factory=list)
    band_positions: List[float] = field(default_factory=list)
    band_intensity_vs_frame: Dict[str, List[float]] = field(default_factory=dict)
    band_indices_vs_frame: Dict[str, List[float]] = field(default_factory=dict)
    dynamic_matrix: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    sync_corr: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    async_corr: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    neg_fraction: float = 0.0
    sync_cross_peaks: List[Dict[str, Any]] = field(default_factory=list)
    async_cross_peaks: List[Dict[str, Any]] = field(default_factory=list)
    transitions: List[Dict[str, Any]] = field(default_factory=list)
    cross_peak_assignment_summary: Dict[str, Any] = field(default_factory=dict)
    band_index_transition_summary: Dict[str, Any] = field(default_factory=dict)

    @property
    def temperatures(self) -> List[float]:
        return [f.temperature_C for f in self.frames]

    @property
    def stages(self) -> List[str]:
        return [f.stage for f in self.frames]

    @property
    def results(self) -> List[IRResult]:
        return [f.result for f in self.frames if f.result is not None]

    @property
    def parameters(self) -> Dict[str, Any]:
        temps = [float(t) for t in self.temperatures if np.isfinite(t)]
        stage_counts: Dict[str, int] = {}
        stage_sequence: List[str] = []
        order_sources: List[str] = []
        wavenumber_lengths: List[int] = []
        frame_rms_values: List[float] = []
        frame_peak_values: List[float] = []
        frame_polymer_scores: List[float] = []
        frame_assignment_confidence: List[float] = []
        frame_key_band_support: List[float] = []
        temperature_missing_count = 0
        time_missing_count = 0
        time_estimated_count = 0
        hold_time_missing_count = 0
        hold_time_estimated_count = 0
        heating_temps: List[float] = []
        cooling_temps: List[float] = []
        hold_times: List[float] = []
        for frame in self.frames:
            stage = str(frame.stage or "").strip().lower()
            if stage:
                stage_sequence.append(stage)
            order_source = str(getattr(frame, "sequence_order_source", "") or "").strip().lower()
            if order_source:
                order_sources.append(order_source)
            if stage:
                stage_counts[stage] = stage_counts.get(stage, 0) + 1
            if frame.spectrum is not None and frame.spectrum.wavenumber is not None:
                try:
                    wavenumber_lengths.append(int(len(frame.spectrum.wavenumber)))
                except Exception:
                    pass
            if not np.isfinite(frame.temperature_C):
                temperature_missing_count += 1
            elif stage == "heating":
                heating_temps.append(float(frame.temperature_C))
            elif stage == "cooling":
                cooling_temps.append(float(frame.temperature_C))
            if not np.isfinite(frame.time_min):
                time_missing_count += 1
                if stage == "hold":
                    hold_time_missing_count += 1
            elif stage == "hold":
                hold_times.append(float(frame.time_min))
                if frame.time_estimated:
                    hold_time_estimated_count += 1
            if frame.time_estimated:
                time_estimated_count += 1
            if frame.spectrum is not None:
                raw = np.asarray(frame.spectrum.raw_absorbance if frame.spectrum.raw_absorbance.size else frame.spectrum.absorbance, dtype=float)
                if raw.size:
                    frame_rms_values.append(float(np.sqrt(np.nanmean(np.square(raw)))))
                    frame_peak_values.append(float(np.nanmax(np.abs(raw))))
            if frame.result is not None:
                frame_params = frame.result.parameters if hasattr(frame.result, "parameters") else {}
                if not isinstance(frame_params, dict):
                    frame_params = {}
                try:
                    if np.isfinite(frame.result.polymer_score):
                        frame_polymer_scores.append(float(frame.result.polymer_score))
                except Exception:
                    pass
                try:
                    assignment = float(frame_params.get("assignment_confidence", frame.result.polymer_score))
                    if np.isfinite(assignment):
                        frame_assignment_confidence.append(assignment)
                except Exception:
                    pass
                try:
                    assigned = 0
                    total = 0
                    for peak in getattr(frame.result, "peaks", []) or []:
                        if not isinstance(peak, dict):
                            continue
                        total += 1
                        assignment_name = str(peak.get("assignment", "") or "").strip().lower()
                        if assignment_name and assignment_name != "unknown":
                            assigned += 1
                    key_support = float(frame_params.get("key_band_support_score", (assigned / total) if total else np.nan))
                    if np.isfinite(key_support):
                        frame_key_band_support.append(key_support)
                except Exception:
                    pass
        params: Dict[str, Any] = {
            "n_frames": len(self.frames),
            "n_bands_tracked": len(self.band_names),
            "stage_counts": stage_counts,
            "stage_sequence": stage_sequence,
            "sequence_order_source": (
                max(set(order_sources), key=order_sources.count) if order_sources else "index"
            ),
            "wavenumber_lengths": wavenumber_lengths,
            "temperature_missing_count": temperature_missing_count,
            "time_missing_count": time_missing_count,
            "time_estimated_count": time_estimated_count,
            "hold_time_missing_count": hold_time_missing_count,
            "hold_time_estimated_count": hold_time_estimated_count,
            "heating_monotonic": bool(np.all(np.diff(heating_temps) >= 0)) if len(heating_temps) >= 2 else True,
            "cooling_monotonic": bool(np.all(np.diff(cooling_temps) <= 0)) if len(cooling_temps) >= 2 else True,
            "hold_monotonic": bool(np.all(np.diff(hold_times) >= 0)) if len(hold_times) >= 2 else True,
        }
        low_confidence_frames = 0
        for frame in self.frames:
            result = frame.result
            if result is None:
                low_confidence_frames += 1
                continue
            result_params = result.parameters if hasattr(result, "parameters") else {}
            if not isinstance(result_params, dict):
                result_params = {}
            polymer_score = float(getattr(result, "polymer_score", np.nan))
            assignment = float(result_params.get("assignment_confidence", polymer_score))
            total = 0
            assigned = 0
            for peak in getattr(result, "peaks", []) or []:
                if not isinstance(peak, dict):
                    continue
                total += 1
                assignment_name = str(peak.get("assignment", "") or "").strip().lower()
                if assignment_name and assignment_name != "unknown":
                    assigned += 1
            key_support = float(result_params.get("key_band_support_score", (assigned / total) if total else np.nan))
            if (
                (np.isfinite(polymer_score) and polymer_score < 0.65)
                or (np.isfinite(assignment) and assignment < 0.60)
                or (np.isfinite(key_support) and key_support < 0.60)
            ):
                low_confidence_frames += 1
        if self.frames:
            params["low_confidence_frame_count"] = int(low_confidence_frames)
            params["low_confidence_frame_ratio"] = float(low_confidence_frames / max(len(self.frames), 1))
        if frame_polymer_scores:
            params["frame_polymer_score_mean"] = float(np.nanmean(frame_polymer_scores))
        if frame_assignment_confidence:
            params["frame_assignment_confidence_mean"] = float(np.nanmean(frame_assignment_confidence))
        if frame_key_band_support:
            params["frame_key_band_support_mean"] = float(np.nanmean(frame_key_band_support))
        if temps:
            params["T_range_C"] = f"{min(temps):.0f}-{max(temps):.0f}"
            params["temperature_min_C"] = float(min(temps))
            params["temperature_max_C"] = float(max(temps))
        if self.transitions:
            params["n_transitions"] = len(self.transitions)
            params["transition_temperatures_C"] = ";".join(
                f"{t.get('T_C', np.nan):.0f}" for t in self.transitions)
            params["transition_count"] = len(self.transitions)
        if self.sync_corr.size:
            params["max_sync_autocorr"] = float(np.nanmax(np.diag(self.sync_corr)))
            params["sync_shape"] = tuple(self.sync_corr.shape)
        if self.async_corr.size:
            params["async_shape"] = tuple(self.async_corr.shape)
        if self.dynamic_matrix.size:
            params["dynamic_shape"] = tuple(self.dynamic_matrix.shape)
            params["dynamic_rms"] = float(
                np.sqrt(np.nanmean(np.square(self.dynamic_matrix)))
            )
            params["nan_fraction"] = float(np.isnan(self.dynamic_matrix).sum() / self.dynamic_matrix.size)
        if self.absorbance_matrix.size:
            params["matrix_shape"] = tuple(self.absorbance_matrix.shape)
            params["matrix_nan_fraction"] = float(np.isnan(self.absorbance_matrix).sum() / self.absorbance_matrix.size)
            params["wavenumber_grid_consistent"] = bool(
                all(
                    frame.spectrum is not None
                    and frame.spectrum.wavenumber is not None
                    and len(frame.spectrum.wavenumber) == len(self.wavenumber)
                    and np.allclose(np.asarray(frame.spectrum.wavenumber, dtype=float), np.asarray(self.wavenumber, dtype=float), rtol=0, atol=1e-6)
                    for frame in self.frames
                )
            )
            params["frame_intensity_scale_spread"] = float(
                (max(frame_peak_values) - min(frame_peak_values)) / max(max(abs(v) for v in frame_peak_values), 1e-9)
            ) if len(frame_peak_values) >= 2 else np.nan
        params["sync_cross_peak_count"] = len(self.sync_cross_peaks)
        params["async_cross_peak_count"] = len(self.async_cross_peaks)
        if self.cross_peak_assignment_summary:
            params.update(self.cross_peak_assignment_summary)
        if self.band_index_transition_summary:
            params.update(self.band_index_transition_summary)
        params["neg_fraction"] = self.neg_fraction
        params["dynamic_signal_rms"] = params.get("dynamic_rms", np.nan)
        if self.sync_corr.size:
            params["max_sync_abs"] = float(np.nanmax(np.abs(self.sync_corr)))
        if self.async_corr.size:
            params["max_async_abs"] = float(np.nanmax(np.abs(self.async_corr)))
        if self.async_cross_peaks:
            top = self.async_cross_peaks[0]
            params["top_async_cross_peak_cm1"] = (
                f"{top.get('wavenumber_1_cm1', np.nan):.0f}/"
                f"{top.get('wavenumber_2_cm1', np.nan):.0f}"
            )
        if self.sync_cross_peaks:
            top = self.sync_cross_peaks[0]
            params["top_sync_cross_peak_cm1"] = (
                f"{top.get('wavenumber_1_cm1', np.nan):.0f}/"
                f"{top.get('wavenumber_2_cm1', np.nan):.0f}"
            )
        for key, values in self.band_indices_vs_frame.items():
            arr = np.asarray(values, dtype=float)
            if np.any(np.isfinite(arr)):
                params[f"{key}_initial"] = float(arr[np.where(np.isfinite(arr))[0][0]])
                params[f"{key}_final"] = float(arr[np.where(np.isfinite(arr))[0][-1]])
        return params


def detect_temperature_2d(filepath: str) -> Optional[str]:
    if not os.path.isdir(filepath):
        return None
    try:
        names = [fn for fn in os.listdir(filepath)
                 if os.path.splitext(fn)[1].lower() in {'.csv', '.txt', '.dat', '.spa', '.dpt', '.asc'}]
    except Exception:
        return None
    if len(names) < 3:
        return None
    hits = 0
    for name in names:
        lower = name.lower()
        if re.search(r'-(sw|jw)-\d+', lower) or re.search(r'\d+\s*[-_ ]*for\s*\d+\s*min', lower):
            hits += 1
        elif re.search(r'(?:^|[-_ ])t?\d{2,3}(?:\.\d+)?(?:c|degc)?(?:$|[-_ ])', lower):
            hits += 1
    return "ir.temperature_2d" if hits >= 3 else None


def parse_temperature_condition(spectrum: IRSpectrum, fallback_order: int = 0) -> IRTempFrame:
    filename = str(spectrum.metadata.get('filename') or spectrum.label)
    stem = os.path.splitext(os.path.basename(filename))[0]
    lower = stem.lower()

    stage = "sequence"
    sequence_order_source = "index"
    group = 3.0
    temp = np.nan
    time_min = np.nan
    within = float(fallback_order)

    m = re.search(r'(?P<T>\d+(?:\.\d+)?)\s*[-_ ]*for\s*(?P<t>\d+(?:\.\d+)?)\s*min', lower)
    if m:
        stage = "hold"
        group = 1.0
        temp = float(m.group("T"))
        time_min = float(m.group("t"))
        within = time_min
        sequence_order_source = "filename_time"
    else:
        m = re.search(r'-(?P<stage>sw|jw)-(?P<T>\d+(?:\.\d+)?)', lower)
        if m:
            code = m.group("stage")
            temp = float(m.group("T"))
            if code == "sw":
                stage = "heating"
                group = 0.0
                within = temp
            else:
                stage = "cooling"
                group = 2.0
                within = -temp
            sequence_order_source = "filename_stage"
        else:
            nums = re.findall(r'\d+(?:\.\d+)?', stem)
            if nums:
                temp = float(nums[-1])
                within = temp
                sequence_order_source = "filename_numeric"

    return IRTempFrame(
        label=spectrum.label or stem,
        stage=stage,
        sequence_order_source=sequence_order_source,
        temperature_C=temp,
        time_min=time_min,
        order=group * 10000.0 + within,
        spectrum=spectrum,
    )


def _load_sequence_axis_metadata(config: IRConfig) -> dict[str, dict[str, Any]]:
    path = str(getattr(config, "sequence_axis_metadata_path", "") or "").strip()
    if not path or not os.path.isfile(path):
        return {}
    try:
        import csv

        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            mapping: dict[str, dict[str, Any]] = {}
            for row in reader:
                if not isinstance(row, dict):
                    continue
                key = str(row.get("label") or row.get("filename") or row.get("stem") or "").strip()
                if not key:
                    continue
                item: dict[str, Any] = {}
                stage = str(row.get("stage") or "").strip().lower()
                if stage:
                    item["stage"] = stage
                try:
                    if str(row.get("temperature_C", "")).strip():
                        item["temperature_C"] = float(row["temperature_C"])
                except Exception:
                    pass
                try:
                    if str(row.get("time_min", "")).strip():
                        item["time_min"] = float(row["time_min"])
                except Exception:
                    pass
                try:
                    if str(row.get("order", "")).strip():
                        item["order"] = float(row["order"])
                except Exception:
                    pass
                if item:
                    mapping[key] = item
            return mapping
    except Exception:
        return {}


def _apply_sequence_axis_metadata(
    frames: List[IRTempFrame],
    metadata: dict[str, dict[str, Any]],
) -> None:
    if not frames or not metadata:
        return
    for index, frame in enumerate(frames):
        filename = str(getattr(frame.spectrum, "metadata", {}).get("filename") or frame.label or "").strip()
        stem = os.path.splitext(os.path.basename(filename))[0] if filename else str(frame.label or "").strip()
        override = metadata.get(str(frame.label or "").strip()) or metadata.get(stem) or metadata.get(filename)
        if not isinstance(override, dict):
            continue
        stage = str(override.get("stage") or "").strip().lower()
        if stage:
            frame.stage = stage
        if "temperature_C" in override:
            try:
                frame.temperature_C = float(override["temperature_C"])
            except Exception:
                pass
        if "time_min" in override:
            try:
                frame.time_min = float(override["time_min"])
                frame.time_estimated = False
            except Exception:
                pass
        if "order" in override:
            try:
                frame.order = float(override["order"])
            except Exception:
                pass
        else:
            frame.order = float(index)
        frame.sequence_order_source = "metadata_csv"


def analyze_temperature_2d_series(
    spectra: List[IRSpectrum],
    config: IRConfig,
    label: str = "IR temperature series",
) -> IRTemp2DResult:
    frames = [parse_temperature_condition(s, i) for i, s in enumerate(spectra)]
    sequence_axis_mode = str(getattr(config, "sequence_axis_mode", "auto") or "auto").strip().lower()
    metadata = _load_sequence_axis_metadata(config)
    if metadata and sequence_axis_mode in {"auto", "metadata"}:
        _apply_sequence_axis_metadata(frames, metadata)
    frames.sort(key=lambda f: (f.order, f.label))

    result = IRTemp2DResult(label=label, frames=frames)
    if not frames:
        return result

    base_wn = np.asarray(frames[0].spectrum.wavenumber, dtype=float)
    matrix_rows: List[np.ndarray] = []

    for frame in frames:
        spec = frame.spectrum
        analysis = analyze_spectrum(
            spec, config, label=frame.label,
            polymer_name=config.polymer_name or "PA6",
        )
        frame.result = analysis

        # Use raw absorbance (pre-baseline, pre-normalisation) with
        # a light mute-zone baseline for the 2D-COS matrix.
        # This preserves temperature-induced spectral changes that
        # rubberband + minmax normalisation would otherwise erase.
        raw_y = spec.raw_absorbance if spec.raw_absorbance.size else spec.absorbance
        if raw_y.size:
            corrected_y, _bg = baseline_mute_zone(spec.wavenumber, raw_y)
        else:
            corrected_y = raw_y
        matrix_rows.append(_interp_to_grid(spec.wavenumber, corrected_y, base_wn))

    result.wavenumber = base_wn
    result.absorbance_matrix = np.vstack(matrix_rows) if matrix_rows else np.empty((0, 0))

    bands = PA6_TRACKED_BANDS
    result.band_names = list(bands.keys())
    result.band_positions = list(bands.values())
    for band_name, band_pos in bands.items():
        values = []
        for frame in frames:
            spec = frame.spectrum
            values.append(measure_band_height(spec.wavenumber, spec.absorbance, band_pos, tolerance=10.0))
        result.band_intensity_vs_frame[band_name] = values

    all_index_keys = sorted({k for frame in frames if frame.result for k in frame.result.band_indices})
    for key in all_index_keys:
        result.band_indices_vs_frame[key] = [
            frame.result.band_indices.get(key, np.nan) if frame.result else np.nan
            for frame in frames
        ]

    result.dynamic_matrix, result.sync_corr, result.async_corr, result.neg_fraction = compute_2d_correlation(
        result.absorbance_matrix)
    exclusion_cm1 = float(getattr(config, "cross_peak_exclusion_cm1", 35.0) or 35.0)
    result.sync_cross_peaks = _find_2d_cross_peaks(
        result.wavenumber,
        result.sync_corr,
        mode="sync",
        exclusion_cm1=exclusion_cm1,
    )
    result.async_cross_peaks = _find_2d_cross_peaks(
        result.wavenumber,
        result.async_corr,
        mode="async",
        exclusion_cm1=exclusion_cm1,
    )
    _annotate_cross_peaks(result, config)
    result.transitions = _detect_ir_band_transitions(result)
    return result


def compute_2d_correlation(absorbance_matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Compute Noda synchronous/asynchronous 2D correlation spectra.

    Rows are ordered perturbation states (temperature/time sequence), columns
    are wavenumbers.  The dynamic spectrum is mean-centered before correlation.

    Returns (dynamic, sync, async, neg_fraction).
    neg_fraction is the fraction of absorbance matrix elements <= 0
    (indicator of potential baseline over-subtraction / signal clipping).
    """
    M = np.asarray(absorbance_matrix, dtype=float)
    if M.ndim != 2 or min(M.shape) == 0:
        empty = np.empty((0, 0))
        return empty, empty, empty, 0.0
    if M.shape[0] < 3:
        dynamic = M - np.nanmean(M, axis=0, keepdims=True)
        return dynamic, np.empty((0, 0)), np.empty((0, 0)), 0.0

    # Detect baseline over-subtraction: fraction of raw absorbance values <= 0
    neg_fraction = float(np.nansum(M <= 0) / M.size) if M.size else 0.0

    col_mean = np.nanmean(M, axis=0, keepdims=True)
    dynamic = M - col_mean
    dynamic = np.nan_to_num(dynamic, nan=0.0, posinf=0.0, neginf=0.0)
    denom = max(M.shape[0] - 1, 1)

    sync = (dynamic.T @ dynamic) / denom
    noda = _noda_matrix(M.shape[0])
    async_corr = (dynamic.T @ noda @ dynamic) / denom
    return dynamic, sync, async_corr, neg_fraction


def _noda_matrix(n: int) -> np.ndarray:
    idx = np.arange(n, dtype=float)
    diff = idx[None, :] - idx[:, None]
    mat = np.zeros((n, n), dtype=float)
    mask = diff != 0
    mat[mask] = 1.0 / (np.pi * diff[mask])
    return mat


def _find_2d_cross_peaks(
    wavenumber: np.ndarray,
    corr: np.ndarray,
    mode: str,
    max_peaks: int = 12,
    exclusion_cm1: float = 35.0,
) -> List[Dict[str, Any]]:
    wn = np.asarray(wavenumber, dtype=float)
    C = np.asarray(corr, dtype=float)
    if C.ndim != 2 or C.shape[0] != len(wn) or C.shape[1] != len(wn) or C.size == 0:
        return []

    finite = np.isfinite(C)
    if not np.any(finite):
        return []
    work = np.where(finite, np.abs(C), -np.inf)
    diag_mask = np.abs(wn[:, None] - wn[None, :]) < exclusion_cm1
    work[diag_mask] = -np.inf
    upper = np.triu(np.ones_like(work, dtype=bool), k=1)
    work[~upper] = -np.inf

    flat = np.argsort(work.ravel())[::-1]
    peaks: List[Dict[str, Any]] = []
    used: List[Tuple[float, float]] = []
    for flat_idx in flat:
        score = work.ravel()[flat_idx]
        if not np.isfinite(score):
            break
        i, j = np.unravel_index(flat_idx, C.shape)
        w1 = float(wn[i])
        w2 = float(wn[j])
        if any(
            abs(w1 - u1) < exclusion_cm1 and abs(w2 - u2) < exclusion_cm1
            for u1, u2 in used
        ):
            continue
        peaks.append({
            "mode": mode,
            "wavenumber_1_cm1": w1,
            "wavenumber_2_cm1": w2,
            "correlation": float(C[i, j]),
            "abs_correlation": float(score),
        })
        used.append((w1, w2))
        if len(peaks) >= max_peaks:
            break
    return peaks


def _reference_bands_for_polymer(config: IRConfig) -> list[dict[str, Any]]:
    polymer_key = normalize_ir_polymer_name(getattr(config, "polymer_name", ""))
    polymer_db = normalize_ir_polymer_database(getattr(config, "polymer_peaks_db", {}))
    entries = polymer_db.get(polymer_key, [])
    out: list[dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, (list, tuple)) or not item:
            continue
        try:
            wavenumber = float(item[0])
        except (TypeError, ValueError):
            continue
        out.append(
            {
                "wavenumber_cm1": wavenumber,
                "assignment": str(item[1] if len(item) > 1 else "" or "").strip(),
                "strength": str(item[2] if len(item) > 2 else "" or "").strip(),
                "crystalline": bool(item[3]) if len(item) > 3 else False,
            }
        )
    return out


def _nearest_reference_band(
    value_cm1: float,
    references: list[dict[str, Any]],
    tolerance_cm1: float,
) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_delta = float(tolerance_cm1)
    for ref in references:
        ref_wn = ref.get("wavenumber_cm1")
        try:
            delta = abs(float(value_cm1) - float(ref_wn))
        except (TypeError, ValueError):
            continue
        if delta <= best_delta:
            best_delta = delta
            best = {
                "ref_wavenumber_cm1": float(ref_wn),
                "assignment": str(ref.get("assignment", "") or "").strip(),
                "strength": str(ref.get("strength", "") or "").strip(),
                "crystalline": bool(ref.get("crystalline", False)),
                "delta_cm1": float(delta),
            }
    return best


def _reference_pair_key(ref1: dict[str, Any] | None, ref2: dict[str, Any] | None) -> tuple[float, float] | None:
    if not ref1 or not ref2:
        return None
    wn1 = ref1.get("ref_wavenumber_cm1")
    wn2 = ref2.get("ref_wavenumber_cm1")
    try:
        pair = sorted((float(wn1), float(wn2)))
    except (TypeError, ValueError):
        return None
    return (pair[0], pair[1])


def _cross_peak_pair_matches(
    peak_a: tuple[float, float],
    peak_b: tuple[float, float],
    tolerance_cm1: float,
) -> bool:
    a1, a2 = sorted((float(peak_a[0]), float(peak_a[1])))
    b1, b2 = sorted((float(peak_b[0]), float(peak_b[1])))
    return abs(a1 - b1) <= tolerance_cm1 and abs(a2 - b2) <= tolerance_cm1


def _annotate_cross_peaks(result: IRTemp2DResult, config: IRConfig) -> None:
    references = _reference_bands_for_polymer(config)
    tolerance_cm1 = float(getattr(config, "assignment_tolerance_cm1", 18.0) or 18.0)
    exclusion_cm1 = float(getattr(config, "cross_peak_exclusion_cm1", 35.0) or 35.0)
    sync_reference_pairs: set[tuple[float, float]] = set()
    sync_peak_pairs: list[tuple[float, float]] = []

    for peak in result.sync_cross_peaks:
        w1 = float(peak.get("wavenumber_1_cm1", np.nan))
        w2 = float(peak.get("wavenumber_2_cm1", np.nan))
        diag_distance = abs(w1 - w2)
        ref1 = _nearest_reference_band(w1, references, tolerance_cm1)
        ref2 = _nearest_reference_band(w2, references, tolerance_cm1)
        peak["diagonal_distance_cm1"] = float(diag_distance)
        peak["near_reference_band_1"] = ref1
        peak["near_reference_band_2"] = ref2
        peak["assigned"] = bool(ref1 and ref2)
        peak["assignment_pair"] = (
            f"{ref1.get('assignment', '')}/{ref2.get('assignment', '')}"
            if ref1 and ref2
            else ""
        )
        peak["cross_peak_near_diagonal"] = bool(diag_distance < exclusion_cm1 + 10.0)
        sync_peak_pairs.append((w1, w2))
        pair_key = _reference_pair_key(ref1, ref2)
        if pair_key is not None:
            sync_reference_pairs.add(pair_key)

    async_with_sync_support = 0
    assigned_sync = sum(1 for peak in result.sync_cross_peaks if peak.get("assigned"))
    assigned_async = 0
    for peak in result.async_cross_peaks:
        w1 = float(peak.get("wavenumber_1_cm1", np.nan))
        w2 = float(peak.get("wavenumber_2_cm1", np.nan))
        diag_distance = abs(w1 - w2)
        ref1 = _nearest_reference_band(w1, references, tolerance_cm1)
        ref2 = _nearest_reference_band(w2, references, tolerance_cm1)
        ref_pair_key = _reference_pair_key(ref1, ref2)
        has_sync_support = bool(ref_pair_key is not None and ref_pair_key in sync_reference_pairs)
        if not has_sync_support:
            has_sync_support = any(
                _cross_peak_pair_matches((w1, w2), sync_pair, tolerance_cm1)
                for sync_pair in sync_peak_pairs
            )
        peak["diagonal_distance_cm1"] = float(diag_distance)
        peak["near_reference_band_1"] = ref1
        peak["near_reference_band_2"] = ref2
        peak["assigned"] = bool(ref1 and ref2)
        peak["assignment_pair"] = (
            f"{ref1.get('assignment', '')}/{ref2.get('assignment', '')}"
            if ref1 and ref2
            else ""
        )
        peak["sync_support"] = has_sync_support
        peak["cross_peak_near_diagonal"] = bool(diag_distance < exclusion_cm1 + 10.0)
        if peak["assigned"]:
            assigned_async += 1
        if has_sync_support:
            async_with_sync_support += 1

    total_cross_peak_count = len(result.sync_cross_peaks) + len(result.async_cross_peaks)
    assigned_cross_peak_count = assigned_sync + assigned_async
    unassigned_cross_peak_count = max(total_cross_peak_count - assigned_cross_peak_count, 0)
    top_sync = result.sync_cross_peaks[0] if result.sync_cross_peaks else {}
    top_async = result.async_cross_peaks[0] if result.async_cross_peaks else {}
    result.cross_peak_assignment_summary = {
        "cross_peak_count": total_cross_peak_count,
        "assigned_cross_peak_count": assigned_cross_peak_count,
        "unassigned_cross_peak_count": unassigned_cross_peak_count,
        "sync_assigned_cross_peak_count": assigned_sync,
        "async_assigned_cross_peak_count": assigned_async,
        "async_with_sync_support_count": async_with_sync_support,
        "top_sync_diagonal_distance_cm1": float(top_sync.get("diagonal_distance_cm1", np.nan)) if top_sync else np.nan,
        "top_async_diagonal_distance_cm1": float(top_async.get("diagonal_distance_cm1", np.nan)) if top_async else np.nan,
        "top_sync_assigned": bool(top_sync.get("assigned")) if top_sync else False,
        "top_async_assigned": bool(top_async.get("assigned")) if top_async else False,
        "top_async_has_sync_support": bool(top_async.get("sync_support")) if top_async else False,
        "noda_rule_interpretation_ready": bool(
            result.async_cross_peaks
            and result.sync_cross_peaks
            and assigned_async > 0
            and async_with_sync_support > 0
        ),
    }


def _interp_to_grid(x: np.ndarray, y: np.ndarray, grid: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    grid = np.asarray(grid, dtype=float)
    if len(x) == len(grid) and np.allclose(x, grid, rtol=0, atol=1e-6):
        return np.asarray(y, dtype=float)
    order = np.argsort(x)
    return np.interp(grid, x[order], y[order])


def _band_index_transition_candidates(result: IRTemp2DResult) -> List[Dict[str, Any]]:
    temps = np.asarray(result.temperatures, dtype=float)
    if not np.any(np.isfinite(temps)):
        return []

    candidates: List[Dict[str, Any]] = []
    for key, values in result.band_indices_vs_frame.items():
        y = np.asarray(values, dtype=float)
        valid = np.isfinite(y) & np.isfinite(temps)
        if np.sum(valid) < 5:
            continue
        x = np.arange(len(y), dtype=float)
        y_fill = y.copy()
        y_fill[~np.isfinite(y_fill)] = np.interp(x[~np.isfinite(y_fill)], x[valid], y[valid])
        dy = np.diff(y_fill)
        finite_dy = dy[np.isfinite(dy)]
        if finite_dy.size < 2:
            continue
        noise = float(np.nanstd(finite_dy))
        if noise <= 1e-9:
            continue
        peak_frame = int(np.nanargmax(np.abs(dy)))
        jump_abs = float(abs(dy[peak_frame]))
        jump_ratio = float(jump_abs / max(noise, 1e-9))
        if jump_ratio < 2.0:
            continue
        support_slice = slice(max(0, peak_frame - 1), min(len(y_fill), peak_frame + 3))
        local_span = float(np.nanmax(y_fill[support_slice]) - np.nanmin(y_fill[support_slice]))
        candidates.append(
            {
                "index": key,
                "frame": peak_frame,
                "T_C": float(temps[min(peak_frame, len(temps) - 1)]) if np.isfinite(temps[min(peak_frame, len(temps) - 1)]) else np.nan,
                "slope": float(dy[peak_frame]),
                "jump_abs": jump_abs,
                "jump_ratio": jump_ratio,
                "noise": noise,
                "local_span": local_span,
            }
        )
    return candidates


def _detect_ir_band_transitions(result: IRTemp2DResult) -> List[Dict[str, Any]]:
    candidates = _band_index_transition_candidates(result)
    tracked_keys = sorted(result.band_indices_vs_frame.keys())
    summary: Dict[str, Any] = {
        "band_index_series_count": len(tracked_keys),
        "band_index_transition_candidate_count": len(candidates),
        "band_tracking_missing_key_band": len(tracked_keys) < 3,
    }
    if not candidates:
        result.band_index_transition_summary = summary
        return []

    frame_votes: Dict[int, int] = {}
    for candidate in candidates:
        frame = int(candidate.get("frame", 0))
        frame_votes[frame] = frame_votes.get(frame, 0) + 1
    consensus_frame = max(frame_votes.items(), key=lambda item: (item[1], -abs(item[0])))[0]
    support = [candidate for candidate in candidates if abs(int(candidate.get("frame", 0)) - consensus_frame) <= 1]
    if not support:
        support = [max(candidates, key=lambda item: (float(item.get("jump_ratio", 0.0)), float(item.get("jump_abs", 0.0))))]
        consensus_frame = int(support[0].get("frame", 0))

    support_band_indices = [str(candidate.get("index", "") or "").strip() for candidate in support if str(candidate.get("index", "") or "").strip()]
    support_frames = [int(candidate.get("frame", 0)) for candidate in support]
    support_ratios = [float(candidate.get("jump_ratio", 0.0)) for candidate in support]
    support_jumps = [float(candidate.get("jump_abs", 0.0)) for candidate in support]
    support_spans = [float(candidate.get("local_span", 0.0)) for candidate in support]
    support_count = len(support_band_indices)
    frame_spread = float(max(support_frames) - min(support_frames)) if support_frames else np.nan
    support_ratio = float(support_count / max(len(tracked_keys), 1))
    max_jump = float(max(support_jumps)) if support_jumps else np.nan
    median_jump = float(np.median(support_jumps)) if support_jumps else np.nan
    max_jump_ratio = float(max(support_ratios)) if support_ratios else np.nan
    consensus_temp = float(result.temperatures[min(consensus_frame, len(result.temperatures) - 1)]) if result.temperatures and np.isfinite(result.temperatures[min(consensus_frame, len(result.temperatures) - 1)]) else np.nan
    reproducible = bool(support_count >= 2 and frame_spread <= 1.0 and support_ratio >= 0.5)
    single_frame_only = bool(support_count < 2 or frame_spread > 1.0)
    denominator_unstable = bool(max_jump_ratio > 4.5 and support_count < len(tracked_keys))
    band_tracking_score = float(
        max(
            0.0,
            min(
                1.0,
                0.32
                + 0.18 * min(len(tracked_keys) / 3.0, 1.0)
                + 0.20 * support_ratio
                + (0.14 if reproducible else 0.0)
                + (0.10 if not single_frame_only else 0.0)
                + (0.08 if not denominator_unstable else 0.0),
            ),
        )
    )

    anchor = max(support, key=lambda item: (float(item.get("jump_ratio", 0.0)), float(item.get("jump_abs", 0.0))))
    transition = {
        "type": "band_index_change",
        "index": str(anchor.get("index", "") or ""),
        "frame": int(consensus_frame),
        "T_C": consensus_temp,
        "slope": float(anchor.get("slope", np.nan)),
        "support_band_indices": support_band_indices,
        "support_band_count": support_count,
        "band_index_series_count": len(tracked_keys),
        "support_ratio": support_ratio,
        "frame_spread": frame_spread,
        "max_jump_cm1": max_jump,
        "median_jump_cm1": median_jump,
        "max_jump_ratio": max_jump_ratio,
        "temperature_trend_reproducible": reproducible,
        "single_frame_only": single_frame_only,
        "band_index_denominator_unstable": denominator_unstable,
        "band_tracking_score": band_tracking_score,
    }
    summary.update(
        {
            "band_index_transition_consensus_frame": int(consensus_frame),
            "band_index_transition_support_band_count": support_count,
            "band_index_transition_support_ratio": support_ratio,
            "band_index_transition_frame_spread": frame_spread,
            "band_index_transition_single_frame_only": single_frame_only,
            "band_index_transition_reproducible": reproducible,
            "band_index_transition_denominator_unstable": denominator_unstable,
            "band_index_transition_max_jump_cm1": max_jump,
            "band_index_transition_median_jump_cm1": median_jump,
            "band_index_transition_max_jump_ratio": max_jump_ratio,
            "band_index_transition_support_keys": support_band_indices,
            "band_index_transition_support_spans": support_spans,
            "band_tracking_score": band_tracking_score,
        }
    )
    result.band_index_transition_summary = summary
    return [transition]


def _temp_dirs(output_dir: str) -> Tuple[str, str]:
    fig_dir = os.path.join(output_dir, 'figures')
    data_dir = os.path.join(output_dir, 'data')
    os.makedirs(fig_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    return fig_dir, data_dir


def _save_figure(fig, output_dir: str, name: str, config: Optional[IRConfig] = None) -> str:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig_dir, _ = _temp_dirs(output_dir)
    fmt = getattr(config, 'fig_format', 'svg') if config else 'svg'
    dpi = getattr(config, 'fig_dpi', 300) if config else 300
    path = os.path.join(fig_dir, f'{name}.{fmt}')
    savefig_with_edits(fig, path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


def generate_temperature_2d_figures(
    result: IRTemp2DResult,
    output_dir: str,
    config: Optional[IRConfig] = None,
) -> Dict[str, str]:
    figures: Dict[str, str] = {}
    p = fig_ir_temperature_heatmap(result, output_dir, config)
    if p:
        figures["temperature_heatmap"] = p
    p = fig_ir_temperature_waterfall(result, output_dir, config)
    if p:
        figures["temperature_waterfall"] = p
    p = fig_ir_temperature_band_indices(result, output_dir, config)
    if p:
        figures["temperature_band_indices"] = p
    p = fig_ir_temperature_band_tracking(result, output_dir, config)
    if p:
        figures["temperature_band_tracking"] = p
    p = fig_ir_temperature_2dcos_sync(result, output_dir, config)
    if p:
        figures["temperature_2dcos_sync"] = p
    p = fig_ir_temperature_2dcos_async(result, output_dir, config)
    if p:
        figures["temperature_2dcos_async"] = p
    export_temperature_2d_csv(result, output_dir)
    return figures


def fig_ir_temperature_heatmap(result: IRTemp2DResult, output_dir: str,
                               config: Optional[IRConfig] = None) -> str:
    if result.absorbance_matrix.size == 0:
        return ""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    M = np.asarray(result.absorbance_matrix, dtype=float)
    wn = np.asarray(result.wavenumber, dtype=float)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    im = ax.imshow(
        M,
        aspect='auto',
        cmap='viridis',
        origin='lower',
        extent=[float(wn[0]), float(wn[-1]), 0, max(len(result.frames) - 1, 1)],
    )
    ax.invert_xaxis()
    ax.set_xlabel('Wavenumber (cm^-1)')
    ax.set_ylabel('Frame')
    pass
    tick_idx = _selected_frame_ticks(result.frames)
    ax.set_yticks(tick_idx)
    ax.set_yticklabels([_frame_tick_label(result.frames[i]) for i in tick_idx], fontsize=7)
    fig.colorbar(im, ax=ax, label='Absorbance (a.u.)')
    ax.tick_params(direction='in', top=True, right=True)
    return _save_figure(fig, output_dir, 'Fig-IRT1_2D_heatmap', config)


def fig_ir_temperature_waterfall(result: IRTemp2DResult, output_dir: str,
                                 config: Optional[IRConfig] = None) -> str:
    if result.absorbance_matrix.size == 0:
        return ""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.0, 5.2))
    temps = np.asarray(result.temperatures, dtype=float)
    finite_t = temps[np.isfinite(temps)]
    norm = plt.Normalize(np.nanmin(finite_t), np.nanmax(finite_t)) if finite_t.size else None
    cmap = plt.cm.plasma
    offset = 0.0
    for i, frame in enumerate(result.frames):
        y = result.absorbance_matrix[i].copy()
        y = y - np.nanmin(y)
        ymax = np.nanmax(y)
        if ymax > 0:
            y = y / ymax
        color = cmap(norm(frame.temperature_C)) if norm and np.isfinite(frame.temperature_C) else '#2166AC'
        ax.plot(result.wavenumber, y + offset, color=color, linewidth=0.8)
        if i in _selected_frame_ticks(result.frames, max_ticks=10):
            ax.text(float(result.wavenumber[-1]), offset + 0.1, _frame_tick_label(frame),
                    fontsize=6, va='bottom', ha='left')
        offset += 0.55
    ax.invert_xaxis()
    ax.set_xlabel('Wavenumber (cm^-1)')
    ax.set_ylabel('Normalized absorbance + offset')
    pass
    ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
    ax.tick_params(direction='in', top=True, right=True)
    return _save_figure(fig, output_dir, 'Fig-IRT2_waterfall', config)


def fig_ir_temperature_band_indices(result: IRTemp2DResult, output_dir: str,
                                    config: Optional[IRConfig] = None) -> str:
    if not result.band_indices_vs_frame:
        return ""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    x = np.arange(len(result.frames), dtype=float)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for key, values in result.band_indices_vs_frame.items():
        ax.plot(x, values, marker='o', markersize=3, linewidth=1.0, label=key)
    _apply_stage_spans(ax, result.frames)
    ax.set_xlabel('Sequence frame')
    ax.set_ylabel('IR band index')
    pass
    ax.set_xticks(_selected_frame_ticks(result.frames))
    ax.set_xticklabels([_frame_tick_label(result.frames[i]) for i in _selected_frame_ticks(result.frames)],
                       rotation=45, ha='right', fontsize=7)
    ax.legend(fontsize=7, framealpha=0.85)
    ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
    ax.tick_params(direction='in', top=True, right=True)
    return _save_figure(fig, output_dir, 'Fig-IRT3_band_indices', config)


def fig_ir_temperature_band_tracking(result: IRTemp2DResult, output_dir: str,
                                     config: Optional[IRConfig] = None) -> str:
    if not result.band_intensity_vs_frame:
        return ""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    x = np.arange(len(result.frames), dtype=float)
    key_order = ['amide_I', 'amide_II', 'cryst_1200', 'skeletal_1120', 'amide_V_929']
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for key in key_order:
        values = result.band_intensity_vs_frame.get(key)
        if values is not None:
            ax.plot(x, values, marker='o', markersize=3, linewidth=1.0, label=key)
    _apply_stage_spans(ax, result.frames)
    ax.set_xlabel('Sequence frame')
    ax.set_ylabel('Band height (a.u.)')
    pass
    ticks = _selected_frame_ticks(result.frames)
    ax.set_xticks(ticks)
    ax.set_xticklabels([_frame_tick_label(result.frames[i]) for i in ticks],
                       rotation=45, ha='right', fontsize=7)
    ax.legend(fontsize=7, framealpha=0.85)
    ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
    ax.tick_params(direction='in', top=True, right=True)
    return _save_figure(fig, output_dir, 'Fig-IRT4_band_tracking', config)


def fig_ir_temperature_2dcos_sync(result: IRTemp2DResult, output_dir: str,
                                  config: Optional[IRConfig] = None) -> str:
    return _fig_ir_temperature_2dcos(
        result,
        result.sync_corr,
        output_dir,
        name='Fig-IRT5_2DCOS_synchronous',
        title='Synchronous 2D correlation IR',
        cbar_label='Synchronous correlation',
        config=config,
    )


def fig_ir_temperature_2dcos_async(result: IRTemp2DResult, output_dir: str,
                                   config: Optional[IRConfig] = None) -> str:
    return _fig_ir_temperature_2dcos(
        result,
        result.async_corr,
        output_dir,
        name='Fig-IRT6_2DCOS_asynchronous',
        title='Asynchronous 2D correlation IR',
        cbar_label='Asynchronous correlation',
        config=config,
    )


def _fig_ir_temperature_2dcos(
    result: IRTemp2DResult,
    corr: np.ndarray,
    output_dir: str,
    name: str,
    title: str,
    cbar_label: str,
    config: Optional[IRConfig] = None,
) -> str:
    if corr.size == 0 or result.wavenumber.size == 0:
        return ""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    wn, C = _downsample_square(result.wavenumber, corr, max_points=420)
    if C.size == 0:
        return ""
    finite = C[np.isfinite(C)]
    if finite.size == 0:
        return ""
    vmax = float(np.nanpercentile(np.abs(finite), 99.0))
    if vmax <= 0:
        vmax = float(np.nanmax(np.abs(finite))) or 1.0

    fig, ax = plt.subplots(figsize=(5.8, 5.2))
    im = ax.imshow(
        C,
        aspect='equal',
        origin='lower',
        cmap='RdBu_r',
        vmin=-vmax,
        vmax=vmax,
        extent=[float(wn[0]), float(wn[-1]), float(wn[0]), float(wn[-1])],
    )
    ax.plot([float(wn[0]), float(wn[-1])], [float(wn[0]), float(wn[-1])],
            color='#222222', linewidth=0.6, alpha=0.45)
    ax.invert_xaxis()
    ax.invert_yaxis()
    ax.set_xlabel('Wavenumber 1 (cm^-1)')
    ax.set_ylabel('Wavenumber 2 (cm^-1)')
    pass  # dynamic title removed
    fig.colorbar(im, ax=ax, label=cbar_label, shrink=0.82)
    ax.tick_params(direction='in', top=True, right=True)
    return _save_figure(fig, output_dir, name, config)


def _downsample_square(
    wavenumber: np.ndarray,
    matrix: np.ndarray,
    max_points: int = 420,
) -> Tuple[np.ndarray, np.ndarray]:
    wn = np.asarray(wavenumber, dtype=float)
    M = np.asarray(matrix, dtype=float)
    if M.ndim != 2 or M.shape[0] != len(wn) or M.shape[1] != len(wn):
        return np.array([]), np.empty((0, 0))
    n = len(wn)
    if n <= max_points:
        return wn, M
    idx = np.linspace(0, n - 1, max_points, dtype=int)
    return wn[idx], M[np.ix_(idx, idx)]


def export_temperature_2d_csv(result: IRTemp2DResult, output_dir: str) -> Dict[str, str]:
    import pandas as pd

    _, data_dir = _temp_dirs(output_dir)
    rows = []

    # Detect missing cooling 250°C point
    missing_cooling_250 = _detect_missing_cooling_250(result.frames)

    # Estimate time_min from temperature differences where missing
    _estimate_missing_times(result.frames)

    for i, frame in enumerate(result.frames):
        row: Dict[str, Any] = {
            "frame": i,
            "label": frame.label,
            "stage": frame.stage,
            "temperature_C": frame.temperature_C,
            "time_min": frame.time_min,
            "n_peaks": frame.result.n_peaks if frame.result else np.nan,
            "polymer": frame.result.polymer_name if frame.result else "",
            "polymer_score": frame.result.polymer_score if frame.result else np.nan,
        }
        # Add note for missing cooling 250°C
        notes = []
        if missing_cooling_250 and frame.stage == "cooling" and abs(frame.temperature_C - 240) < 1:
            notes.append("cooling_250C_missing:降温段缺少250°C数据点")
        if np.isfinite(frame.time_min) and frame.time_estimated:
            notes.append("time_estimated_from_rate")
        row["note"] = "; ".join(notes) if notes else ""
        if frame.result:
            row.update(frame.result.band_indices)
        for key, values in result.band_intensity_vs_frame.items():
            row[f"band_height_{key}"] = values[i] if i < len(values) else np.nan
        rows.append(row)
    params_path = os.path.join(data_dir, 'ir_temperature_parameters.csv')
    pd.DataFrame(rows).to_csv(params_path, index=False)

    matrix = {"wavenumber_cm1": result.wavenumber}
    for i, frame in enumerate(result.frames):
        matrix[f"{i:03d}_{frame.label}"] = result.absorbance_matrix[i]
    matrix_path = os.path.join(data_dir, 'ir_temperature_matrix.csv')
    pd.DataFrame(matrix).to_csv(matrix_path, index=False)

    cross_peaks = result.sync_cross_peaks + result.async_cross_peaks
    cross_path = os.path.join(data_dir, 'ir_temperature_2dcos_cross_peaks.csv')
    pd.DataFrame(cross_peaks).to_csv(cross_path, index=False)

    return {"parameters": params_path, "matrix": matrix_path, "cross_peaks": cross_path}


def _selected_frame_ticks(frames: List[IRTempFrame], max_ticks: int = 12) -> List[int]:
    if not frames:
        return []
    if len(frames) <= max_ticks:
        return list(range(len(frames)))
    return sorted(set(np.linspace(0, len(frames) - 1, max_ticks, dtype=int).tolist()))


def _frame_tick_label(frame: IRTempFrame) -> str:
    if frame.stage == "hold" and np.isfinite(frame.time_min):
        return f"{frame.temperature_C:g}C/{frame.time_min:g}m"
    if np.isfinite(frame.temperature_C):
        prefix = {"heating": "H", "cooling": "C", "sequence": ""}.get(frame.stage, "")
        return f"{prefix}{frame.temperature_C:g}C"
    return frame.label


def _apply_stage_spans(ax, frames: List[IRTempFrame]) -> None:
    if not frames:
        return
    colors = {"heating": "#E69F00", "hold": "#56B4E9", "cooling": "#009E73", "sequence": "#999999"}
    start = 0
    current = frames[0].stage
    for i, frame in enumerate(frames[1:], start=1):
        if frame.stage != current:
            ax.axvspan(start - 0.5, i - 0.5, color=colors.get(current, "#999999"), alpha=0.08, linewidth=0)
            start = i
            current = frame.stage
    ax.axvspan(start - 0.5, len(frames) - 0.5, color=colors.get(current, "#999999"), alpha=0.08, linewidth=0)


def _detect_missing_cooling_250(frames: List[IRTempFrame]) -> bool:
    """Return True if cooling starts at 240°C (250°C data point missing)."""
    heating_250 = False
    cooling_start = None
    for f in frames:
        if f.stage == "heating" and abs(f.temperature_C - 250) < 1:
            heating_250 = True
        if f.stage == "cooling" and cooling_start is None:
            cooling_start = f.temperature_C
    if heating_250 and cooling_start is not None:
        return abs(cooling_start - 240) < 1
    return False


def _estimate_missing_times(frames: List[IRTempFrame]) -> None:
    """Fill missing time_min using a fixed 2 min/frame protocol step.

    This assumes a standard 10°C / 2 min heating/cooling ramp,
    which is the default protocol for this instrument setup.
    Sets frame.time_estimated = True on frames whose time was filled.
    """
    default_step = 2.0  # min per frame

    # Group by stage and fill missing times within each stage
    stage_start: Dict[str, int] = {}
    for i, f in enumerate(frames):
        if f.stage not in stage_start:
            stage_start[f.stage] = i

    for i, f in enumerate(frames):
        if f.stage == "hold":
            continue  # hold times already set by parse_temperature_condition
        if not np.isfinite(f.time_min):
            base_idx = stage_start.get(f.stage, 0)
            f.time_min = float(i - base_idx) * default_step
            f.time_estimated = True
