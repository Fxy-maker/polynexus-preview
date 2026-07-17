from __future__ import annotations

from pathlib import Path

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.io import recover_condition_axis, scan_experiment_dir


def test_recover_condition_axis_uses_edf_header_temperature() -> None:
    path = Path(r"D:\PolyNexus\测试数据\saxs\无定形单个样品变温\Check-20260618_0_00002.edf")
    cfg = SAXSConfig(experiment_type="temperature", condition_label="Temperature", condition_unit="C")

    recovered = recover_condition_axis(path, cfg, header={"temperature": "-20"})

    assert recovered["source"] == "header"
    assert recovered["confidence"] == 0.9
    assert recovered["condition_key"] == -20.0
    assert recovered["value"] == -20.0
    assert "Temperature" in recovered["label"]


def test_scan_experiment_dir_keeps_unresolved_entries_separate(tmp_path) -> None:
    root = tmp_path / "series"
    root.mkdir()

    sample_a = root / "frame_a.edf"
    sample_b = root / "frame_b.edf"
    sample_a.write_text("dummy", encoding="utf-8")
    sample_b.write_text("dummy", encoding="utf-8")

    cfg = SAXSConfig(experiment_type="temperature", condition_label="Temperature", condition_unit="C")

    # Force the unresolved branch by using non-EDF-like inputs with the .edf suffix.
    # scan_experiment_dir will try to read them and fall back to unresolved keys.
    conditions = scan_experiment_dir(str(root), cfg)

    assert len(conditions) == 2
    assert all(np.isnan(cond.value) for cond in conditions)
    assert len({cond.condition_key for cond in conditions}) == 2


def test_recover_condition_axis_distinguishes_directory_and_filename_sources(tmp_path) -> None:
    root = tmp_path / "temperature_180"
    root.mkdir()
    path = root / "sample_001.edf"
    path.write_text("dummy", encoding="utf-8")

    cfg = SAXSConfig(experiment_type="temperature", condition_label="Temperature", condition_unit="C")
    recovered = recover_condition_axis(path, cfg)

    assert recovered["source"] == "path_directory"
    assert recovered["source_key"] == "temp_directory_label"
    assert recovered["confidence"] >= 0.7
    assert recovered["value"] == 180.0


def test_scan_experiment_dir_preserves_condition_confidence_metadata(tmp_path) -> None:
    root = tmp_path / "temperature_180"
    root.mkdir()
    sample = root / "sample_001.edf"
    sample.write_text("dummy", encoding="utf-8")

    cfg = SAXSConfig(experiment_type="temperature", condition_label="Temperature", condition_unit="C")
    conditions = scan_experiment_dir(str(root), cfg)

    assert len(conditions) == 1
    metadata = conditions[0].metadata or {}
    assert metadata["condition_source"] == "path_directory"
    assert metadata["condition_source_key"] == "temp_directory_label"
    assert metadata["condition_confidence"] >= 0.7


def test_scan_experiment_dir_ignores_generated_output_tree(tmp_path) -> None:
    root = tmp_path / "temperature_series"
    root.mkdir()
    raw = root / "PA6-250-170-S_0_00000.edf"
    raw.write_text("dummy", encoding="utf-8")
    generated = (
        root
        / "polynexus_output"
        / "runs"
        / "saxs-old"
        / "figures"
        / "saxs.temperature.waterfall"
        / "assets"
        / "figure.tiff"
    )
    generated.parent.mkdir(parents=True)
    generated.write_bytes(b"generated figure asset")

    cfg = SAXSConfig(
        experiment_type="temperature",
        condition_label="Temperature",
        condition_unit="C",
    )
    conditions = scan_experiment_dir(str(root), cfg)
    discovered = [path for condition in conditions for path in condition.files]

    assert [Path(path).resolve() for path in discovered] == [raw.resolve()]
