from __future__ import annotations


def _waxs_actionable_constraint_lines(soft_warn_names: set[str]) -> list[str]:
    names = {str(name).strip() for name in soft_warn_names if str(name).strip()}
    lines: list[str] = []
    if "scherrer_instrument_broadening_unresolved" in names:
        lines.append(
            "scherrer_instrument_broadening_unresolved -> keep D provisional until instrument broadening is modeled or documented"
        )
    if "scherrer_jump_single_frame" in names:
        lines.append("scherrer_jump_single_frame -> review the unstable frame before trusting the temperature trend")
    if "scherrer_dominated_by_peak_width_noise" in names:
        lines.append("scherrer_dominated_by_peak_width_noise -> stabilize peak widths and family tracking before promoting D")
    return lines


__all__ = ["_waxs_actionable_constraint_lines"]
