from polynexus.core.figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)
from polynexus.core.figures.profiles import get_figure_output_profile


def test_paper_complete_profile_has_fixed_roles():
    profile = get_figure_output_profile("paper_complete")

    assert profile.profile_id == "paper_complete"
    assert profile.preview_filename == "preview.png"
    assert profile.formal_assets == {
        "svg": "figure.svg",
        "png": "figure.png",
        "pdf": "figure.pdf",
    }
    assert profile.preview_dpi == 150
    assert profile.publication_png_dpi == 600


def test_figure_definition_serializes_stable_layout_and_data_contract():
    source = FigureDataSourceDefinition(
        source_id="spectrum-data",
        columns=(
            DataColumnDefinition("wavenumber_cm1", "cm^-1"),
            DataColumnDefinition("absorbance", "a.u."),
        ),
        values={
            "wavenumber_cm1": (1800.0, 1700.0),
            "absorbance": (0.1, 0.4),
        },
    )
    definition = FigureDefinition(
        figure_id="ir.frame.spectrum.001",
        technique="ir",
        scope="frame",
        category="per_frame",
        title="IR Spectrum",
        layout=FigureLayoutDefinition(
            width_in=7.5,
            height_in=3.8,
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
        data_sources=(source,),
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
            "module": "polynexus.core.ir_engine.figure_provider",
            "function": "build_ir_spectrum_definitions",
            "inputs": {"result_label": "sample"},
            "parameters": {},
        },
        style_profile="sci_default",
    )

    payload = definition.to_payload()

    assert payload["figure_id"] == "ir.frame.spectrum.001"
    assert payload["layout"]["panels"][0]["x_axis"]["reversed"] is True
    assert payload["data_sources"][0]["columns"][0]["unit"] == "cm^-1"
