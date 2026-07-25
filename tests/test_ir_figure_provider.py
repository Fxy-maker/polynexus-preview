import numpy as np
from dataclasses import replace

from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.ir_engine.core import IRResult
from polynexus.core.ir_engine.figure_provider import build_ir_spectrum_definitions


def test_ir_provider_builds_stable_spectrum_definition():
    result = IRResult(
        label="sample-ir",
        wavenumber=np.array([1800.0, 1700.0, 1600.0]),
        absorbance=np.array([0.1, 0.4, 0.2]),
        peaks=[
            {
                "wavenumber": 1700.0,
                "height": 0.4,
                "prominence": 0.3,
                "assignment": "amide I",
            }
        ],
    )

    definitions = build_ir_spectrum_definitions((result,))

    assert len(definitions) == 1
    definition = definitions[0]
    assert definition.figure_id == "ir.frame.spectrum.001"
    assert definition.category == "per_frame"
    assert definition.layout.panels[0].x_axis.reversed is True
    assert definition.objects[0]["type"] == "plot_series"
    assert {item["type"] for item in definition.objects} == {
        "plot_series",
        "line",
        "text",
    }


def test_ir_provider_skips_empty_frames_and_caps_peak_annotations():
    peaks = [
        {
            "wavenumber": 1800.0 - index,
            "height": 0.1 + index / 100.0,
            "prominence": float(index),
        }
        for index in range(20)
    ]
    definitions = build_ir_spectrum_definitions(
        (
            IRResult(label="empty"),
            IRResult(
                label="populated",
                wavenumber=np.array([1800.0, 1700.0, 1600.0]),
                absorbance=np.array([0.1, 0.4, 0.2]),
                peaks=peaks,
            ),
        )
    )

    assert len(definitions) == 1
    assert definitions[0].figure_id == "ir.frame.spectrum.002"
    assert sum(item["type"] == "line" for item in definitions[0].objects) == 16
    assert sum(item["type"] == "text" for item in definitions[0].objects) == 16


def test_ir_spectrum_vertical_slice_produces_complete_manifest(tmp_path):
    result = IRResult(
        label="sample-ir",
        wavenumber=np.array([1800.0, 1700.0, 1600.0]),
        absorbance=np.array([0.1, 0.4, 0.2]),
    )

    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="ir-run-1",
        technique="ir",
        definitions=build_ir_spectrum_definitions((result,)),
        profile_id="paper_complete",
    )

    entry = manifest.figures[0]
    assert entry.status == "ready"
    assert entry.capability_report["editing_mode"] == "object"
    assert set(entry.assets) == {"preview", "svg", "png", "pdf"}


def test_ir_pipeline_keeps_ready_siblings_when_one_definition_fails(tmp_path):
    definition = build_ir_spectrum_definitions(
        (
            IRResult(
                label="sample-ir",
                wavenumber=np.array([1800.0, 1700.0, 1600.0]),
                absorbance=np.array([0.1, 0.4, 0.2]),
            ),
        )
    )[0]
    broken = replace(
        definition,
        figure_id="ir.frame.broken",
        objects=(
            {
                "id": "broken-series",
                "type": "plot_series",
                "panel_id": "main",
                "data_ref": "missing-source",
                "x_column": "wavenumber_cm1",
                "y_column": "absorbance",
            },
        ),
    )
    valid = replace(definition, figure_id="ir.frame.valid")

    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="ir-failure-sibling-1",
        technique="ir",
        definitions=(broken, valid),
        profile_id="paper_complete",
    )

    assert [(item.figure_id, item.status) for item in manifest.figures] == [
        ("ir.frame.broken", "generation_failed"),
        ("ir.frame.valid", "ready"),
    ]
    assert "unknown data_ref" in manifest.figures[0].error
