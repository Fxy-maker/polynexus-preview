from __future__ import annotations

import numpy as np

from polynexus.core.saxs_sequence_qa import build_sequence_qa_summary


def test_sequence_qa_handles_numpy_conditions_dirty_values_and_zero_keys() -> None:
    summary = build_sequence_qa_summary(
        discovered_files=["a.edf", "b.edf"], loaded_files=["a.edf", "b.edf"],
        skipped_files=[], conditions=np.asarray([0.0, "N/A"], dtype=object),
        condition_keys=[0, "unresolved::b.edf"], condition_sources=[0, "unresolved"],
        condition_source_keys=["temperature"] * 2, condition_source_texts=["0C", "N/A"],
        condition_confidences=[0.0, "n/a"], geometry_sources=["header"] * 2,
        geometry_confidences=[0.9, 0.8],
    )

    axis = summary["condition_axis"]
    assert [entry["value"] for entry in axis["entries"]] == [0.0, None]
    assert [entry["key"] for entry in axis["entries"]] == ["0", "unresolved::b.edf"]
    assert axis["unresolved_count"] == 1
    assert axis["duplicate_count"] == 0


def test_sequence_qa_aligns_unresolved_and_missing_counts_to_longest_axis() -> None:
    summary = build_sequence_qa_summary(
        discovered_files=["a.edf", "b.edf"], loaded_files=["a.edf", "b.edf"],
        skipped_files=[], conditions=[1.0],
        condition_keys=["temperature::1", "unresolved::b.edf"],
        condition_sources=["header", "unresolved"],
        condition_source_keys=["temperature"] * 2, condition_source_texts=["1C", "N/A"],
        condition_confidences=[0.9, None], geometry_sources=["config_default"] * 2,
        geometry_confidences=[0.4, 0.4],
    )

    axis = summary["condition_axis"]
    assert len(axis["entries"]) == 2
    assert axis["entries"][1]["value"] is None
    assert axis["unresolved_count"] == 1
    assert axis["missing_count"] == 1


def test_sequence_qa_preserves_geometry_confidence_and_unknown_sources() -> None:
    summary = build_sequence_qa_summary(
        discovered_files=["a.edf", "b.edf", "c.edf"],
        loaded_files=["a.edf", "b.edf", "c.edf"], skipped_files=[],
        conditions=[1.0, 2.0, 3.0],
        condition_keys=["temperature::1", "temperature::2", "temperature::3"],
        condition_sources=["header"] * 3, condition_source_keys=["temperature"] * 3,
        condition_source_texts=["1C", "2C", "3C"], condition_confidences=[0.9] * 3,
        geometry_sources=["header", "metadata_file", ""],
        geometry_confidences=[0.9, "n/a", None, 0.4],
    )

    geometry = summary["geometry"]
    assert geometry["status"] == "mixed"
    assert geometry["unrecognized_frame_count"] == 2
    assert geometry["confidence"] == [0.9, None, None, 0.4]
