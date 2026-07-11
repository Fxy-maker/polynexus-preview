from pathlib import Path

from polynexus.gui.i18n import get_language, set_language
from polynexus.gui.sample_analysis_service import request_sample_batch_analysis


class _FakeButton:
    def __init__(self):
        self.checked = False

    def setChecked(self, value):
        self.checked = bool(value)


class _FakeOutputInput:
    def __init__(self):
        self.text = ""

    def setText(self, value):
        self.text = value


class _FakeTabs:
    def __init__(self):
        self.index = None

    def setCurrentIndex(self, value):
        self.index = value


class _FakeDb:
    def __init__(self, *, batch, sample, files, runs):
        self._batch = batch
        self._sample = sample
        self._files = files
        self._runs = runs

    def get_batch(self, batch_id):
        return self._batch if batch_id == self._batch["id"] else None

    def get_sample(self, sample_id):
        return self._sample if sample_id == self._sample["id"] else None

    def get_data_files(self, batch_id):
        return list(self._files if batch_id == self._batch["id"] else [])

    def get_analysis_runs(self, batch_id):
        return list(self._runs if batch_id == self._batch["id"] else [])


class _FakeWindow:
    def __init__(self, db):
        self._db = db
        self._current_submodule_id = "initial"
        self._nav_buttons = {
            "waxs": _FakeButton(),
            "waxs.static": _FakeButton(),
        }
        self._output_input = _FakeOutputInput()
        self._tabs = _FakeTabs()
        self.events = []
        self._output_dir = ""

    def _ensure_sample_db(self):
        return self._db

    def _set_sample_batch_context(self, **kwargs):
        self.events.append(("context", kwargs))

    def _on_technique_selected(self, technique):
        self.events.append(("technique", technique))
        self._current_technique = technique

    def _on_submodule_selected(self, technique, submodule_id):
        self.events.append(("submodule", technique, submodule_id))
        self._current_submodule_id = submodule_id

    def _set_input_path(self, path, clear_sample_context=True):
        self.events.append(("input", path, clear_sample_context))

    def _save_last_dir(self, path):
        self.events.append(("last_dir", path))

    def _update_workspace_context(self):
        self.events.append(("workspace",))

    def log(self, message):
        self.events.append(("log", message))


def test_request_sample_batch_analysis_switches_workspace_and_prefills_paths(tmp_path):
    data_file = tmp_path / "sample.edf"
    data_file.write_text("data", encoding="utf-8")

    db = _FakeDb(
        batch={"id": "batch-1", "sample_id": "sample-1", "label": "batch-01"},
        sample={"id": "sample-1", "polymer_name": "PA6"},
        files=[{"file_path": str(data_file), "technique": "waxs"}],
        runs=[{"technique": "waxs", "submodule": "waxs.static", "output_dir": str(tmp_path / "output")}],
    )
    window = _FakeWindow(db)

    request_sample_batch_analysis(window, "batch-1")

    assert window._current_technique == "waxs"
    assert window._current_submodule_id == "waxs.static"
    assert window._output_dir == str(tmp_path / "output")
    assert window._output_input.text == str(tmp_path / "output")
    assert window._tabs.index == 0
    assert window._nav_buttons["waxs"].checked is True
    assert window._nav_buttons["waxs.static"].checked is True
    assert ("log", "LOG_SAMPLE_BATCH_ANALYSIS_READY") not in window.events
    assert any(event[0] == "log" for event in window.events)
    assert ("input", str(data_file), False) in window.events
    assert ("last_dir", str(data_file)) in window.events


def test_request_sample_batch_analysis_warns_when_batch_has_no_files(monkeypatch):
    captured = []
    monkeypatch.setattr(
        "polynexus.gui.sample_analysis_service.QMessageBox.warning",
        lambda *args: captured.append(args),
    )

    db = _FakeDb(
        batch={"id": "batch-1", "sample_id": "sample-1", "label": "batch-01"},
        sample={"id": "sample-1", "polymer_name": "PA6"},
        files=[],
        runs=[],
    )
    window = _FakeWindow(db)

    previous = get_language()
    try:
        set_language("en")
        request_sample_batch_analysis(window, "batch-1")
    finally:
        set_language(previous)

    assert len(captured) == 1
    assert captured[0][1] == "Use in Analysis"
