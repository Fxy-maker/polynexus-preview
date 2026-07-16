import numpy as np
import pytest
from types import SimpleNamespace

from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.figures.v2_capabilities import build_v2_definition_artifact
from polynexus.core.waxs import WAXSEngine
from polynexus.core.waxs_engine.core import WAXSResult
from polynexus.core.waxs_engine.figure_provider import build_waxs_figure_definitions


@pytest.fixture
def waxs_results():
    two_theta = np.array([10.0, 15.0, 20.0, 25.0, 30.0])
    return (
        WAXSResult(
            label="waxs-a",
            two_theta=two_theta,
            I=np.array([10.0, 24.0, 18.0, 8.0, 5.0]),
            I_fit=np.array([9.5, 23.0, 17.5, 8.5, 5.2]),
            I_amorphous=np.array([6.0, 8.0, 7.0, 5.0, 3.0]),
            I_crystalline=np.array([4.0, 16.0, 11.0, 3.0, 2.0]),
            peaks=[
                {
                    "two_theta": 15.0,
                    "height": 24.0,
                    "prominence": 12.0,
                    "hkl": "110",
                }
            ],
            Xc_pct=42.0,
            r_squared=0.95,
            size_reliability_status="reliable",
        ),
        WAXSResult(
            label="waxs-b",
            two_theta=two_theta,
            I=np.array([8.0, 19.0, 15.0, 7.0]),
            Xc_pct=35.0,
            r_squared=0.95,
            size_reliability_status="reliable",
        ),
    )


def test_waxs_provider_emits_profile_decomposition_and_overview(waxs_results):
    engine = SimpleNamespace(active_submodule="waxs.static", _results=waxs_results)
    definitions = build_waxs_figure_definitions(engine)

    assert {item.figure_id for item in definitions} >= {
        "waxs.static.profile",
    }
    assert definitions[0].publication_role == "main"

    for definition in definitions:
        validate_figure_definition(definition)
        assert definition.recipe["v2_adapter"] == "waxs"
    assert (
        build_v2_definition_artifact(definitions[0]).capability["v2_runtime"]
        == "ready"
    )


def test_waxs_engine_exposes_complete_definitions(waxs_results):
    engine = WAXSEngine()
    engine._results = list(waxs_results)
    engine.active_submodule = "waxs.static"

    definitions = engine.build_figure_definitions()

    assert {item.figure_id for item in definitions} >= {
        "waxs.static.profile",
    }
