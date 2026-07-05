"""Tests for PolyNexus core engine."""

import pytest
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
