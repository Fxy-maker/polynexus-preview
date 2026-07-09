from __future__ import annotations

import math
from typing import Any


def _saxs_cross_validation(self, output: dict[str, Any]) -> dict[str, Any]:
    validations: list[dict[str, Any]] = []
    l_bragg = self._safe_float(output.get("L_bragg"))
    l_corr = self._safe_float(output.get("L_corr_peak", output.get("L_corr")))
    l_best = self._safe_float(output.get("L_nm", output.get("L_best")))
    if math.isfinite(l_bragg) and math.isfinite(l_best):
        diff = abs(l_bragg - l_best)
        rel = diff / max(abs(l_bragg), abs(l_best), 1e-9)
        validations.append(
            {
                "check_name": f"{self.technique}/L_bragg_vs_L_best",
                "passed": rel <= 0.03,
                "severity": "OK" if rel <= 0.03 else "WARN",
                "message": f"L(Bragg)={l_bragg:.3f} vs L(best)={l_best:.3f} nm",
                "details": {"L_bragg_nm": l_bragg, "L_best_nm": l_best, "diff_nm": diff, "rel_diff": rel},
            }
        )
    if math.isfinite(l_bragg) and math.isfinite(l_corr):
        diff = abs(l_bragg - l_corr)
        rel = diff / max(abs(l_bragg), abs(l_corr), 1e-9)
        validations.append(
            {
                "check_name": f"{self.technique}/L_bragg_vs_L_corr",
                "passed": rel <= 0.03,
                "severity": "OK" if rel <= 0.03 else "WARN",
                "message": f"L(Bragg)={l_bragg:.3f} vs L(corr)={l_corr:.3f} nm",
                "details": {"L_bragg_nm": l_bragg, "L_corr_nm": l_corr, "diff_nm": diff, "rel_diff": rel},
            }
        )
    if output.get("beam_stop_contaminated"):
        validations.append(
            {
                "check_name": f"{self.technique}/beamstop",
                "passed": False,
                "severity": "ERROR",
                "message": "beam_stop_contaminated",
                "details": {"beam_stop_contaminated": True},
            }
        )
    return {"saxs": validations}


def _dsc_cross_validation(self, output: dict[str, Any]) -> dict[str, Any]:
    validations: list[dict[str, Any]] = []
    tm = self._safe_float(output.get("Tm_peak_C"))
    xc = self._safe_float(output.get("Xc_pct"))
    if math.isfinite(tm):
        validations.append(
            {
                "check_name": f"{self.technique}/tm_present",
                "passed": True,
                "severity": "OK",
                "message": f"Tm_peak_C={tm:.2f}",
                "details": {"Tm_peak_C": tm},
            }
        )
    if math.isfinite(xc):
        validations.append(
            {
                "check_name": f"{self.technique}/xc_present",
                "passed": True,
                "severity": "OK",
                "message": f"Xc_pct={xc:.2f}",
                "details": {"Xc_pct": xc},
            }
        )
    return {"dsc": validations}
