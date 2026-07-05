from __future__ import annotations

from rag.polymer_knowledge import format_polymer_knowledge, load_polymer_knowledge, load_required_polymer_knowledge


def test_load_pa6_knowledge_has_waxs_reference_fields() -> None:
    knowledge = load_polymer_knowledge("PA6")

    assert knowledge["name"] == "PA6"
    assert knowledge["waxs"]["xc_range"] == [35, 55]
    assert knowledge["waxs"]["characteristic_peaks"]
    assert "ir" in knowledge
    assert knowledge["ir"]["key_bands"]


def test_load_required_polymer_knowledge_has_ir_reference_fields() -> None:
    items = load_required_polymer_knowledge()

    assert len(items) == 8
    for item in items:
        ir = item.get("ir", {})
        assert ir, f"missing ir reference for {item.get('name')}"
        assert ir.get("characteristic_bands")
        assert ir.get("key_bands")
        assert ir.get("assignment_notes")


def test_all_required_polymer_json_share_waxs_and_dsc_schema() -> None:
    items = load_required_polymer_knowledge()

    assert len(items) == 8
    for item in items:
        waxs = item["waxs"]
        assert "xc_range" in waxs
        assert "xc_typical" in waxs
        assert "characteristic_peaks" in waxs
        assert isinstance(waxs["characteristic_peaks"], list)
        assert "dsc" in item
        assert "xc_range" in item["dsc"]
        assert "delta_hm_100" in item["dsc"]


def test_rag_polymer_lookup_returns_pa6_peak_information() -> None:
    knowledge = load_polymer_knowledge("PA6")
    peaks = [peak["two_theta"] for peak in knowledge["waxs"]["characteristic_peaks"]]
    reference = format_polymer_knowledge(knowledge, {"Xc_pct": 18.7})

    assert 20.2 in peaks
    assert 23.7 in peaks
    assert "35-55%" in reference
    assert "明显偏低" in reference


def test_ir_polymer_reference_formats_key_and_secondary_bands() -> None:
    knowledge = load_polymer_knowledge("PA6")
    reference = format_polymer_knowledge(knowledge, {"Xc_pct": 18.7}, technique="IR")

    assert "强特征带" in reference
    assert "辅助带" in reference
    assert "重叠风险" in reference
    assert "归属提示" in reference


def test_dsc_polymer_reference_formats_tm_and_enthalpy() -> None:
    knowledge = load_polymer_knowledge("PA6")
    reference = format_polymer_knowledge(knowledge, {"Xc_pct": 18.7}, technique="DSC")

    assert "Tm≈220°C" in reference
    assert "ΔHm0=230 J/g" in reference
    assert "25-50%" in reference
