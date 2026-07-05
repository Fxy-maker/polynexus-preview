"""Tests for PolyNexus core engine."""

import ast
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


def test_core_logger_warning_messages_do_not_contain_mojibake():
    root = Path(__file__).resolve().parents[1] / "polynexus" / "core"
    bad_tokens = ("寮傚父", "闈欓粯", "鈥", "�")
    checked = 0

    for path in root.rglob("*.py"):
        if path.name == "plot_edits.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr == "warning"
                and isinstance(func.value, ast.Name)
                and func.value.id == "logger"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                continue
            checked += 1
            message = node.args[0].value
            assert not any(token in message for token in bad_tokens), f"{path}: {message}"

    assert checked > 0


def test_core_logger_warning_messages_are_contextual():
    root = Path(__file__).resolve().parents[1] / "polynexus" / "core"
    generic_messages = {"异常已处理", "静默异常", "Unexpected error"}
    checked = 0

    for path in root.rglob("*.py"):
        if path.name == "plot_edits.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr == "warning"
                and isinstance(func.value, ast.Name)
                and func.value.id == "logger"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                continue
            checked += 1
            message = node.args[0].value
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

    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8-sig", errors="ignore"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr == "warning"
                and isinstance(func.value, ast.Name)
                and func.value.id == "logger"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                continue
            checked += 1
            message = node.args[0].value
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

    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr == "warning"
                and isinstance(func.value, ast.Name)
                and func.value.id == "logger"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                continue
            checked += 1
            message = node.args[0].value
            assert message not in generic_messages, f"{path}: {message}"

    assert checked > 0
