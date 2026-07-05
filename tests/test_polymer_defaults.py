import json
from pathlib import Path

from polynexus.utils import (
    delete_config_preset,
    detect_polymer_type,
    list_config_presets,
    load_config_preset,
    load_defaults,
    save_config_preset,
)


def test_detect_polymer_type_prefers_longer_matches():
    assert detect_polymer_type("PA66_batch01") == "PA66"
    assert detect_polymer_type("PEEK_film_02") == "PEEK"
    assert detect_polymer_type("sample_003") == "unknown"


def test_load_defaults_returns_polymer_profiles():
    defaults = load_defaults("PEEK")
    assert defaults["dsc"]["standard_enthalpy"] == 130.0
    assert defaults["nmr"]["lb_hz"] == 5.0


def test_load_defaults_falls_back_to_unknown_profile():
    assert load_defaults("random_sample") == load_defaults("unknown")


def test_defaults_json_contains_required_polymer_profiles():
    path = Path(__file__).resolve().parents[1] / "config" / "defaults.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    profiles = data["polymers"]
    for polymer in ["PA6", "PA66", "PE", "PP", "PET", "PEK", "PEEK", "PLA", "PVDF", "unknown"]:
        assert polymer in profiles
        assert "dsc" in profiles[polymer]
        assert "nmr" in profiles[polymer]


def test_config_presets_round_trip_in_user_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    save_config_preset(
        "saxs",
        "saxs.static",
        "Lab Default",
        {"baseline_method": "normalize", "smooth_window": 9},
    )
    save_config_preset(
        "saxs",
        "saxs.static",
        "Fast Scan",
        {"baseline_method": "subtract", "smooth_window": 5},
    )

    assert list_config_presets("saxs", "saxs.static") == ["Fast Scan", "Lab Default"]
    assert load_config_preset("saxs", "saxs.static", "Lab Default") == {
        "baseline_method": "normalize",
        "smooth_window": 9,
    }

    assert delete_config_preset("saxs", "saxs.static", "Fast Scan") is True
    assert list_config_presets("saxs", "saxs.static") == ["Lab Default"]
    assert delete_config_preset("saxs", "saxs.static", "Missing") is False
