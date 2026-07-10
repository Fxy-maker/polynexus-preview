import numpy as np
import pytest

from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.waxs import WAXSEngine
from polynexus.core.waxs_engine.core import WAXSResult
from polynexus.core.waxs_engine.figure_provider import build_waxs_figure_definitions


@pytest.fixture
def waxs_results():
    two_theta = np.array([10.0, 15.0, 20.0, 25.0])
    return (
        WAXSResult(
            label="waxs-a",
            two_theta=two_theta,
            I=np.array([10.0, 24.0, 18.0, 8.0]),
            I_fit=np.array([9.5, 23.0, 17.5, 8.5]),
            I_amorphous=np.array([6.0, 8.0, 7.0, 5.0]),
            I_crystalline=np.array([4.0, 16.0, 11.0, 3.0]),
            peaks=[
                {
                    "two_theta": 15.0,
                    "height": 24.0,
                    "prominence": 12.0,
                    "hkl": "110",
                }
            ],
            Xc_pct=42.0,
        ),
        WAXSResult(
            label="waxs-b",
            two_theta=two_theta,
            I=np.array([8.0, 19.0, 15.0, 7.0]),
            Xc_pct=35.0,
        ),
    )


def test_waxs_provider_emits_profile_decomposition_and_overview(waxs_results):
    definitions = build_waxs_figure_definitions(waxs_results)

    assert [item.figure_id for item in definitions] == [
        "waxs.frame.profile.001",
        "waxs.frame.decomposition.001",
        "waxs.frame.profile.002",
        "waxs.series.crystallinity",
    ]
    assert definitions[0].layout.rows == 2
    assert {obj["panel_id"] for obj in definitions[0].objects} == {
        "profile",
        "residual",
    }
    assert definitions[1].layout.panels[0].show_legend is True
    assert definitions[-1].objects[0]["chart_kind"] == "bar"

    for definition in definitions:
        validate_figure_definition(definition)


def test_waxs_engine_exposes_complete_definitions(waxs_results):
    engine = WAXSEngine()
    engine._results = list(waxs_results)

    definitions = engine.build_figure_definitions()

    assert {item.figure_id for item in definitions} >= {
        "waxs.frame.profile.001",
        "waxs.series.crystallinity",
    }
