import json
from pathlib import Path
from types import SimpleNamespace

from polynexus.cli.parser import build_parser
from polynexus.cli import run_suite_service


def test_parser_exposes_suite_handoff():
    args = build_parser().parse_args(["suite", "handoff", "--package", "pkg"])
    assert args.cmd == "suite"
    assert args.operation == "handoff"
    assert args.package == "pkg"


def test_cli_doctor_delegates_to_shared_manager(monkeypatch, capsys):
    class FakeStatus:
        def to_dict(self):
            return {"status": "ready"}

    class FakeManager:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def doctor(self):
            return FakeStatus()

    monkeypatch.setattr(run_suite_service, "SuiteManager", FakeManager)
    code = run_suite_service.run_suite(SimpleNamespace(operation="doctor", manifest=None, codex_skills_dir=None, lock=None))
    assert code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ready"


def test_cli_install_requires_yes(monkeypatch, capsys):
    class FakeStatus:
        def to_dict(self):
            return {"status": "confirmation_required"}

    class FakeManager:
        def __init__(self, **kwargs):
            pass

        def install(self, *args, **kwargs):
            assert kwargs["confirm"] is False
            return FakeStatus()

    monkeypatch.setattr(run_suite_service, "SuiteManager", FakeManager)
    code = run_suite_service.run_suite(SimpleNamespace(operation="install-ars", manifest=None, codex_skills_dir=None, lock=None, yes=False, source=None))
    assert code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "confirmation_required"
