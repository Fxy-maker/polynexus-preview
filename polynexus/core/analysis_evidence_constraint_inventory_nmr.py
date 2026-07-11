from __future__ import annotations

from .analysis_evidence_constraint_models import EvidenceConstraint, _inventory


def _nmr_constraint_inventory() -> list[EvidenceConstraint]:
    return _inventory(
        EvidenceConstraint(
            name="fit_quality",
            kind="soft_warn",
            source="NMR",
            severity="WARN",
            description="Low-quality deconvolution should reduce confidence.",
            field="quality_metrics.fit_quality",
            rationale="Fit quality should be visible to the orchestrator.",
        ),
        EvidenceConstraint(
            name="peak_snr",
            kind="evidence_only",
            source="NMR",
            severity="INFO",
            description="Median SNR is a supporting confidence signal.",
            field="median_snr",
            rationale="Use it to contextualize line-shape and assignment reliability.",
        ),
        EvidenceConstraint(
            name="nmr_low_peak_count",
            kind="soft_warn",
            source="NMR",
            severity="WARN",
            description="Too few resolved NMR peaks to support strong assignment confidence.",
            field="n_peaks",
            rationale="Assignments and Xc estimates need enough resolved peak support.",
        ),
        EvidenceConstraint(
            name="nmr_low_snr",
            kind="soft_warn",
            source="NMR",
            severity="WARN",
            description="Median NMR SNR is too low for strong assignment confidence.",
            field="median_snr",
            rationale="Low SNR makes peak detection, deconvolution, and assignment fragile.",
        ),
        EvidenceConstraint(
            name="nmr_broad_linewidth",
            kind="soft_warn",
            source="NMR",
            severity="WARN",
            description="NMR linewidth is broad enough to weaken peak separation and phase assignment.",
            field="mean_fwhm_ppm",
            rationale="Broad peaks make crystalline/amorphous peak partitioning less reliable.",
        ),
        EvidenceConstraint(
            name="nmr_weak_assignment",
            kind="soft_warn",
            source="NMR",
            severity="WARN",
            description="Detected NMR peaks are not backed by enough assignments or database matches.",
            field="n_matches",
            rationale="Peak-derived conclusions should stay provisional when assignments are sparse.",
        ),
        EvidenceConstraint(
            name="nmr_solvent_risk",
            kind="soft_warn",
            source="NMR",
            severity="WARN",
            description="One or more NMR peaks overlap likely solvent regions.",
            field="peak_possible_solvent",
            rationale="Solvent-like peaks can inflate or mislead assignment evidence.",
        ),
        EvidenceConstraint(
            name="nmr_xc_assignment_missing",
            kind="soft_warn",
            source="NMR",
            severity="WARN",
            description="NMR crystallinity requires crystalline/amorphous peak assignment support.",
            field="Xc_method",
            rationale="Solid-state NMR Xc should not be promoted before phase assignments are explicit.",
        ),
        EvidenceConstraint(
            name="nmr_xc_assignment_limited",
            kind="soft_warn",
            source="NMR",
            severity="WARN",
            description="NMR Xc is present without crystalline/amorphous phase assignment support.",
            field="Xc_method",
            rationale="Assignment-limited Xc should not enter Joint as strong crystallinity evidence.",
        ),
    )
