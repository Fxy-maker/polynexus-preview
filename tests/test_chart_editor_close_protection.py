from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from polynexus.gui.widgets.chart_editor import ChartEditor


class _CloseEvent:
    def __init__(self):
        self.accepted = False
        self.ignored = False

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.ignored = True


class _EditorHarness:
    def __init__(self, dirty=False):
        self._editor_dirty = dirty
        self.save_calls = 0

    def save_to_target(self):
        self.save_calls += 1


def test_clean_editor_closes_without_prompt():
    editor = _EditorHarness()
    event = _CloseEvent()

    ChartEditor.closeEvent(editor, event)

    assert event.accepted is True
    assert event.ignored is False


def test_dirty_editor_cancel_keeps_window_open(monkeypatch):
    editor = _EditorHarness(dirty=True)
    monkeypatch.setattr(
        "polynexus.gui.widgets.chart_editor.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Cancel,
    )
    event = _CloseEvent()

    ChartEditor.closeEvent(editor, event)

    assert event.accepted is False
    assert event.ignored is True


def test_dirty_editor_discard_closes_without_saving(monkeypatch):
    editor = _EditorHarness(dirty=True)
    monkeypatch.setattr(
        "polynexus.gui.widgets.chart_editor.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Discard,
    )
    event = _CloseEvent()

    ChartEditor.closeEvent(editor, event)

    assert event.accepted is True
    assert editor.save_calls == 0


def test_dirty_editor_save_closes_only_after_save_clears_dirty(monkeypatch):
    editor = _EditorHarness(dirty=True)
    editor.save_to_target = lambda: setattr(editor, "_editor_dirty", False)
    monkeypatch.setattr(
        "polynexus.gui.widgets.chart_editor.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Save,
    )
    event = _CloseEvent()

    ChartEditor.closeEvent(editor, event)

    assert event.accepted is True


def test_dirty_editor_save_failure_keeps_window_open(monkeypatch):
    editor = _EditorHarness(dirty=True)
    monkeypatch.setattr(
        "polynexus.gui.widgets.chart_editor.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Save,
    )
    event = _CloseEvent()

    ChartEditor.closeEvent(editor, event)

    assert event.accepted is False
    assert event.ignored is True


def test_dirty_editor_save_exception_keeps_window_open(monkeypatch):
    editor = _EditorHarness(dirty=True)

    def _raise_save_error():
        raise OSError("disk full")

    editor.save_to_target = _raise_save_error
    monkeypatch.setattr(
        "polynexus.gui.widgets.chart_editor.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Save,
    )
    event = _CloseEvent()

    ChartEditor.closeEvent(editor, event)

    assert event.accepted is False
    assert event.ignored is True
