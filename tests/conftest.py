"""Test bootstrap helpers for PySide6 import stability."""

from dataclasses import replace

# Preload the scientific stack before any test imports PySide6.
# On this environment, collecting Qt-heavy tests first can leave shiboken's
# import hook active while lmfit/dill later resolve `_thread` via six.moves.
# Importing the fit stack up front keeps the mixed GUI/core pytest runs stable.
import dill  # noqa: F401
import lmfit  # noqa: F401
import matplotlib.pyplot  # noqa: F401
import numpy  # noqa: F401
import pandas  # noqa: F401
import pytest
import six.moves._thread  # noqa: F401

from polynexus.core.figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)


@pytest.fixture
def ir_definition():
    return FigureDefinition(
        figure_id="ir.frame.spectrum.001",
        technique="ir",
        scope="frame",
        category="per_frame",
        title="IR Spectrum",
        layout=FigureLayoutDefinition(
            width_in=2.0,
            height_in=1.0,
            rows=1,
            columns=1,
            panels=(
                PanelDefinition(
                    panel_id="main",
                    row=0,
                    column=0,
                    x_axis=AxisDefinition(
                        axis_id="x",
                        label="Wavenumber",
                        unit="cm^-1",
                        reversed=True,
                    ),
                    y_axis=AxisDefinition(
                        axis_id="y",
                        label="Absorbance",
                        unit="a.u.",
                    ),
                ),
            ),
        ),
        data_sources=(
            FigureDataSourceDefinition(
                source_id="spectrum-data",
                columns=(
                    DataColumnDefinition("wavenumber_cm1", "cm^-1"),
                    DataColumnDefinition("absorbance", "a.u."),
                ),
                values={
                    "wavenumber_cm1": (1800.0, 1700.0),
                    "absorbance": (0.1, 0.4),
                },
            ),
        ),
        objects=(
            {
                "id": "series-spectrum",
                "type": "plot_series",
                "panel_id": "main",
                "data_ref": "spectrum-data",
                "x_column": "wavenumber_cm1",
                "y_column": "absorbance",
                "style": {"color": "#222222", "line_width": 0.8},
            },
        ),
        recipe={
            "module": "tests.conftest",
            "function": "ir_definition",
            "inputs": {"result_label": "sample"},
            "parameters": {},
        },
        style_profile="sci_default",
    )


@pytest.fixture
def invalid_ir_definition(ir_definition):
    return replace(
        ir_definition,
        objects=(
            {
                **ir_definition.objects[0],
                "panel_id": "missing-panel",
            },
        ),
    )


@pytest.fixture
def built_ir_document(ir_definition, tmp_path):
    from polynexus.core.figures.data_writer import FigureDataSnapshotWriter
    from polynexus.core.figures.document_builder import FigureDocumentBuilder

    run_root = tmp_path / "runs" / "run-1"
    figure_dir = run_root / "figures" / ir_definition.figure_id
    records = FigureDataSnapshotWriter(run_root).write(ir_definition, figure_dir)
    document_path, document = FigureDocumentBuilder().write(
        definition=ir_definition,
        run_id="run-1",
        revision=1,
        figure_dir=figure_dir,
        data_sources=records,
    )
    return run_root, document_path, document


@pytest.fixture
def render_plan(built_ir_document):
    from polynexus.core.figures.render_plan import FigureRenderPlanBuilder

    run_root, document_path, document = built_ir_document
    return FigureRenderPlanBuilder(run_root).build(document_path, document)


@pytest.fixture
def complete_inspection():
    from polynexus.core.figures.inspector import FigureArtifactInspection

    return FigureArtifactInspection(
        complete=True,
        errors=(),
        warnings=(),
        dimensions={
            "preview": (300, 150, 150),
            "svg": (192, 96, 96),
            "png": (1200, 600, 600),
            "pdf": (144, 72, 72),
        },
        png_dpi=600,
    )


@pytest.fixture
def three_format_paths(tmp_path):
    from matplotlib.figure import Figure

    paths = {
        "png": tmp_path / "figure.png",
        "svg": tmp_path / "figure.svg",
        "pdf": tmp_path / "figure.pdf",
    }
    for file_format, path in paths.items():
        dpi = 600 if file_format == "png" else 72
        figure = Figure(figsize=(2.0, 1.0), dpi=dpi)
        axis = figure.add_subplot(111)
        axis.plot([0.0, 1.0], [0.0, 1.0])
        figure.savefig(path, format=file_format, dpi=dpi)
    return paths
