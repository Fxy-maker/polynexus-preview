from __future__ import annotations

from PySide6.QtWidgets import QApplication

from polynexus.plot_runtime.spike import (
    AxisGeometry,
    ErrorBarGeometry,
    LegendGeometry,
    LineGeometry,
    MatplotlibSceneRenderer,
    Point,
    QtSceneRenderer,
    compare_raster_images,
    Rect,
    RenderScene,
)


def _representative_scene() -> RenderScene:
    return RenderScene(
        width_px=640,
        height_px=480,
        background="#FFFFFF",
        axis=AxisGeometry(
            rect=Rect(left=88.0, top=48.0, width=480.0, height=344.0),
            x_ticks=((0.0, "0"), (0.5, "0.5"), (1.0, "1.0")),
            y_ticks=((0.0, "0"), (0.5, "0.5"), (1.0, "1.0")),
            x_label="q (nm^-1)",
            y_label="I(q)",
        ),
        lines=(
            LineGeometry(
                object_id="curve",
                points=(
                    Point(88.0, 350.0),
                    Point(184.0, 266.0),
                    Point(328.0, 208.0),
                    Point(472.0, 146.0),
                    Point(568.0, 96.0),
                ),
                color="#0072B2",
                width_px=2.0,
                label="Intensity",
            ),
        ),
        error_bars=(
            ErrorBarGeometry(
                object_id="curve-errors",
                points=(
                    (Point(184.0, 266.0), 16.0),
                    (Point(328.0, 208.0), 12.0),
                    (Point(472.0, 146.0), 10.0),
                ),
                color="#D55E00",
                width_px=1.0,
            ),
        ),
        legend=LegendGeometry(
            object_id="legend",
            anchor=Point(408.0, 72.0),
            label="Intensity",
            color="#0072B2",
        ),
        title="Representative SAXS curve",
    )


def test_qt_and_matplotlib_render_one_shared_scene_within_geometry_tolerance():
    app = QApplication.instance() or QApplication([])
    assert app is not None
    scene = _representative_scene()

    qt_result = QtSceneRenderer().render(scene)
    matplotlib_result = MatplotlibSceneRenderer().render(scene, dpi=100)

    assert not qt_result.image.isNull()
    assert matplotlib_result.figure.canvas.get_width_height() == (640, 480)
    comparison = qt_result.trace.compare_geometry(
        matplotlib_result.trace,
        pixel_tolerance=1.0,
        text_tolerance=2.0,
    )
    assert comparison.passed, comparison.messages


def test_render_trace_reports_geometry_changes_instead_of_hiding_them():
    scene = _representative_scene()
    original = QtSceneRenderer().render(scene).trace
    shifted = QtSceneRenderer().render(
        RenderScene(
            **{
                **scene.__dict__,
                "legend": LegendGeometry(
                    object_id="legend",
                    anchor=Point(440.0, 72.0),
                    label="Intensity",
                    color="#0072B2",
                ),
            }
        )
    ).trace

    comparison = original.compare_geometry(shifted, pixel_tolerance=1.0)

    assert not comparison.passed
    assert any("legend" in message for message in comparison.messages)


def test_actual_raster_difference_stays_below_spike_threshold():
    app = QApplication.instance() or QApplication([])
    assert app is not None
    scene = _representative_scene()
    qt_result = QtSceneRenderer().render(scene)
    matplotlib_result = MatplotlibSceneRenderer().render(scene, dpi=100)

    comparison = compare_raster_images(qt_result.image, matplotlib_result.figure)

    assert comparison.passed, comparison
    assert comparison.mean_absolute_rgb_error <= 6.0
