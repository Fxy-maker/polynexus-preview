"""Tests for PolyNexus core engine."""

import re
from pathlib import Path

from polynexus.core.engine import BaseEngine, get_engine, list_techniques, register_technique


@register_technique("test_tech")
class DummyEngine(BaseEngine):
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
    names = [t["name"] for t in techs]
    assert "test_tech" in names


def test_run_pipeline():
    engine = get_engine("test_tech")
    result = engine.run_pipeline("dummy.txt")
    assert result.parameters == {"test": 42}


def test_no_unreachable_logger_after_return():
    root = Path(__file__).resolve().parents[1] / "polynexus"
    pattern = re.compile(r"return[^\n]*\n\s*logger\.(?:warning|error)\(", re.MULTILINE)
    offenders = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            offenders.append(str(path.relative_to(root.parent)))

    assert offenders == []


def test_public_text_and_logs_do_not_contain_mojibake():
    bad_tokens = (
        "\u95c8\u6b13\u7cbf",
        "\u5bee\u50a4\u7236",
        "\u9225",
        "\u9983",
        "\u95b3",
        "\u68e3",
        "\ufffd",
    )

    offenders = []
    for item in list_techniques():
        name = item["name"]
        engine_cls = get_engine(name)
        public_text = " ".join(
            str(getattr(engine_cls, attr, ""))
            for attr in ("label", "description", "icon")
        )
        if any(token in public_text for token in bad_tokens):
            offenders.append(f"engine:{name}")

    root = Path(__file__).resolve().parents[1] / "polynexus"
    logger_pattern = re.compile(r"logger\.(?:warning|error)\((?P<message>[^)\n]+)")
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in logger_pattern.finditer(text):
            if any(token in match.group("message") for token in bad_tokens):
                offenders.append(str(path.relative_to(root.parent)))

    assert offenders == []


def test_core_physics_logs_are_contextual_not_generic():
    root = Path(__file__).resolve().parents[1]
    paths = [
        root / "polynexus" / "core" / "dsc_engine" / "core.py",
        root / "polynexus" / "core" / "waxs_engine" / "core.py",
        root / "polynexus" / "core" / "nmr_engine" / "core.py",
    ]
    generic_tokens = ("异常已处理", "静默异常", "Unexpected error")
    offenders = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(token in text for token in generic_tokens):
            offenders.append(str(path.relative_to(root)))

    assert offenders == []
