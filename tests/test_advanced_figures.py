from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from polynexus.core.advanced_figures import build_advanced_figure_definitions
from polynexus.core.canonical_experiments.models import Measurement
from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.figures.v2_capabilities import build_v2_definition_artifact


def _measurement(measurement_id: str = "bound") -> Measurement:
    return Measurement(
        measurement_id=measurement_id,
        family="diagnostic",
        role="response",
        channels={"x": (0.0, 1.0, 2.0), "intensity": (1.0, 2.0, 3.0)},
        units={"x": "s", "intensity": "Pa"},
        source_locator={
            "source_path": "synthetic.csv",
            "sheet_name": None,
            "sheet_index": 0,
            "table_index": 0,
            "header_row": 0,
            "data_row_start": 1,
            "data_row_end": 3,
            "point_start": 0,
            "point_end": 3,
        },
    )


def _engine(technique: str):
    measurement = _measurement()
    metrics = {
        "tga": {
            "kinetics": {
                "kissinger": {
                    "status": "computed_with_warning",
                    "method": "kissinger_linear_fit",
                    "peak_temperatures_K": (500.0, 510.0, 520.0),
                    "heating_rates": (5.0, 10.0, 20.0),
                    "activation_energy_J_mol": 100_000.0,
                    "intercept": 1.0,
                    "parameters": {"gas_constant": 8.31446261815324},
                },
                "source_measurement_ids": ("rate-5", "rate-10", "rate-20"),
                "isoconversional_ofw": {
                    "method": "ozawa_flynn_wall_linear_fit",
                    "source_measurement_ids": ("rate-5", "rate-10", "rate-20"),
                    "conversion_levels": {
                        "conversion_0.2": {
                            "status": "computed_with_warning",
                            "conversion": 0.2,
                            "activation_energy_J_mol": 90_000.0,
                        },
                        "conversion_0.5": {
                            "status": "computed_with_warning",
                            "conversion": 0.5,
                            "activation_energy_J_mol": 95_000.0,
                        },
                    },
                },
            }
        },
        "dma": {
            "dma_tts": {
                "status": "computed_with_warning",
                "method": "time_temperature_superposition",
                "shift_mode": "explicit",
                "shift_factors": (1.0, 10.0),
                "frequency_unit": "Hz",
                "modulus_unit": "Pa",
                "source_measurement_ids": ("dma-25", "dma-35"),
                "points": (
                    {"temperature": 25.0, "frequency": 1.0, "modulus": 10.0},
                    {"temperature": 25.0, "frequency": 2.0, "modulus": 20.0},
                    {"temperature": 35.0, "frequency": 10.0, "modulus": 12.0},
                    {"temperature": 35.0, "frequency": 20.0, "modulus": 22.0},
                ),
            }
        },
        "rheology": {
            "rheology_advanced": {
                "cox_merz": {
                    "status": "computed_with_warning",
                    "method": "cox_merz_pointwise_comparison",
                    "frequency": (1.0, 2.0),
                    "shear_rate": (1.0, 2.0),
                    "complex_viscosity_Pa_s": (10.0, 8.0),
                    "steady_viscosity_Pa_s": (9.0, 8.5),
                    "source_measurement_ids": ("dynamic", "steady"),
                },
                "tts": {
                    "status": "computed_with_warning",
                    "method": "time_temperature_superposition",
                    "source_measurement_ids": ("rheo-25", "rheo-35"),
                    "parameters": {"shift_factors": (1.0, 10.0)},
                    "points": (
                        {"temperature": 25.0, "frequency": 1.0, "value": 10.0},
                        {"temperature": 25.0, "frequency": 2.0, "value": 8.0},
                        {"temperature": 35.0, "frequency": 10.0, "value": 10.0},
                        {"temperature": 35.0, "frequency": 20.0, "value": 8.0},
                    ),
                },
                "thixotropy": {
                    "status": "computed_with_warning",
                    "method": "thixotropy_time_integral",
                    "source_measurement_ids": ("bound",),
                },
                "creep": {
                    "status": "computed_with_warning",
                    "method": "creep_linear_time_fit",
                    "source_measurement_ids": ("bound",),
                },
                "relaxation": {"status": "unavailable", "unavailable_reason": "series_missing"},
            }
        },
        "mechanics": {
            "mechanics_advanced": {
                "cycles": {
                    "status": "computed_with_warning",
                    "method": "cycle_peak_envelope",
                    "cycle_ids": (1.0, 2.0),
                    "peak_response": (10.0, 9.0),
                    "source_measurement_ids": ("bound",),
                },
                "fatigue": {
                    "status": "computed_with_warning",
                    "method": "fatigue_response_history",
                    "cycle_count": (1.0, 2.0),
                    "response": (10.0, 8.0),
                    "source_measurement_ids": ("bound",),
                },
                "creep": {
                    "status": "computed_with_warning",
                    "method": "creep_time_integral",
                    "source_measurement_ids": ("bound",),
                },
                "fracture": {
                    "status": "computed_with_warning",
                    "method": "fracture_energy_integral",
                    "source_measurement_ids": ("bound",),
                },
            }
        },
    }[technique]
    measurements = (measurement,) if technique in {"rheology", "mechanics"} else ()
    return SimpleNamespace(name=technique, _metrics=metrics, _measurements=measurements)


@pytest.mark.parametrize("technique", ("tga", "dma", "rheology", "mechanics"))
def test_advanced_figures_validate_and_adapt_to_shared_v2(technique: str) -> None:
    definitions = build_advanced_figure_definitions(_engine(technique))

    assert definitions
    assert all(definition.technique == technique for definition in definitions)
    assert all(definition.category == "diagnostic" for definition in definitions)
    assert all(definition.publication_role == "diagnostic" for definition in definitions)
    assert all(definition.recipe["parameters"]["source_measurement_ids"] for definition in definitions)
    assert all(definition.recipe["parameters"]["method"] for definition in definitions)
    assert [definition.recipe["parameters"]["display_order"] for definition in definitions] == [
        definition.display_order for definition in definitions
    ]
    for definition in definitions:
        validate_figure_definition(definition)
        artifact = build_v2_definition_artifact(definition)
        assert artifact.capability["v2_runtime"] == "ready"
        assert artifact.sidecar is not None


def test_unavailable_advanced_result_does_not_create_figure() -> None:
    engine = _engine("mechanics")
    engine._metrics["mechanics_advanced"] = {
        "cycles": {"status": "unavailable", "unavailable_reason": "cycle_series_missing"},
        "fatigue": {"status": "unavailable", "unavailable_reason": "fatigue_series_missing"},
        "creep": {"status": "unavailable", "unavailable_reason": "creep_series_missing"},
        "fracture": {"status": "unavailable", "unavailable_reason": "fracture_series_missing"},
    }

    assert build_advanced_figure_definitions(engine) == ()


def test_advanced_figure_exports_shared_assets_data_and_v2_sidecar(tmp_path: Path) -> None:
    definition = build_advanced_figure_definitions(_engine("tga"))[0]

    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="advanced-figure-proof",
        technique="tga",
        definitions=(definition,),
        profile_id="paper_complete",
    )

    entry = manifest.figures[0]
    assert entry.status == "ready"
    assert entry.display_order == definition.display_order
    assert set(entry.assets) == {"preview", "svg", "png", "pdf"}
    run_root = tmp_path / "runs" / manifest.run_id
    assert all((run_root / relative).is_file() for relative in entry.assets.values())
    assert all((run_root / relative).is_file() for relative in entry.data_sources)
    assert (run_root / entry.capability_report["v2_sidecar"]).is_file()
    assert entry.capability_report["v2_runtime"] == "ready"
