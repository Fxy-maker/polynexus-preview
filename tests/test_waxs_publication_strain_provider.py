from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.waxs_engine.figure_strain import build_strain_waxs_figure_definitions
from polynexus.plotting.sci_style import AXIS_LABELS


def _point(index: int, *, orientation: float = 0.4, with_image: bool = False) -> SimpleNamespace:
    result = SimpleNamespace(
        label=f"strain-{index}",
        two_theta=np.arange(5.0),
        I=np.asarray([1.0, 2.0, 3.0 + index, 2.0, 1.0]),
        peaks=[{"two_theta": 2.0 + index * 0.1}],
        parameters={"Xc_pct": 20.0 + index, "D_Scherrer_nm": 10.0 + index},
        r_squared=0.95,
        size_reliability_status="reliable",
        sector_used="full",
        quality_flags=[],
    )
    return SimpleNamespace(
        strain_pct=float(index * 10.0),
        phase="ELASTIC",
        Xc_pct=20.0 + index,
        D_Scherrer_nm=10.0 + index,
        D_WH_nm=9.0 + index,
        epsilon_WH_pct=0.2 + index * 0.1,
        f_Herman_avg=orientation,
        lattice_strain_per_peak={"200": 0.1 + index * 0.01},
        r_squared=0.95,
        waxs_result=result,
        with_image=with_image,
    )


def _strain_engine(*, with_images: bool, orientation: float = 0.4) -> SimpleNamespace:
    points = [_point(index, orientation=orientation, with_image=with_images) for index in range(4)]
    scans = []
    for point in points:
        scans.append(SimpleNamespace(image=np.ones((2, 2)) if with_images else None))
    series = SimpleNamespace(
        strains=[point.strain_pct for point in points],
        point_results=points,
        phase_boundaries={},
        stress_induced_cryst=False,
        polymorph_transition=None,
    )
    return SimpleNamespace(_strain_result=series, _dataset=SimpleNamespace(scans=scans))


def _definition(definitions, figure_id: str):
    return next(item for item in definitions if item.figure_id == figure_id)


def test_reliable_strain_series_creates_1d_evolution_main() -> None:
    main = _definition(build_strain_waxs_figure_definitions(_strain_engine(with_images=False)), "waxs.strain.evolution")
    assert main.publication_role == "main"
    assert all(item["type"] != "image_grid" for item in main.objects)


def test_valid_2d_patterns_add_editable_grid() -> None:
    main = _definition(build_strain_waxs_figure_definitions(_strain_engine(with_images=True)), "waxs.strain.evolution")
    assert any(item["type"] == "image_grid" for item in main.objects)
    pattern_panel = main.layout.panels[1]
    assert pattern_panel.x_axis.label == AXIS_LABELS["detector_x"]
    assert pattern_panel.y_axis.label == AXIS_LABELS["detector_y"]


def test_2d_pattern_snapshot_is_bounded_for_publication() -> None:
    engine = _strain_engine(with_images=True)
    for scan in engine._dataset.scans:
        scan.image = np.arange(513 * 517, dtype=float).reshape(513, 517)

    main = _definition(build_strain_waxs_figure_definitions(engine), "waxs.strain.evolution")
    source = next(item for item in main.data_sources if item.source_id == "waxs-strain-image-grid")

    frame_cells = sorted(set(zip(source.values["grid_column"], source.values["grid_row"])))
    assert len(frame_cells) == 3
    for column, row in frame_cells:
        mask = [
            current_column == column and current_row == row
            for current_column, current_row in zip(
                source.values["grid_column"], source.values["grid_row"]
            )
        ]
        assert sum(mask) <= 256 * 256
    assert len(source.values["pixel_x"]) == len(source.values["intensity"])


def test_invalid_orientation_is_not_main_response() -> None:
    definitions = build_strain_waxs_figure_definitions(_strain_engine(with_images=False, orientation=np.nan))
    assert "waxs.strain.orientation" not in {item.figure_id for item in definitions if item.publication_role == "main"}
