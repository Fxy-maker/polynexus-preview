from __future__ import annotations

import pytest

from polynexus.core.figure_export_preset_service import (
    list_export_presets,
    load_export_preset,
    save_export_preset,
    validate_export_preset,
)


def test_export_preset_round_trips_named_formats(tmp_path, monkeypatch):
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "config"))

    path = save_export_preset(
        "publication",
        {"formats": ["png", "svg", "project"], "dpi": 300},
    )

    assert path.exists()
    assert list_export_presets() == ["publication"]
    assert load_export_preset("publication")["dpi"] == 300


def test_export_preset_validation_rejects_unknown_formats_and_overwrite_requires_choice():
    with pytest.raises(ValueError, match="unsupported"):
        validate_export_preset({"formats": ["jpeg2000"]})

    assert validate_export_preset({"formats": ["png"]})["formats"] == ["png"]
