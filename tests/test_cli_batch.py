from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
import io


def test_batch_invalid_dir(tmp_path):
    from polynexus.__main__ import run_batch

    class Args:
        input_dir = str(tmp_path / "missing")
        technique = "saxs"
        pattern = "*"
        workers = 1
        output_dir = None

    stderr = io.StringIO()
    with redirect_stderr(stderr):
        assert run_batch(Args()) == 2
    assert "is not a valid directory" in stderr.getvalue()


def test_batch_empty_dir(tmp_path):
    from polynexus.__main__ import run_batch

    class Args:
        input_dir = str(tmp_path)
        technique = "saxs"
        pattern = "*"
        workers = 1
        output_dir = None

    stderr = io.StringIO()
    with redirect_stderr(stderr):
        assert run_batch(Args()) == 2
    assert "No supported files found" in stderr.getvalue()


def test_batch_unsupported_files(tmp_path):
    (tmp_path / "file.unsupported").write_text("hello", encoding="utf-8")
    from polynexus.__main__ import run_batch

    class Args:
        input_dir = str(tmp_path)
        technique = "saxs"
        pattern = "*"
        workers = 1
        output_dir = None

    stderr = io.StringIO()
    with redirect_stderr(stderr):
        assert run_batch(Args()) == 2
    assert "No supported files found" in stderr.getvalue()


def test_batch_single_file_mock(tmp_path, monkeypatch):
    dat = tmp_path / "sample.dat"
    dat.write_text("q I\n0.1 100\n0.2 90\n", encoding="utf-8")

    class FakeResult:
        r_squared = 0.99
        parameters = {"r_squared": 0.99}

    class FakeEngine:
        def run_pipeline(self, *args, **kwargs):
            return FakeResult()

    import polynexus.__main__ as main_mod

    calls = []
    monkeypatch.setattr(main_mod, "get_engine", lambda tech: FakeEngine())
    monkeypatch.setattr(main_mod, "_persist_batch_run", lambda *args, **kwargs: calls.append(args))

    class Args:
        input_dir = str(tmp_path)
        technique = "saxs"
        pattern = "*.dat"
        workers = 1
        output_dir = None

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        result = main_mod.run_batch(Args())
    assert result == 0
    assert len(calls) == 1
    text = stdout.getvalue()
    assert "Starting batch analysis [SAXS]" in text
    assert "Completed: 1 succeeded, 0 failed, 1 total." in text


def test_batch_preset_helper_round_trip(tmp_path, monkeypatch):
    import polynexus.__main__ as main_mod

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    class Args:
        input_dir = str(tmp_path / "inputs")
        technique = "waxs"
        pattern = "*.csv"
        workers = 3
        output_dir = str(tmp_path / "output")
        preset = None
        save_preset = "lab-batch"
        delete_preset = None
        list_presets = False

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        assert main_mod._apply_batch_preset_actions(Args()) == 0
    saved_text = stdout.getvalue()
    assert "Saved batch preset: lab-batch" in saved_text
    assert "technique=waxs" in saved_text
    assert f"input_dir={tmp_path / 'inputs'}" in saved_text

    class LoadArgs:
        input_dir = None
        technique = None
        pattern = "*"
        workers = 1
        output_dir = None
        preset = "lab-batch"
        save_preset = None
        delete_preset = None
        list_presets = False

    load_args = LoadArgs()
    assert main_mod._apply_batch_preset_actions(load_args) is None
    assert load_args.input_dir == str(tmp_path / "inputs")
    assert load_args.technique == "waxs"
    assert load_args.pattern == "*.csv"
    assert load_args.workers == 3
    assert load_args.output_dir == str(tmp_path / "output")

    class ListArgs:
        input_dir = None
        technique = None
        pattern = "*"
        workers = 1
        output_dir = None
        preset = None
        save_preset = None
        delete_preset = None
        list_presets = True

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        assert main_mod._apply_batch_preset_actions(ListArgs()) == 0
    list_text = stdout.getvalue()
    assert "Batch presets:" in list_text
    assert "lab-batch" in list_text
    assert "technique=waxs" in list_text

    class DeleteArgs:
        input_dir = None
        technique = None
        pattern = "*"
        workers = 1
        output_dir = None
        preset = None
        save_preset = None
        delete_preset = "lab-batch"
        list_presets = False

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        assert main_mod._apply_batch_preset_actions(DeleteArgs()) == 0
    deleted_text = stdout.getvalue()
    assert "Deleted batch preset: lab-batch" in deleted_text
    assert "technique=waxs" in deleted_text


def test_run_batch_uses_loaded_preset(tmp_path, monkeypatch):
    dat = tmp_path / "sample.dat"
    dat.write_text("q I\n0.1 100\n0.2 90\n", encoding="utf-8")

    import polynexus.__main__ as main_mod

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    main_mod.save_batch_preset(
        "saved-saxs",
        {
            "input_dir": str(tmp_path),
            "technique": "saxs",
            "pattern": "*.dat",
            "workers": 2,
            "output_dir": str(tmp_path / "batch_output"),
        },
    )

    class FakeResult:
        r_squared = 0.98
        parameters = {"r_squared": 0.98}

    class FakeEngine:
        def run_pipeline(self, *args, **kwargs):
            return FakeResult()

    calls = []
    monkeypatch.setattr(main_mod, "get_engine", lambda tech: FakeEngine())
    monkeypatch.setattr(main_mod, "_persist_batch_run", lambda *args, **kwargs: calls.append(args))

    class Args:
        input_dir = None
        technique = None
        pattern = "*"
        workers = 1
        output_dir = None
        preset = "saved-saxs"
        save_preset = None
        delete_preset = None
        list_presets = False

    args = Args()
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        result = main_mod.run_batch(args)
    assert result == 0
    assert len(calls) == 1
    assert args.input_dir == str(tmp_path)
    assert args.technique == "saxs"
    assert args.pattern == "*.dat"
    assert args.workers == 2
    text = stdout.getvalue()
    assert "Loaded batch preset: saved-saxs" in text
    assert "technique=saxs" in text
    assert f"input_dir={tmp_path}" in text
    assert "pattern=*.dat" in text
    assert "workers=2" in text
    assert "requested workers=2" in text
    assert "running sequentially" in text
    assert "Starting batch analysis [SAXS]" in text
    assert "Completed: 1 succeeded, 0 failed, 1 total." in text


def test_run_batch_loaded_preset_respects_explicit_cli_overrides(tmp_path, monkeypatch):
    dat = tmp_path / "sample.dat"
    dat.write_text("q I\n0.1 100\n0.2 90\n", encoding="utf-8")

    import polynexus.__main__ as main_mod

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    main_mod.save_batch_preset(
        "saved-saxs",
        {
            "input_dir": str(tmp_path),
            "technique": "saxs",
            "pattern": "*.dat",
            "workers": 2,
            "output_dir": str(tmp_path / "batch_output"),
        },
    )

    class FakeResult:
        r_squared = 0.98
        parameters = {"r_squared": 0.98}

    class FakeEngine:
        def run_pipeline(self, *args, **kwargs):
            return FakeResult()

    calls = []
    monkeypatch.setattr(main_mod, "get_engine", lambda tech: FakeEngine())
    monkeypatch.setattr(main_mod, "_persist_batch_run", lambda *args, **kwargs: calls.append(args))

    class Args:
        input_dir = None
        technique = "waxs"
        pattern = "*"
        workers = 5
        output_dir = str(tmp_path / "manual_output")
        preset = "saved-saxs"
        save_preset = None
        delete_preset = None
        list_presets = False

    args = Args()
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        result = main_mod.run_batch(args)
    assert result == 0
    assert len(calls) == 1
    assert args.input_dir == str(tmp_path)
    assert args.technique == "waxs"
    assert args.pattern == "*.dat"
    assert args.workers == 5
    assert args.output_dir == str(tmp_path / "manual_output")
    text = stdout.getvalue()
    assert "Loaded batch preset: saved-saxs" in text
    assert "technique=waxs" in text
    assert "workers=5" in text
    assert f"output_dir={tmp_path / 'manual_output'}" in text
    assert "requested workers=5" in text
    assert "running sequentially" in text


def test_batch_last_run_helper_round_trip(tmp_path, monkeypatch):
    import polynexus.__main__ as main_mod

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    values = {
        "input_dir": str(tmp_path / "inputs"),
        "technique": "ir",
        "pattern": "*.csv",
        "workers": 4,
        "output_dir": str(tmp_path / "out"),
    }

    main_mod.save_batch_last_run(values)

    class Args:
        input_dir = None
        technique = None
        pattern = "*"
        workers = 1
        output_dir = None
        preset = None
        save_preset = None
        delete_preset = None
        list_presets = False
        rerun_last = True

    args = Args()
    assert main_mod._apply_batch_preset_actions(args) is None
    assert args.input_dir == values["input_dir"]
    assert args.technique == values["technique"]
    assert args.pattern == values["pattern"]
    assert args.workers == values["workers"]
    assert args.output_dir == values["output_dir"]


def test_batch_actions_reject_preset_and_rerun_last_together(tmp_path, monkeypatch):
    import polynexus.__main__ as main_mod

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    class Args:
        input_dir = None
        technique = None
        pattern = "*"
        workers = 1
        output_dir = None
        preset = "saved-saxs"
        save_preset = None
        delete_preset = None
        list_presets = False
        rerun_last = True

    assert main_mod._apply_batch_preset_actions(Args()) == 2


def test_batch_save_preset_requires_core_fields(tmp_path, monkeypatch):
    import polynexus.__main__ as main_mod

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    class MissingInputArgs:
        input_dir = None
        technique = "saxs"
        pattern = "*.dat"
        workers = 1
        output_dir = None
        preset = None
        save_preset = "saved-saxs"
        delete_preset = None
        list_presets = False
        rerun_last = False

    class MissingTechniqueArgs:
        input_dir = str(tmp_path)
        technique = None
        pattern = "*.dat"
        workers = 1
        output_dir = None
        preset = None
        save_preset = "saved-saxs"
        delete_preset = None
        list_presets = False
        rerun_last = False

    assert main_mod._apply_batch_preset_actions(MissingInputArgs()) == 2
    assert main_mod._apply_batch_preset_actions(MissingTechniqueArgs()) == 2


def test_run_batch_rerun_last_without_snapshot_returns_2(tmp_path, monkeypatch):
    import polynexus.__main__ as main_mod

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    class Args:
        input_dir = None
        technique = None
        pattern = "*"
        workers = 1
        output_dir = None
        preset = None
        save_preset = None
        delete_preset = None
        list_presets = False
        rerun_last = True

    assert main_mod.run_batch(Args()) == 2


def test_run_batch_uses_last_snapshot(tmp_path, monkeypatch):
    dat = tmp_path / "sample.dat"
    dat.write_text("q I\n0.1 100\n0.2 90\n", encoding="utf-8")

    import polynexus.__main__ as main_mod

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    main_mod.save_batch_last_run(
        {
            "input_dir": str(tmp_path),
            "technique": "saxs",
            "pattern": "*.dat",
            "workers": 2,
            "output_dir": str(tmp_path / "rerun_output"),
        }
    )

    class FakeResult:
        r_squared = 0.97
        parameters = {"r_squared": 0.97}

    class FakeEngine:
        def run_pipeline(self, *args, **kwargs):
            return FakeResult()

    calls = []
    monkeypatch.setattr(main_mod, "get_engine", lambda tech: FakeEngine())
    monkeypatch.setattr(main_mod, "_persist_batch_run", lambda *args, **kwargs: calls.append(args))

    class Args:
        input_dir = None
        technique = None
        pattern = "*"
        workers = 1
        output_dir = None
        preset = None
        save_preset = None
        delete_preset = None
        list_presets = False
        rerun_last = True

    args = Args()
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        result = main_mod.run_batch(args)
    assert result == 0
    assert len(calls) == 1
    assert args.input_dir == str(tmp_path)
    assert args.technique == "saxs"
    assert args.pattern == "*.dat"
    assert args.workers == 2
    assert args.output_dir == str(tmp_path / "rerun_output")
    text = stdout.getvalue()
    assert "Loaded last batch task snapshot." in text
    assert "technique=saxs" in text
    assert f"input_dir={tmp_path}" in text
    assert "pattern=*.dat" in text
    assert "workers=2" in text


def test_run_batch_rerun_last_respects_explicit_cli_overrides(tmp_path, monkeypatch):
    dat = tmp_path / "sample.dat"
    dat.write_text("q I\n0.1 100\n0.2 90\n", encoding="utf-8")

    import polynexus.__main__ as main_mod

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    main_mod.save_batch_last_run(
        {
            "input_dir": str(tmp_path),
            "technique": "saxs",
            "pattern": "*.dat",
            "workers": 2,
            "output_dir": str(tmp_path / "rerun_output"),
        }
    )

    class FakeResult:
        r_squared = 0.97
        parameters = {"r_squared": 0.97}

    class FakeEngine:
        def run_pipeline(self, *args, **kwargs):
            return FakeResult()

    calls = []
    monkeypatch.setattr(main_mod, "get_engine", lambda tech: FakeEngine())
    monkeypatch.setattr(main_mod, "_persist_batch_run", lambda *args, **kwargs: calls.append(args))

    class Args:
        input_dir = None
        technique = "waxs"
        pattern = "*"
        workers = 6
        output_dir = str(tmp_path / "manual_output")
        preset = None
        save_preset = None
        delete_preset = None
        list_presets = False
        rerun_last = True

    args = Args()
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        result = main_mod.run_batch(args)
    assert result == 0
    assert len(calls) == 1
    assert args.input_dir == str(tmp_path)
    assert args.technique == "waxs"
    assert args.pattern == "*.dat"
    assert args.workers == 6
    assert args.output_dir == str(tmp_path / "manual_output")
    text = stdout.getvalue()
    assert "Loaded last batch task snapshot." in text
    assert "technique=waxs" in text
    assert "workers=6" in text
    assert f"output_dir={tmp_path / 'manual_output'}" in text


def test_run_batch_saves_last_snapshot_even_when_some_files_fail(tmp_path, monkeypatch):
    import polynexus.__main__ as main_mod

    first = tmp_path / "ok.dat"
    second = tmp_path / "bad.dat"
    first.write_text("q I\n0.1 100\n", encoding="utf-8")
    second.write_text("q I\n0.1 90\n", encoding="utf-8")

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    def fake_run_batch_one(task):
        file_path, technique, output_dir = task
        if file_path.endswith("bad.dat"):
            return {"file": "bad.dat", "technique": technique, "status": "FAILED", "r2": None, "elapsed": 0.2}
        return {"file": "ok.dat", "technique": technique, "status": "OK", "r2": 0.95, "elapsed": 0.1}

    monkeypatch.setattr(main_mod, "_run_batch_one", fake_run_batch_one)

    class Args:
        input_dir = str(tmp_path)
        technique = "saxs"
        pattern = "*.dat"
        workers = 1
        output_dir = str(tmp_path / "out")
        preset = None
        save_preset = None
        delete_preset = None
        list_presets = False
        rerun_last = False

    result = main_mod.run_batch(Args())
    assert result == 1

    last = main_mod.load_batch_last_run()
    assert last is not None
    assert last["input_dir"] == str(tmp_path)
    assert last["technique"] == "saxs"
    assert last["pattern"] == "*.dat"
    assert last["workers"] == 1
    assert last["output_dir"] == str(tmp_path / "out")
