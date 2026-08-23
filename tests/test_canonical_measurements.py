from __future__ import annotations

import json
from pathlib import Path

import pytest

from polynexus.core.canonical_experiments import (
    CAPABILITY_ITEM_STATUSES,
    MAPPING_SOURCES,
    CapabilityItemResult,
    MappingProposal,
    MappingSelection,
    Measurement,
)


def _source_locator() -> dict[str, object]:
    return {
        "source_path": Path("raw/spectrum.csv"),
        "sheet_name": None,
        "sheet_index": None,
        "table_index": 0,
        "header_row": 1,
        "data_row_start": 2,
        "data_row_end": 4,
        "point_start": 0,
        "point_end": 2,
    }


def _selection(*, source: str = "observed") -> MappingSelection:
    return MappingSelection(
        measurement_id="measurement-1",
        sheet_name=None,
        sheet_index=None,
        table_index=0,
        header_row=1,
        data_row_start=2,
        data_row_end=4,
        x_column="Wavenumber",
        intensity_column="Absorbance",
        x_kind="wavenumber",
        x_unit="cm^-1",
        intensity_unit="a.u.",
        source=source,
    )


def test_measurement_is_immutable_ordered_and_json_safe() -> None:
    measurement = Measurement(
        measurement_id="measurement-1",
        family="spectrum_1d",
        role="primary",
        channels={"x": (4000.0, 2000.0, 500.0), "intensity": (0.1, 0.2, 0.3)},
        units={"x": "cm^-1", "intensity": "a.u."},
        source_locator=_source_locator(),
        acquisition_metadata={"operator": "A", "scan_count": 3},
    )

    assert measurement.channels["x"] == (4000.0, 2000.0, 500.0)
    assert json.loads(json.dumps(measurement.to_dict()))["source_locator"]["source_path"] == str(Path("raw/spectrum.csv"))
    with pytest.raises(TypeError):
        measurement.channels["x"] = (1.0, 2.0)
    with pytest.raises(TypeError):
        measurement.source_locator["source_path"] = "other.csv"
    with pytest.raises(ValueError, match="non-finite"):
        Measurement(
            measurement_id="nan",
            family="spectrum_1d",
            role="primary",
            channels={"x": (1.0, float("nan")), "intensity": (0.1, 0.2)},
            units={"x": "cm^-1", "intensity": "a.u."},
            source_locator=_source_locator(),
        )


def test_mapping_selection_and_proposal_preserve_allowed_sources() -> None:
    assert MAPPING_SOURCES == frozenset({"observed", "user", "AI proposal", "default"})
    with pytest.raises(ValueError, match="mapping source"):
        _selection(source="spectrum.csv")

    proposal = MappingProposal.create(
        source_artifact_id="raw-sha256",
        technique="IR",
        source="AI proposal",
        selections=(_selection(source="AI proposal"),),
        alternatives=(_selection(source="observed"),),
    )

    assert proposal.selections[0].source == "AI proposal"
    assert proposal.alternatives[0].source == "observed"
    assert json.loads(json.dumps(proposal.to_dict()))["proposal_id"] == proposal.proposal_id
    with pytest.raises(AttributeError):
        proposal.selections[0].source = "user"


@pytest.mark.parametrize("status", sorted(CAPABILITY_ITEM_STATUSES))
def test_capability_item_result_allows_payloads_only_when_completed(status: str) -> None:
    kwargs = {
        "item_id": "item-1",
        "measurement_id": "measurement-1",
        "capability_id": "peak-analysis",
        "status": status,
    }
    if status == "completed":
        result = CapabilityItemResult(
            **kwargs,
            result={"peak_count": 3},
            figures={"plot": "figures/peaks.svg"},
            reason_codes=("validated",),
        )
        assert result.to_dict()["figures"] == {"plot": "figures/peaks.svg"}
        with pytest.raises(ValueError, match="string"):
            CapabilityItemResult(**kwargs, figures={"plot": 3})
    else:
        assert CapabilityItemResult(**kwargs).result == {}
        with pytest.raises(ValueError, match="completed"):
            CapabilityItemResult(**kwargs, result={"peak_count": 3})
        with pytest.raises(ValueError, match="completed"):
            CapabilityItemResult(**kwargs, figures={"plot": "figures/peaks.svg"})
