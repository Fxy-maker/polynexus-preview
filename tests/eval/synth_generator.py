from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
from numpy.typing import NDArray


Array = NDArray[np.float64]


@dataclass(frozen=True)
class GeneratedCase:
    case_id: str
    data_path: Path
    json_path: Path


class SynthGenerator:
    CASE_IDS = (
        "waxs_synth_pa6_alpha",
        "waxs_synth_pa6_alpha_gamma",
        "waxs_synth_pet",
        "waxs_synth_ipp_alpha",
        "waxs_synth_low_xc",
        "dsc_synth_heating_standard",
        "dsc_synth_heating_cold_cc",
        "dsc_synth_cooling",
        "dsc_synth_no_tg",
        "saxs_synth_lamellar",
        "saxs_synth_guinier_only",
        "saxs_synth_noisy",
        "ir_synth_pa6_standard",
        "ir_synth_pa6_amide",
        "ir_synth_noisy",
        "nmr_synth_pa6_carbon",
        "nmr_synth_pa6_proton",
        "nmr_synth_noisy",
    )

    def __init__(self, output_dir: str | Path = "tests/eval/", seed: int = 42):
        self.output_dir = Path(output_dir)
        self.seed = seed
        self.data_dir = self.output_dir / "synth_data"
        self.case_dir = self.output_dir / "cases" / "synth"
        self.real_dir = self.output_dir / "cases" / "real"

    def generate_all(self) -> list[GeneratedCase]:
        self._prepare_dirs()
        generated: list[GeneratedCase] = []
        generators: list[Callable[[int], GeneratedCase]] = [
            self._waxs_pa6_alpha,
            self._waxs_pa6_alpha_gamma,
            self._waxs_pet,
            self._waxs_ipp_alpha,
            self._waxs_low_xc,
            self._dsc_heating_standard,
            self._dsc_heating_cold_cc,
            self._dsc_cooling,
            self._dsc_no_tg,
            self._saxs_lamellar,
            self._saxs_guinier_only,
            self._saxs_noisy,
            self._ir_pa6_standard,
            self._ir_pa6_amide,
            self._ir_noisy,
            self._nmr_pa6_carbon,
            self._nmr_pa6_proton,
            self._nmr_noisy,
        ]
        for index, generator in enumerate(generators):
            generated.append(generator(self.seed + index))
        return generated

    def _prepare_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.case_dir.mkdir(parents=True, exist_ok=True)
        self.real_dir.mkdir(parents=True, exist_ok=True)
        for path in self.data_dir.glob("*.xy"):
            path.unlink()
        for path in self.case_dir.glob("*.json"):
            path.unlink()

    def _waxs_pa6_alpha(self, seed: int) -> GeneratedCase:
        case_id = "waxs_synth_pa6_alpha"
        x, y = self._make_waxs(
            seed,
            peaks=[(20.0, 1.0), (24.0, 0.8)],
            halos=[(21.0, 0.55, 8.0)],
            xc_pct=45.0,
            noise_gain=35.0,
        )
        return self._write_case(
            case_id,
            x,
            y,
            technique="waxs",
            submodule="static",
            polymer_name="PA6",
            polymer_phase="alpha",
            ground_truth={
                "Xc_pct": [42.0, 48.0],
                "peak_centers": [[19.85, 20.15], [23.85, 24.15]],
                "D_Scherrer_nm": [8.0, 15.0],
                "crystal_form": "alpha",
            },
            config_overrides={"polymer_type": "PA6_alpha", "amorphous_n_peaks": 1},
            notes="Synthetic PA6 alpha WAXS with two crystal peaks and one amorphous halo.",
        )

    def _waxs_pa6_alpha_gamma(self, seed: int) -> GeneratedCase:
        case_id = "waxs_synth_pa6_alpha_gamma"
        x, y = self._make_waxs(
            seed,
            peaks=[(20.0, 1.0), (21.5, 0.65), (24.0, 0.75)],
            halos=[(20.8, 0.45, 7.0), (25.0, 0.35, 10.0)],
            xc_pct=35.0,
            noise_gain=30.0,
        )
        return self._write_case(
            case_id,
            x,
            y,
            technique="waxs",
            submodule="static",
            polymer_name="PA6",
            polymer_phase="alpha_gamma",
            ground_truth={
                "Xc_pct": [32.0, 38.0],
                "peak_centers": [[19.85, 20.15], [21.35, 21.65], [23.85, 24.15]],
                "D_Scherrer_nm": [6.0, 14.0],
                "crystal_form": "alpha_gamma",
            },
            config_overrides={"polymer_type": "PA6_alpha_gamma", "amorphous_n_peaks": 2},
            notes="Synthetic PA6 mixed alpha/gamma WAXS with three crystal peaks.",
        )

    def _waxs_pet(self, seed: int) -> GeneratedCase:
        case_id = "waxs_synth_pet"
        x, y = self._make_waxs(
            seed,
            peaks=[(16.3, 0.55), (17.5, 0.7), (22.5, 1.0), (25.6, 0.8), (32.2, 0.35)],
            halos=[(21.0, 0.6, 9.0)],
            xc_pct=30.0,
            noise_gain=32.0,
        )
        return self._write_case(
            case_id,
            x,
            y,
            technique="waxs",
            submodule="static",
            polymer_name="PET",
            polymer_phase=None,
            ground_truth={
                "Xc_pct": [27.0, 33.0],
                "peak_centers": [[16.15, 16.45], [17.35, 17.65], [22.35, 22.65], [25.45, 25.75], [32.0, 32.4]],
                "D_Scherrer_nm": [7.0, 16.0],
            },
            config_overrides={"polymer_type": "PET"},
            notes="Synthetic PET WAXS with five literature-like crystal peaks.",
        )

    def _waxs_ipp_alpha(self, seed: int) -> GeneratedCase:
        case_id = "waxs_synth_ipp_alpha"
        x, y = self._make_waxs(
            seed,
            peaks=[(14.1, 1.0), (16.9, 0.65), (18.6, 0.7), (21.2, 0.55), (21.9, 0.45)],
            halos=[(18.5, 0.5, 8.0)],
            xc_pct=50.0,
            noise_gain=35.0,
        )
        return self._write_case(
            case_id,
            x,
            y,
            technique="waxs",
            submodule="static",
            polymer_name="iPP",
            polymer_phase="alpha",
            ground_truth={
                "Xc_pct": [47.0, 53.0],
                "peak_centers": [[13.95, 14.25], [16.75, 17.05], [18.45, 18.75], [21.05, 21.35], [21.75, 22.05]],
                "D_Scherrer_nm": [9.0, 20.0],
                "crystal_form": "alpha",
            },
            config_overrides={"polymer_type": "iPP_alpha"},
            notes="Synthetic isotactic polypropylene alpha WAXS.",
        )

    def _waxs_low_xc(self, seed: int) -> GeneratedCase:
        case_id = "waxs_synth_low_xc"
        x, y = self._make_waxs(
            seed,
            peaks=[(20.0, 1.0), (24.0, 0.8)],
            halos=[(21.5, 0.9, 10.0), (27.0, 0.35, 12.0)],
            xc_pct=15.0,
            noise_gain=8.0,
        )
        return self._write_case(
            case_id,
            x,
            y,
            technique="waxs",
            submodule="static",
            polymer_name="PA6",
            polymer_phase="alpha",
            ground_truth={
                "Xc_pct": [12.0, 18.0],
                "peak_centers": [[19.8, 20.2], [23.8, 24.2]],
                "D_Scherrer_nm": [5.0, 12.0],
                "crystal_form": "alpha",
            },
            config_overrides={"polymer_type": "PA6_alpha", "amorphous_n_peaks": 2},
            notes="Synthetic low-crystallinity PA6 WAXS with high noise.",
        )

    def _dsc_heating_standard(self, seed: int) -> GeneratedCase:
        case_id = "dsc_synth_heating_standard"
        x, y = self._make_dsc(seed, tg=50.0, tcc=120.0, tm=220.0, cooling=False)
        return self._write_case(
            case_id,
            x,
            y,
            technique="dsc",
            submodule="heating",
            polymer_name="PA6",
            polymer_phase=None,
            ground_truth={
                "Tg_C": [47.0, 53.0],
                "Tc_peak_C": [116.0, 124.0],
                "Tm_peak_C": [216.0, 224.0],
                "DHm_Jg": [45.0, 65.0],
                "Xc_pct": [28.0, 40.0],
            },
            config_overrides={"scan_direction": "heating"},
            notes="Synthetic PA6 heating DSC with Tg, cold crystallization, and melting.",
        )

    def _dsc_heating_cold_cc(self, seed: int) -> GeneratedCase:
        case_id = "dsc_synth_heating_cold_cc"
        x, y = self._make_dsc(seed, tg=50.0, tcc=80.0, tm=220.0, cooling=False, tcc_amp=1.8)
        return self._write_case(
            case_id,
            x,
            y,
            technique="dsc",
            submodule="heating",
            polymer_name="PA6",
            polymer_phase=None,
            ground_truth={
                "Tg_C": [47.0, 53.0],
                "Tc_peak_C": [76.0, 84.0],
                "Tm_peak_C": [216.0, 224.0],
                "DHm_Jg": [38.0, 58.0],
                "Xc_pct": [24.0, 36.0],
            },
            config_overrides={"scan_direction": "heating"},
            notes="Synthetic heating DSC with a cold-crystallization peak close to Tg.",
        )

    def _dsc_cooling(self, seed: int) -> GeneratedCase:
        case_id = "dsc_synth_cooling"
        x, y = self._make_dsc(seed, tg=None, tcc=170.0, tm=None, cooling=True, tcc_amp=1.6)
        return self._write_case(
            case_id,
            x,
            y,
            technique="dsc",
            submodule="cooling",
            polymer_name="PA6",
            polymer_phase=None,
            ground_truth={"Tc_peak_C": [166.0, 174.0], "DHm_Jg": [35.0, 60.0], "Xc_pct": [24.0, 38.0]},
            config_overrides={"scan_direction": "cooling"},
            notes="Synthetic cooling DSC with crystallization near 170 C.",
        )

    def _dsc_no_tg(self, seed: int) -> GeneratedCase:
        case_id = "dsc_synth_no_tg"
        x, y = self._make_dsc(seed, tg=None, tcc=None, tm=220.0, cooling=False, tm_amp=1.4)
        return self._write_case(
            case_id,
            x,
            y,
            technique="dsc",
            submodule="heating",
            polymer_name="PA6",
            polymer_phase=None,
            ground_truth={"Tm_peak_C": [216.0, 224.0], "DHm_Jg": [42.0, 62.0], "Xc_pct": [26.0, 38.0]},
            config_overrides={"scan_direction": "heating"},
            notes="Synthetic heating DSC with no Tg step and one melting peak.",
        )

    def _saxs_lamellar(self, seed: int) -> GeneratedCase:
        case_id = "saxs_synth_lamellar"
        x, y = self._make_saxs(seed, L_nm=12.0, rg_nm=4.8, noisy=False, bragg=True)
        return self._write_case(
            case_id,
            x,
            y,
            technique="saxs",
            submodule="static",
            polymer_name="PA6",
            polymer_phase=None,
            ground_truth={"L_nm": [11.5, 12.5], "lc_nm": [5.0, 7.0], "phi_c": [0.40, 0.55], "Rg_nm": [4.2, 5.4]},
            config_overrides={"L_method": "bragg"},
            notes="Synthetic SAXS with a clear lamellar Bragg peak at L about 12 nm.",
        )

    def _saxs_guinier_only(self, seed: int) -> GeneratedCase:
        case_id = "saxs_synth_guinier_only"
        x, y = self._make_saxs(seed, L_nm=None, rg_nm=5.5, noisy=False, bragg=False)
        return self._write_case(
            case_id,
            x,
            y,
            technique="saxs",
            submodule="static",
            polymer_name="PA6",
            polymer_phase=None,
            ground_truth={"Rg_nm": [4.8, 6.2], "phi_c": [0.20, 0.40]},
            config_overrides={"L_method": "auto"},
            notes="Synthetic SAXS without a Bragg peak, emphasizing Guinier and Porod regions.",
        )

    def _saxs_noisy(self, seed: int) -> GeneratedCase:
        case_id = "saxs_synth_noisy"
        x, y = self._make_saxs(seed, L_nm=13.5, rg_nm=5.0, noisy=True, bragg=True)
        return self._write_case(
            case_id,
            x,
            y,
            technique="saxs",
            submodule="static",
            polymer_name="PA6",
            polymer_phase=None,
            ground_truth={"L_nm": [12.8, 14.2], "lc_nm": [4.5, 7.0], "phi_c": [0.30, 0.50], "Rg_nm": [4.2, 5.8]},
            config_overrides={"L_method": "bragg", "smooth_window": 11},
            notes="Synthetic noisy SAXS case with a weak lamellar peak.",
        )

    def _ir_pa6_standard(self, seed: int) -> GeneratedCase:
        case_id = "ir_synth_pa6_standard"
        x, y = self._make_ir(seed, [(3295, 0.7), (2930, 0.35), (1635, 1.0), (1535, 0.8), (1260, 0.4)], 0.012)
        return self._write_case(
            case_id,
            x,
            y,
            technique="ir",
            submodule="static",
            polymer_name="PA6",
            polymer_phase=None,
            ground_truth={"peak_wavenumbers": [[3290, 3300], [2925, 2935], [1630, 1640], [1530, 1540], [1255, 1265]]},
            config_overrides={"lineshape": "lorentzian"},
            notes="Synthetic standard PA6 FTIR spectrum.",
        )

    def _ir_pa6_amide(self, seed: int) -> GeneratedCase:
        case_id = "ir_synth_pa6_amide"
        x, y = self._make_ir(seed, [(3295, 0.45), (1635, 1.45), (1535, 1.25), (1465, 0.45), (1260, 0.3)], 0.010)
        return self._write_case(
            case_id,
            x,
            y,
            technique="ir",
            submodule="static",
            polymer_name="PA6",
            polymer_phase=None,
            ground_truth={"peak_wavenumbers": [[3290, 3300], [1630, 1640], [1530, 1540], [1460, 1470], [1255, 1265]]},
            config_overrides={"lineshape": "lorentzian"},
            notes="Synthetic PA6 FTIR with emphasized amide I and II bands.",
        )

    def _ir_noisy(self, seed: int) -> GeneratedCase:
        case_id = "ir_synth_noisy"
        x, y = self._make_ir(seed, [(3295, 0.6), (2930, 0.25), (1635, 0.95), (1535, 0.75)], 0.045)
        return self._write_case(
            case_id,
            x,
            y,
            technique="ir",
            submodule="static",
            polymer_name="PA6",
            polymer_phase=None,
            ground_truth={"peak_wavenumbers": [[3288, 3302], [2923, 2937], [1628, 1642], [1528, 1542]]},
            config_overrides={"lineshape": "lorentzian", "smooth_window": 11},
            notes="Synthetic noisy PA6 FTIR spectrum.",
        )

    def _nmr_pa6_carbon(self, seed: int) -> GeneratedCase:
        case_id = "nmr_synth_pa6_carbon"
        x, y = self._make_nmr(seed, 200.0, 0.0, [(173.0, 1.0), (42.0, 0.65), (36.0, 0.6), (29.0, 0.5), (25.0, 0.45)], 0.010)
        return self._write_case(
            case_id,
            x,
            y,
            technique="nmr",
            submodule="liquid_c",
            polymer_name="PA6",
            polymer_phase=None,
            ground_truth={"peak_shifts": [[172.5, 173.5], [41.5, 42.5], [35.5, 36.5], [28.5, 29.5], [24.5, 25.5]]},
            config_overrides={"nucleus": "13C", "deconvolution_method": "mixed"},
            notes="Synthetic PA6 13C NMR spectrum.",
        )

    def _nmr_pa6_proton(self, seed: int) -> GeneratedCase:
        case_id = "nmr_synth_pa6_proton"
        x, y = self._make_nmr(seed, 6.0, 0.0, [(3.25, 0.85), (2.25, 0.75), (1.62, 1.0), (1.35, 0.6)], 0.008)
        return self._write_case(
            case_id,
            x,
            y,
            technique="nmr",
            submodule="liquid_h",
            polymer_name="PA6",
            polymer_phase=None,
            ground_truth={"peak_shifts": [[3.15, 3.35], [2.15, 2.35], [1.52, 1.72], [1.25, 1.45]]},
            config_overrides={"nucleus": "1H", "deconvolution_method": "mixed"},
            notes="Synthetic PA6 1H NMR spectrum.",
        )

    def _nmr_noisy(self, seed: int) -> GeneratedCase:
        case_id = "nmr_synth_noisy"
        x, y = self._make_nmr(seed, 200.0, 0.0, [(173.0, 0.9), (42.0, 0.55), (36.0, 0.45), (29.0, 0.35)], 0.045)
        return self._write_case(
            case_id,
            x,
            y,
            technique="nmr",
            submodule="liquid_c",
            polymer_name="PA6",
            polymer_phase=None,
            ground_truth={"peak_shifts": [[172.3, 173.7], [41.3, 42.7], [35.3, 36.7], [28.3, 29.7]]},
            config_overrides={"nucleus": "13C", "deconvolution_method": "mixed", "lb_Hz": 8.0},
            notes="Synthetic noisy PA6 13C NMR spectrum.",
        )

    def _write_case(
        self,
        case_id: str,
        x: Array,
        y: Array,
        *,
        technique: str,
        submodule: str,
        polymer_name: str,
        polymer_phase: str | None,
        ground_truth: dict[str, Any],
        config_overrides: dict[str, Any],
        notes: str,
    ) -> GeneratedCase:
        data_path = self.data_dir / f"{case_id}.xy"
        json_path = self.case_dir / f"{case_id}.json"
        np.savetxt(data_path, np.column_stack((x, y)), fmt="%.8f")
        payload = {
            "case_id": case_id,
            "technique": technique,
            "submodule": submodule,
            "data_file": f"synth:{case_id}",
            "polymer_name": polymer_name,
            "polymer_phase": polymer_phase,
            "config_overrides": {"rng_seed": self.seed, **config_overrides},
            "ground_truth": ground_truth,
            "source": "synthetic",
            "notes": notes,
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return GeneratedCase(case_id=case_id, data_path=data_path, json_path=json_path)

    def _make_waxs(
        self,
        seed: int,
        *,
        peaks: list[tuple[float, float]],
        halos: list[tuple[float, float, float]],
        xc_pct: float,
        noise_gain: float,
    ) -> tuple[Array, Array]:
        rng = np.random.default_rng(seed)
        x = np.linspace(5.0, 45.0, 1600, dtype=np.float64)
        slope = rng.uniform(-0.5, 0.5)
        y = 45.0 + slope * (x - x.mean())
        peak_scale = 260.0 * (xc_pct / 45.0)
        for center, rel_amp in peaks:
            sigma = rng.uniform(0.20, 0.80)
            eta = rng.uniform(0.30, 0.55)
            y += peak_scale * rel_amp * self._pseudo_voigt(x, center, sigma, eta)
        for center, rel_amp, sigma in halos:
            eta = rng.uniform(0.35, 0.60)
            y += 170.0 * rel_amp * self._pseudo_voigt(x, center, sigma, eta)
        return x, self._poisson_noise(y, rng, gain=noise_gain)

    def _make_dsc(
        self,
        seed: int,
        *,
        tg: float | None,
        tcc: float | None,
        tm: float | None,
        cooling: bool,
        tcc_amp: float = 1.1,
        tm_amp: float = 1.2,
    ) -> tuple[Array, Array]:
        rng = np.random.default_rng(seed)
        x = np.linspace(260.0, -20.0, 1400, dtype=np.float64) if cooling else np.linspace(-20.0, 260.0, 1400)
        y = 0.002 * (x - x.mean()) + 0.05
        if tg is not None:
            y += 0.20 / (1.0 + np.exp(-(x - tg) / 2.0))
        if tcc is not None:
            sign = 1.0 if cooling else -1.0
            y += sign * tcc_amp * self._gaussian(x, tcc, 7.5)
        if tm is not None:
            y += tm_amp * self._gaussian(x, tm, 9.0)
        y += rng.normal(0.0, 0.025, size=x.size)
        return x.astype(np.float64), y.astype(np.float64)

    def _make_saxs(self, seed: int, *, L_nm: float | None, rg_nm: float, noisy: bool, bragg: bool) -> tuple[Array, Array]:
        rng = np.random.default_rng(seed)
        q = np.linspace(0.005, 1.2, 1400, dtype=np.float64)
        guinier = 8.0 * np.exp(-(q * rg_nm) ** 2 / 3.0)
        porod = 0.0004 / np.power(q + 0.015, 4.0)
        y = guinier + porod + 0.04
        if bragg and L_nm is not None:
            q0 = 2.0 * np.pi / L_nm
            y += 6.0 * self._lorentzian(q, q0, 0.018)
        gain = 18.0 if noisy else 70.0
        return q, self._poisson_noise(y, rng, gain=gain)

    def _make_ir(self, seed: int, peaks: list[tuple[float, float]], noise_sigma: float) -> tuple[Array, Array]:
        rng = np.random.default_rng(seed)
        x = np.linspace(4000.0, 600.0, 2400, dtype=np.float64)
        y = 0.08 + 0.00002 * (4000.0 - x)
        for center, amp in peaks:
            width = 10.0 if center > 2500 else 7.0
            y += amp * self._lorentzian(x, center, width)
        y += rng.normal(0.0, noise_sigma, size=x.size)
        return x, np.clip(y, 0.0, None).astype(np.float64)

    def _make_nmr(self, seed: int, start: float, stop: float, peaks: list[tuple[float, float]], noise_sigma: float) -> tuple[Array, Array]:
        rng = np.random.default_rng(seed)
        x = np.linspace(start, stop, 2200, dtype=np.float64)
        y = 0.02 + 0.0001 * (x - x.min())
        width = 0.10 if start <= 10.0 else 0.45
        for center, amp in peaks:
            y += amp * self._lorentzian(x, center, width)
        y += rng.normal(0.0, noise_sigma, size=x.size)
        return x, np.clip(y, 0.0, None).astype(np.float64)

    @staticmethod
    def _gaussian(x: Array, center: float, sigma: float) -> Array:
        return np.exp(-0.5 * np.square((x - center) / sigma))

    @staticmethod
    def _lorentzian(x: Array, center: float, gamma: float) -> Array:
        return 1.0 / (1.0 + np.square((x - center) / gamma))

    @classmethod
    def _pseudo_voigt(cls, x: Array, center: float, sigma: float, eta: float) -> Array:
        return eta * cls._lorentzian(x, center, sigma) + (1.0 - eta) * cls._gaussian(x, center, sigma)

    @staticmethod
    def _poisson_noise(y: Array, rng: np.random.Generator, *, gain: float) -> Array:
        positive = np.clip(y, 0.0, None)
        noisy = rng.poisson(positive * gain) / gain
        return noisy.astype(np.float64)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate PolyNexus synthetic eval cases.")
    parser.add_argument("--output-dir", default="tests/eval/", help="Eval output directory.")
    parser.add_argument("--seed", type=int, default=42, help="Base RNG seed.")
    args = parser.parse_args(argv)

    generator = SynthGenerator(output_dir=args.output_dir, seed=args.seed)
    generated = generator.generate_all()
    print(f"Generated {len(generated)} synthetic eval cases under {generator.output_dir}")
    print(f"Data files: {generator.data_dir}")
    print(f"Case JSON:  {generator.case_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
