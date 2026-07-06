"""Tests for PolyNexus core engine."""

import ast
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


def _logger_messages(paths, *, attrs=("warning",)):
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8-sig", errors="ignore"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr in attrs
                and isinstance(func.value, ast.Name)
                and func.value.id == "logger"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                continue
            yield path, node.args[0].value


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
        "寮傚父",
        "闈欓粯",
        "閳",
        "棣",
        "鈥",
        "馃",
        "閲",
        "�",
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
    for path, message in _logger_messages(root.rglob("*.py"), attrs=("warning", "error")):
        if any(token in message for token in bad_tokens):
            offenders.append(f"{path}: {message}")

    assert offenders == []


def test_core_logger_warning_messages_are_contextual():
    root = Path(__file__).resolve().parents[1] / "polynexus" / "core"
    generic_messages = {"异常已处理", "静默异常", "Unexpected error"}
    checked = 0

    for path, message in _logger_messages(root.rglob("*.py")):
        checked += 1
        assert message not in generic_messages, f"{path}: {message}"

    assert checked > 0


def test_clean_non_core_logger_warning_messages_are_contextual():
    repo_root = Path(__file__).resolve().parents[1]
    generic_messages = {"异常已处理", "静默异常", "Unexpected error"}
    paths = [
        repo_root / "polynexus" / "data" / "fetch_pubchem.py",
        repo_root / "polynexus" / "gui" / "convergence_viewer.py",
        repo_root / "polynexus" / "orchestrator.py",
        repo_root / "polynexus" / "plotting" / "sci_style.py",
        *sorted((repo_root / "polynexus" / "readers").glob("*.py")),
    ]
    checked = 0

    for path, message in _logger_messages(paths):
        checked += 1
        assert message not in generic_messages, f"{path}: {message}"

    assert checked > 0


def test_figure_workbench_logger_warning_messages_are_contextual():
    repo_root = Path(__file__).resolve().parents[1]
    generic_messages = {"异常已处理", "静默异常", "闈欓粯寮傚父", "Unexpected error"}
    paths = [
        repo_root / "polynexus" / "core" / "plot_edits.py",
        repo_root / "polynexus" / "gui" / "widgets" / "chart_editor.py",
    ]
    checked = 0

    for path, message in _logger_messages(paths):
        checked += 1
        assert message not in generic_messages, f"{path}: {message}"

    assert checked > 0


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
