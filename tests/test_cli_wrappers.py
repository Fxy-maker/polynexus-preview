from polynexus.cli.run_ai_tune import run_ai_tune
from polynexus.cli.run_batch import run_batch
from polynexus.cli.run_single import run_single


def test_cli_wrappers_delegate_to_main_module(monkeypatch):
    import polynexus.__main__ as main_mod

    seen = []
    monkeypatch.setattr(main_mod, "_run_single", lambda args: seen.append(("single", args)) or 11)
    monkeypatch.setattr(main_mod, "run_batch", lambda args: seen.append(("batch", args)) or 12)
    monkeypatch.setattr(main_mod, "_run_ai_tune", lambda args: seen.append(("ai", args)) or 13)

    marker = object()
    assert run_single(marker) == 11
    assert run_batch(marker) == 12
    assert run_ai_tune(marker) == 13
    assert seen == [("single", marker), ("batch", marker), ("ai", marker)]

