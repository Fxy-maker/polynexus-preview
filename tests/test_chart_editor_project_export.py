from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from polynexus.gui.widgets.chart_editor_save_mixin import ChartEditorSaveMixin


class _Label:
    def __init__(self):
        self.value = ""

    def setText(self, value):
        self.value = value


class _Harness(ChartEditorSaveMixin):
    def __init__(self, figure_path, entry=None):
        self._source_path = str(figure_path)
        self._target_path = str(figure_path)
        self._source_entry_context = entry
        self._figure_document = {"figure_id": "fig-a", "objects": []}
        self._generated_document_mode = False
        self._status_label = _Label()


def test_chart_editor_export_project_package_uses_current_document_context(
    monkeypatch, tmp_path
):
    from polynexus.gui import widgets as _widgets  # noqa: F401
    from polynexus.gui.widgets import chart_editor as chart_editor_module
    from polynexus.gui.widgets import chart_editor_save_mixin as module

    figure_path = tmp_path / "figure.png"
    figure_path.write_bytes(b"png")
    output = tmp_path / "figure.pnproject.zip"
    entry = SimpleNamespace(run_root=str(tmp_path / "run"))
    calls = {}

    monkeypatch.setattr(
        chart_editor_module.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(output), "Project package (*.pnproject.zip)"),
    )

    def _export(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(output_path=output)

    monkeypatch.setattr(module, "export_figure_project_bundle", _export)

    editor = _Harness(figure_path, entry)
    result = editor.export_project_package()

    assert result.output_path == output
    assert calls["document"] == editor._figure_document
    assert calls["figure_path"] == Path(figure_path)
    assert calls["source_root"] == Path(entry.run_root)
    assert str(output) in editor._status_label.value
