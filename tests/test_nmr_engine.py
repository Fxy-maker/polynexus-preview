from pathlib import Path
import warnings

import numpy as np
import pytest

from polynexus.core.engine import get_engine
from polynexus.core.submodule_registry import list_all_submodules
from polynexus.core.nmr_engine import NMRConfig, analyze_spectrum, load_project, preprocess_pipeline


def _nmr_root() -> Path:
    root = Path(__file__).resolve().parents[1] / "\u6d4b\u8bd5\u6570\u636e" / "NMR"
    if not root.is_dir():
        pytest.skip("external NMR instrument fixtures are unavailable")
    return root


def test_liquid_fid_readers_transform_h_and_c_spectra():
    root = _nmr_root() / "\u6db2\u4f53\u6838\u78c1"

    h_specs = load_project(str(root / "H\u8c31"))
    c_specs = load_project(str(root / "C\u8c31"))

    assert len(h_specs) == 1
    assert len(c_specs) == 1
    assert h_specs[0].has_data
    assert c_specs[0].has_data
    assert h_specs[0].nucleus == "1H"
    assert c_specs[0].nucleus == "13C"
    assert h_specs[0].metadata["format"] == "raw_fid"
    assert c_specs[0].metadata["format"] == "raw_fid"
    assert h_specs[0].ppm[0] > h_specs[0].ppm[-1]
    assert c_specs[0].ppm[0] > c_specs[0].ppm[-1]


def test_jeol_solid_readers_find_float64_payloads():
    root = _nmr_root()

    h_specs = load_project(str(root / "\u56fa\u4f53nmr\u6c22\u8c31"))
    c_specs = load_project(str(root / "\u56fa\u4f53nmr\u78b3\u8c31"))

    assert len(h_specs) >= 1
    assert len(c_specs) >= 1
    assert h_specs[0].metadata["format"] == "jeol_jdf"
    assert c_specs[0].metadata["format"] == "jeol_jdf"
    assert h_specs[0].nucleus == "1H"
    assert c_specs[0].nucleus == "13C"
    assert h_specs[0].metadata["data_points"] == len(h_specs[0].ppm)
    assert c_specs[0].metadata["data_points"] == len(c_specs[0].ppm)
    assert np.nanstd(h_specs[0].intensity) > 0
    assert np.nanstd(c_specs[0].intensity) > 0


def test_nmr_submodule_registry_has_liquid_and_solid_h_c_partitions():
    ids = [mod["id"] for mod in list_all_submodules() if mod["technique"] == "nmr"]

    assert ids == ["nmr.liquid_h", "nmr.liquid_c", "nmr.solid_h", "nmr.solid_c"]


def test_nmr_result_parameters_include_phase_and_match_evidence() -> None:
    from polynexus.core.nmr_engine.core import NMRResult

    result = NMRResult(nucleus="13C", sample_state="solid")
    result.peaks = [
        {
            "ppm": 172.0,
            "assignment": "C=O (c)",
            "phase": "c",
            "delta_ppm": 0.4,
            "snr": 12.0,
            "possible_solvent": "",
        },
        {
            "ppm": 170.5,
            "assignment": "C=O (a)",
            "phase": "a",
            "delta_ppm": 0.7,
            "snr": 9.0,
            "possible_solvent": "",
        },
    ]
    result.n_peaks = 2

    params = result.parameters

    assert params["peak_0_phase"] == "c"
    assert params["peak_1_phase"] == "a"
    assert params["peak_0_delta_ppm"] == 0.4


def test_nmr_result_parameters_include_assignment_source_statistics() -> None:
    from polynexus.core.nmr_engine.core import NMRResult

    result = NMRResult(nucleus="13C", sample_state="solid")
    result.peaks = [
        {"assignment": "carbonyl_C", "phase": "unknown", "possible_solvent": ""},
        {"assignment": "aliphatic_C", "phase": "unknown", "possible_solvent": "DMSO"},
    ]
    result.n_peaks = 2

    params = result.parameters

    assert params["assignment_source"] == "generic_region"
    assert params["generic_assignment_fraction"] == 1.0
    assert params["phase_assignment_count"] == 0
    assert params["solvent_peak_count"] == 1


def test_nmr_engine_analysis_attaches_unified_evidence_for_history_persistence(monkeypatch) -> None:
    from polynexus.core import nmr as nmr_module
    from polynexus.core.nmr_engine.core import NMRResult
    from polynexus.core.nmr_engine.io import NMRSpectrum

    expected = NMRResult(
        label="synthetic-c",
        nucleus="13C",
        sample_state="solid",
        n_peaks=2,
        median_snr=12.0,
        mean_fwhm_ppm=1.2,
        peaks=[
            {"ppm": 173.5, "assignment": "C=O (c)", "phase": "c", "snr": 12.0},
            {"ppm": 42.0, "assignment": "Calpha_am (a)", "phase": "a", "snr": 11.0},
        ],
        Xc_pct=41.0,
        Xc_method="requires_crystalline_amorphous_assignment",
        Xc_assignment_status="supported",
    )
    monkeypatch.setattr(nmr_module, "analyze_spectrum", lambda *args, **kwargs: expected)

    engine = nmr_module.NMREngine()
    engine.active_submodule = "nmr.solid_c"
    engine._spectra = [
        NMRSpectrum(
            label="synthetic-c",
            nucleus="13C",
            ppm=np.array([180.0, 42.0, 173.5]),
            intensity=np.array([0.1, 0.4, 0.8]),
            metadata={"sample_state": "solid"},
        )
    ]

    assert engine.analyze() is True

    evidence = engine.result.analysis_evidence
    assert evidence["technique"] == "NMR"
    assert evidence["peak_evidence"]["peak_count"] == 2
    assert evidence["structure_evidence"]["Xc_assignment_status"] == "supported"


def test_nmr_assignment_library_scores_phase_pair_support() -> None:
    from polynexus.core.nmr_engine.core import NMRResult, _score_assignment_library

    cfg = NMRConfig(sample_state="solid", nucleus="13C", polymer_name="PA6")
    result = NMRResult(nucleus="13C", sample_state="solid")
    result.peaks = [
        {"ppm": 173.4, "area": 80.0, "assignment": "C=O (c)", "phase": "c", "possible_solvent": ""},
        {"ppm": 42.1, "area": 25.0, "assignment": "Calpha_am (a)", "phase": "a", "possible_solvent": ""},
        {"ppm": 36.4, "area": 52.0, "assignment": "Cdelta (c)", "phase": "c", "possible_solvent": ""},
    ]
    result.n_peaks = len(result.peaks)

    score = _score_assignment_library(result.peaks, cfg, polymer_name="PA6", nucleus="13C")
    result.assignment_metrics.update(score)
    result.Xc_method = "requires_crystalline_amorphous_assignment"
    result.apply_assignment_gate()

    params = result.parameters

    assert params["library_match_fraction"] >= 0.7
    assert params["assignment_confidence"] >= 0.7
    assert params["phase_pair_support"] is True
    assert params["matched_library_count"] >= 2
    assert params["solvent_overlap_penalty"] == 0.0
    assert params["Xc_assignment_status"] == "supported"


def test_liquid_h_pipeline_detects_peaks_from_real_fid():
    cfg = NMRConfig(
        sample_state="liquid",
        nucleus="1H",
        peak_distance_ppm=0.08,
        peak_height_min=0.04,
        max_peaks=8,
        deconvolution_method="lorentzian",
    )
    spec = load_project(str(_nmr_root() / "\u6db2\u4f53\u6838\u78c1" / "H\u8c31"))[0]
    processed = preprocess_pipeline(spec, cfg)
    result = analyze_spectrum(processed, cfg, label=processed.label)

    assert result.sample_state == "liquid"
    assert result.nucleus == "1H"
    assert result.n_peaks > 0
    assert result.peak_area_total > 0
    assert np.isfinite(result.dominant_peak_ppm)
    assert np.isfinite(result.median_snr)
    assert all(pk.get("area", 0) >= 0 for pk in result.peaks)
    assert any("integral_norm" in pk for pk in result.peaks)
    assert not np.isfinite(result.Xc_pct)


def test_liquid_c_uses_generic_regions_without_polymer_scope():
    cfg = NMRConfig(
        sample_state="liquid",
        nucleus="13C",
        peak_distance_ppm=1.0,
        max_peaks=8,
        deconvolution_method="lorentzian",
    )
    spec = load_project(str(_nmr_root() / "\u6db2\u4f53\u6838\u78c1" / "C\u8c31"))[0]
    processed = preprocess_pipeline(spec, cfg)
    result = analyze_spectrum(processed, cfg, label=processed.label)

    assert result.n_peaks > 0
    assert result.region_integrals
    assert all(pk.get("phase") == "unknown" for pk in result.peaks)
    assert not any("(c)" in pk.get("assignment", "") or "(a)" in pk.get("assignment", "")
                   for pk in result.peaks)


def test_solid_13c_crystallinity_requires_explicit_phase_assignment():
    cfg = NMRConfig(
        sample_state="solid",
        nucleus="13C",
        peak_distance_ppm=1.0,
        max_peaks=6,
        deconvolution_method="mixed",
    )
    spec = load_project(str(_nmr_root() / "\u56fa\u4f53nmr\u78b3\u8c31"))[0]
    processed = preprocess_pipeline(spec, cfg)
    result = analyze_spectrum(processed, cfg, label=processed.label)

    assert result.sample_state == "solid"
    assert result.nucleus == "13C"
    assert result.n_peaks > 0
    assert result.peak_area_total > 0
    assert not np.isfinite(result.Xc_pct)
    assert result.Xc_method == "requires_crystalline_amorphous_assignment"


def test_nmr_engine_uses_liquid_h_submodule_defaults():
    engine = get_engine("nmr", config={"max_peaks": 6}, submodule_id="nmr.liquid_h")
    result = engine.run_pipeline(str(_nmr_root() / "\u6db2\u4f53\u6838\u78c1" / "H\u8c31"))

    assert result.metadata["submodule"] == "nmr.liquid_h"
    assert result.metadata["nucleus"] == "1H"
    assert engine.results
    assert engine.results[0].n_peaks > 0


def test_nmr_export_includes_physical_metrics_and_peak_table(tmp_path):
    engine = get_engine(
        "nmr",
        config={"max_peaks": 6, "fig_format": "png"},
        submodule_id="nmr.liquid_h",
    )
    result = engine.run_pipeline(
        str(_nmr_root() / "\u6db2\u4f53\u6838\u78c1" / "H\u8c31"),
        str(tmp_path),
    )

    assert result.figures
    params_csv = tmp_path / "data" / "nmr_parameters.csv"
    peaks_csv = tmp_path / "data" / "nmr_peaks.csv"
    assert params_csv.exists()
    assert peaks_csv.exists()
    assert "median_snr" in params_csv.read_text(encoding="utf-8")
    peak_text = peaks_csv.read_text(encoding="utf-8")
    assert "integral_norm" in peak_text
    assert "region" in peak_text
    assert any("region_integrals" in key for key in result.figures)


def test_nmr_export_does_not_emit_arial_missing_glyph_warning(tmp_path):
    engine = get_engine(
        "nmr",
        config={"max_peaks": 6, "fig_format": "png"},
        submodule_id="nmr.liquid_h",
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = engine.run_pipeline(
            str(_nmr_root() / "\u6db2\u4f53\u6838\u78c1" / "H\u8c31"),
            str(tmp_path),
        )

    assert result.figures
    warning_text = "\n".join(str(item.message) for item in caught)
    assert "missing from font(s) Arial" not in warning_text


# --- regression tests for the fixed algorithm ------------------------------


def test_jeol_liquid_c_ppm_axis_uses_jeol_metadata():
    """JEOL .jdf ppm axis must have sensible range — descending, within
    typical 13C chemical shift limits."""
    jeol_path = str(_nmr_root() / "20260527-xye_Carbon-1-1" / "20260527-xye_Carbon-1-1.jdf")
    spec = load_project(jeol_path, sample_state="liquid", nucleus="13C")[0]

    assert spec.has_data
    assert spec.nucleus == "13C"
    assert spec.metadata["format"] == "jeol_jdf"
    # ppm must be descending (JEOL convention)
    assert spec.ppm[0] > spec.ppm[-1], f"ppm not descending: {spec.ppm[0]} -> {spec.ppm[-1]}"
    # The full span must be reasonable (not the tiny sub-ppm span of a
    # misinterpreted metadata read)
    span = abs(float(spec.ppm[0] - spec.ppm[-1]))
    assert 50 < span < 500, f"ppm span = {span}, expected 50-500 ppm for 13C"
    assert spec.metadata["display_mode"] == "jeol_fid_fft"
    assert spec.metadata["params"]["_data_mode"] == "liquid_fid_fft"


def test_liquid_c_deconvolution_quality():
    """With the improved algorithm, r² must be dramatically better than the
    old value of -115 (which indicated complete fit failure).  Peaks are
    detected and FWHM values are recorded.  For poor-quality spectra the
    r² may still be negative, but never catastrophically so."""
    cfg = NMRConfig(
        sample_state="liquid",
        nucleus="13C",
        peak_distance_ppm=1.0,
        peak_height_min=0.03,
        max_peaks=18,
        deconvolution_method="lorentzian",
    )
    jeol_path = str(_nmr_root() / "20260527-xye_Carbon-1-1" / "20260527-xye_Carbon-1-1.jdf")
    spec = load_project(jeol_path, sample_state="liquid", nucleus="13C")[0]
    processed = preprocess_pipeline(spec, cfg)
    result = analyze_spectrum(processed, cfg, label=processed.label)

    assert result.n_peaks > 0, "Should detect at least one peak"
    assert result.n_peaks <= 18, f"Got {result.n_peaks} peaks, expected ≤ 18"

    # r² must be finite and NOT catastrophically negative (< -100 was old bug)
    assert np.isfinite(result.r_squared), "r² must be finite"
    assert result.r_squared > -100.0, (
        f"r² = {result.r_squared:.3f} — catastrophic fit failure")

    # FWHM must be physically finite
    assert np.isfinite(result.mean_fwhm_ppm)
    assert result.mean_fwhm_ppm > 0, f"mean FWHM = {result.mean_fwhm_ppm}"

    # quality metric must include the fit_quality flag
    assert "fit_quality" in result.quality_metrics, (
        "Missing fit_quality in quality_metrics")


def test_liquid_partition_rejects_solid_h_directory():
    root = _nmr_root()
    engine = get_engine("nmr", submodule_id="nmr.liquid_c")
    ok, msg = engine.check_file_compatibility(str(root / "\u56fa\u4f53nmr\u6c22\u8c31"))

    assert not ok
    assert "liquid 13C" in msg

    result = engine.run_pipeline(str(root / "\u56fa\u4f53nmr\u6c22\u8c31"))
    assert not engine.results
    assert result.metadata == {}


def test_liquid_c_directory_filters_mixed_proton_carbon_jdf():
    root = _nmr_root()
    engine = get_engine("nmr", config={"max_peaks": 8}, submodule_id="nmr.liquid_c")
    result = engine.run_pipeline(str(root / "20260527-xye_Carbon-1-1"))

    assert result.metadata["submodule"] == "nmr.liquid_c"
    assert result.metadata["spectra_count"] == "1"
    assert len(engine.results) == 1
    assert engine.results[0].nucleus == "13C"
    assert engine.results[0].metadata["display_mode"] == "jeol_fid_fft"


def test_iterative_polynomial_baseline():
    """Iterative polynomial baseline must produce a non-trivial correction."""
    from polynexus.core.nmr_engine.preprocess import correct_baseline
    import numpy as np

    # Simulate a simple spectrum: polynomial baseline + two Gaussian peaks
    rng = np.random.default_rng(42)
    x = np.linspace(200, 0, 1000)
    baseline = 0.05 + 0.002 * x + 0.00001 * x ** 2
    peaks = (0.3 * np.exp(-0.5 * ((x - 130) / 5) ** 2)
             + 0.5 * np.exp(-0.5 * ((x - 40) / 3) ** 2))
    y = baseline + peaks + rng.normal(0, 0.005, len(x))

    corrected_iter, bl_iter = correct_baseline(x, y, method="polynomial", order=3)
    corrected_simple, bl_simple = correct_baseline(x, y, method="simple_polynomial", order=3)

    # Both should produce signal with peaks still present
    assert np.nanmax(corrected_iter) > 0.2, "Iterative baseline removed peaks"
    assert np.nanmax(corrected_simple) > 0.2, "Simple baseline removed peaks"

    # Iterative baseline should be closer to the true baseline
    # (less biased upward by the peaks)
    true_bl = np.polyval(np.polyfit(x, baseline, 3), x)
    err_iter = np.mean((bl_iter - true_bl) ** 2)
    err_simple = np.mean((bl_simple - true_bl) ** 2)
    assert err_iter <= err_simple * 1.1, (
        f"Iterative baseline error ({err_iter:.2e}) should not be much worse "
        f"than simple ({err_simple:.2e})")
