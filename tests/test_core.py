"""Tests for PolyNexus core engine."""

import pytest
from pathlib import Path
from polynexus.core.engine import BaseEngine, register_technique, get_engine, list_techniques


# Register a test engine
@register_technique("test_tech")
class TestEngine(BaseEngine):
    name = "test_tech"
    label = "Test"

    def load(self, filepath): return True
    def preprocess(self): return True
    def analyze(self): return True
    def get_parameters(self): return {"test": 42}
    def plot(self, output_dir=""): return {}


def test_register_and_get():
    engine = get_engine("test_tech")
    assert engine is not None
    assert engine.label == "Test"


def test_list_techniques():
    techs = list_techniques()
    names = [t['name'] for t in techs]
    assert 'test_tech' in names


def test_run_pipeline():
    engine = get_engine("test_tech")
    result = engine.run_pipeline("dummy.txt")
    assert result.parameters == {"test": 42}


def test_core_engine_wrappers_do_not_hide_logger_after_return():
    root = Path(__file__).resolve().parents[1]
    targets = [
        root / "polynexus" / "core" / name
        for name in ("dsc.py", "ir.py", "nmr.py", "waxs.py")
    ]

    for path in targets:
        text = path.read_text(encoding="utf-8")
        assert "return False\n            logger.warning" not in text


def test_public_engine_labels_do_not_contain_mojibake():
    bad_tokens = ("閳", "棣", "鈥", "�")
    for item in list_techniques():
        public_text = " ".join(
            str(item.get(key, ""))
            for key in ("name", "label", "description", "icon")
        )
        assert not any(token in public_text for token in bad_tokens)
