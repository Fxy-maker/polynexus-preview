from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from polynexus.core.saxs_engine import io as saxs_io
from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.figures.reactive_project_service import (
    ReactiveFigureProjectService,
)
from polynexus.core.saxs_engine.figure_static import (
    build_static_saxs_figure_definitions,
)
from polynexus.core.saxs_engine.figure_temperature import (
    build_temperature_figure_definitions,
)
from polynexus.core.saxs_engine.saxs_temperature import TempSeriesResult
from polynexus.plot_runtime.matplotlib_renderer import PublicationProfile


def _static_engine(paths: list[str]) -> SimpleNamespace:
    q = np.asarray([0.1, 0.2, 0.4, 0.8], dtype=float)
    rows = [
        {
            "file": path,
            "L_nm": 15.0 + index,
            "Q_rel": 1.0,
            "Q_star_valid": True,
            "lc_confidence": 0.8,
            "paper_figure_candidate": True,
            "paper_conclusion_candidate": True,
        }
        for index, path in enumerate(paths)
    ]
    analyses = [
        SimpleNamespace(
            label=f"static-{index}",
            condition_value=float(index),
            q=q,
            I=np.asarray([100.0, 70.0, 28.0, 8.0]) - index,
            quality_flag="OK",
            final_parameters=row,
            fit_regions=(),
            correlation=None,
            idf=None,
            porod=None,
            kratky=None,
        )
        for index, row in enumerate(rows)
    ]
    return SimpleNamespace(
        _batch_results=analyses,
        _batch_params=rows,
        _q_list=[q.copy() for _ in analyses],
        _I_list=[item.I for item in analyses],
        _conditions=list(range(len(paths))),
        _file_list=paths,
        _analysis=None,
        _temperature_result=None,
        _strain_result=None,
        _condition_type="static",
        cfg=SimpleNamespace(experiment_type="static"),
    )


def _temperature_engine(paths: list[str]) -> SimpleNamespace:
    q = np.asarray([0.08, 0.12, 0.18, 0.25], dtype=float)
    parameters = [
        {
            "file": path,
            "quality_flag": "OK",
            "L_nm": 12.0 + index,
            "lc_nm": 4.0 + index * 0.2,
            "la_nm": 8.0 + index * 0.8,
            "q_star_nm1": 0.45 + index * 0.01,
            "Xc_effective": 0.4 + index * 0.05,
        }
        for index, path in enumerate(paths)
    ]
    analyses = [
        SimpleNamespace(
            label=f"temperature-{index}",
            correlation={"r": [1.0, 2.0], "gamma": [0.8, 0.5]},
            idf={"r_idf": [1.0, 2.0], "idf": [0.2, 0.4]},
            final_parameters=row,
        )
        for index, row in enumerate(parameters)
    ]
    result = TempSeriesResult(
        temperatures=np.arange(len(paths), dtype=float),
        L_array=np.asarray([row["L_nm"] for row in parameters], dtype=float),
        lc_array=np.asarray([row["lc_nm"] for row in parameters], dtype=float),
        lc_effective_array=np.asarray(
            [row["lc_nm"] for row in parameters], dtype=float
        ),
        Q_star_array=np.asarray(
            [row["q_star_nm1"] for row in parameters], dtype=float
        ),
        Xc_array=np.asarray(
            [row["Xc_effective"] for row in parameters], dtype=float
        ),
        avrami={},
    )
    return SimpleNamespace(
        _temperature_result=result,
        _batch_results=analyses,
        _batch_params=parameters,
        _q_list=[q.copy() for _ in paths],
        _I_list=[np.asarray([8.0, 6.0, 3.0, 1.0]) for _ in paths],
        _conditions=np.arange(len(paths), dtype=float),
        _file_list=paths,
        _condition_type="temperature",
        cfg=SimpleNamespace(
            experiment_type="temperature",
            condition_label="Temperature",
            condition_unit="C",
        ),
    )


def test_static_detector_figure_projects_finite_pixels_and_counts(monkeypatch):
    engine = _static_engine(["static-0.edf", "static-1.edf"])
    monkeypatch.setattr(
        saxs_io,
        "read_image",
        lambda _path: (np.asarray([[1.0, np.nan], [4.0, 16.0]]), {}),
    )

    definition = next(
        item
        for item in build_static_saxs_figure_definitions(engine)
        if item.figure_id == "saxs.static.detector.2d"
    )
    source = definition.data_sources[0]

    assert source.values["pixel_x"] == (0, 0, 1)
    assert source.values["pixel_y"] == (0, 1, 1)
    assert definition.recipe["parameters"]["detector_projection_quality"]["0"] == {
        "sampled_pixel_count": 4,
        "retained_pixel_count": 3,
        "nonfinite_pixel_count": 1,
        "status": "partial_nonfinite",
    }
    assert definition.publication_role == "diagnostic"
    json.dumps(definition.recipe, allow_nan=False)


def test_static_detector_figure_projects_malformed_pixel_elementwise(monkeypatch):
    engine = _static_engine(["static-0.edf"])
    monkeypatch.setattr(
        saxs_io,
        "read_image",
        lambda _path: (
            np.asarray([[1.0, "bad-pixel"], [4.0, 16.0]], dtype=object),
            {},
        ),
    )

    definition = next(
        item
        for item in build_static_saxs_figure_definitions(engine)
        if item.figure_id == "saxs.static.detector.2d"
    )
    source = definition.data_sources[0]

    assert source.values["pixel_x"] == (0, 0, 1)
    assert source.values["pixel_y"] == (0, 1, 1)
    assert definition.recipe["parameters"]["detector_projection_quality"]["0"] == {
        "sampled_pixel_count": 4,
        "retained_pixel_count": 3,
        "nonfinite_pixel_count": 1,
        "status": "partial_nonfinite",
    }


def test_temperature_detector_figure_preserves_selected_frame_indices(monkeypatch):
    engine = _temperature_engine(
        ["temperature-0.edf", "temperature-1.edf", "temperature-2.edf"]
    )
    monkeypatch.setattr(
        saxs_io,
        "read_image",
        lambda _path: (np.ones((2, 2)), {}),
    )

    definition = next(
        item
        for item in build_temperature_figure_definitions(engine)
        if item.figure_id == "saxs.temperature.detector.2d"
    )

    assert definition.recipe["parameters"]["included_frame_indices"] == [0, 1, 2]
    assert definition.recipe["parameters"]["detector_projection_quality"]["1"] == {
        "sampled_pixel_count": 4,
        "retained_pixel_count": 4,
        "nonfinite_pixel_count": 0,
        "status": "complete",
    }
    assert definition.layout.panels[0].x_axis.label == r"Detector $x$ (pixel)"
    assert definition.publication_role == "diagnostic"
    json.dumps(definition.recipe, allow_nan=False)


def test_detector_reader_failure_is_recorded_alongside_usable_source(monkeypatch):
    engine = _static_engine(["static-0.edf", "static-1.edf"])

    def read_image(path):
        if path.endswith("static-1.edf"):
            raise OSError("reader failed")
        return np.ones((2, 2)), {}

    monkeypatch.setattr(saxs_io, "read_image", read_image)
    definition = next(
        item
        for item in build_static_saxs_figure_definitions(engine)
        if item.figure_id == "saxs.static.detector.2d"
    )

    assert definition.recipe["parameters"]["detector_failures"] == {
        "1": "reader failed"
    }
    assert definition.recipe["parameters"]["detector_projection_quality"]["0"][
        "status"
    ] == "complete"


@pytest.mark.parametrize("mode", ["static", "temperature"])
def test_partial_detector_figure_reaches_ready_manifest_and_export(
    monkeypatch, mode, tmp_path
):
    if mode == "static":
        engine = _static_engine(["static-0.edf"])
        builder = build_static_saxs_figure_definitions
        figure_id = "saxs.static.detector.2d"
    else:
        engine = _temperature_engine(["temperature-0.edf"])
        builder = build_temperature_figure_definitions
        figure_id = "saxs.temperature.detector.2d"
    monkeypatch.setattr(
        saxs_io,
        "read_image",
        lambda _path: (
            np.asarray([[1.0, np.nan], [4.0, 16.0]], dtype=float),
            {},
        ),
    )

    definition = next(item for item in builder(engine) if item.figure_id == figure_id)
    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id=f"saxs-partial-{mode}",
        technique="saxs",
        definitions=(definition,),
    )

    entry = manifest.figures[0]
    assert entry.status == "ready"
    assert {"png", "svg"} <= set(entry.assets)
    document = tmp_path / "runs" / f"saxs-partial-{mode}" / entry.document
    persisted = json.loads(document.read_text(encoding="utf-8"))
    assert (
        persisted["recipe"]["parameters"]["detector_projection_quality"]["0"][
            "status"
        ]
        == "partial_nonfinite"
    )


@pytest.mark.parametrize("mode", ["static", "temperature"])
def test_partial_detector_figure_is_reactive_v2_ready_and_publishable(
    monkeypatch, mode, tmp_path
):
    if mode == "static":
        engine = _static_engine(["static-0.edf"])
        builder = build_static_saxs_figure_definitions
        figure_id = "saxs.static.detector.2d"
    else:
        engine = _temperature_engine(["temperature-0.edf"])
        builder = build_temperature_figure_definitions
        figure_id = "saxs.temperature.detector.2d"
    monkeypatch.setattr(
        saxs_io,
        "read_image",
        lambda _path: (
            np.asarray([[1.0, np.nan], [4.0, 16.0]], dtype=float),
            {},
        ),
    )

    definition = next(item for item in builder(engine) if item.figure_id == figure_id)
    run_id = f"saxs-partial-v2-{mode}"
    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id=run_id,
        technique="saxs",
        definitions=(definition,),
    )

    entry = manifest.figures[0]
    assert entry.status == "ready"
    assert entry.capability_report["v2_runtime"] == "ready"
    sidecar = (
        tmp_path
        / "runs"
        / run_id
        / entry.capability_report["v2_sidecar"]
    )
    assert sidecar.is_file()
    assert entry.publication_role == "diagnostic"
    service = ReactiveFigureProjectService(tmp_path)
    handle = service.load(run_id=run_id, figure_id=figure_id)
    node = handle.session.scene.node_by_id("detector-pattern-000")
    assert len(node.rectangles) == 3
    saved = service.save_working(handle)
    published = service.publish(
        handle,
        profile=PublicationProfile(dpi=100, formats=("png",)),
    )

    assert saved.working_revision == 1
    assert len(published.assets) == 1
    assert published.assets[0].is_file()
    assert published.assets[0].stat().st_size > 0
    persisted = json.loads((tmp_path / "runs" / run_id / entry.document).read_text("utf-8"))
    assert (
        persisted["recipe"]["parameters"]["detector_projection_quality"]["0"][
            "status"
        ]
        == "partial_nonfinite"
    )


@pytest.mark.parametrize("mode", ["static", "temperature"])
def test_all_invalid_detector_images_are_omitted(monkeypatch, mode):
    if mode == "static":
        engine = _static_engine(["static-0.edf"])
        builder = build_static_saxs_figure_definitions
    else:
        engine = _temperature_engine(["temperature-0.edf"])
        builder = build_temperature_figure_definitions
    monkeypatch.setattr(
        saxs_io,
        "read_image",
        lambda _path: (np.full((2, 2), np.nan), {}),
    )

    assert not any(
        item.figure_id.endswith("detector.2d") for item in builder(engine)
    )
