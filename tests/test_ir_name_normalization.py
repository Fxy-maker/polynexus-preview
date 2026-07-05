from __future__ import annotations

from polynexus.core.ir_engine.names import normalize_ir_polymer_database, normalize_ir_polymer_name


def test_normalize_ir_polymer_name_unifies_common_aliases() -> None:
    assert normalize_ir_polymer_name("iPP") == "PP"
    assert normalize_ir_polymer_name("polypropylene") == "PP"
    assert normalize_ir_polymer_name("PA66") == "PA66"
    assert normalize_ir_polymer_name("polyether ether ketone") == "PEEK"


def test_normalize_ir_polymer_database_canonicalizes_keys() -> None:
    normalized = normalize_ir_polymer_database({"iPP": [(998.0, "a", "m", True)], "PA66": []})

    assert "PP" in normalized
    assert "iPP" not in normalized
    assert normalized["PP"][0][0] == 998.0
