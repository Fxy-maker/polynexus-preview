from __future__ import annotations

from polynexus.gui.results_workbench_profiles import profile_for


def test_ir_profiles_expose_mode_specific_narratives_and_known_figure_entrypoints() -> None:
    assert tuple(link.key for link in profile_for("ir.standard").figure_links) == (
        "ir.frame.spectrum.001",
        "ir.series.crystallinity",
    )
    assert tuple(link.key for link in profile_for("ir.temperature_2d").figure_links) == (
        "ir.temperature_2d.heatmap",
        "ir.temperature_2d.band-tracking",
    )
    assert profile_for("ir.mapping").tab_labels == (
        "Map & ROI",
        "Band assignments",
        "Pixel diagnostics",
    )


def test_nmr_and_joint_profiles_are_customized() -> None:
    assert profile_for("nmr.liquid_h").tab_labels == (
        "Peaks & assignments",
        "Solvent / fit support",
        "SNR & overlap diagnostics",
    )
    assert profile_for("nmr.solid_c").tab_labels == (
        "Phase & composition",
        "Assignment coverage",
        "Broad-line diagnostics",
    )
    assert profile_for("nmr.liquid_c").tab_labels == profile_for("nmr.liquid_h").tab_labels
    assert profile_for("nmr.solid_h").tab_labels == profile_for("nmr.solid_c").tab_labels
    assert tuple(link.key for link in profile_for("joint").figure_links) == (
        "joint.series.crystallinity",
        "joint.series.multiscale",
    )
