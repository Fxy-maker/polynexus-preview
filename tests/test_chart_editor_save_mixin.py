from __future__ import annotations

import importlib
import importlib.util
from copy import deepcopy
from pathlib import Path

from polynexus.core.figure_document import load_figure_document
from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.figures.project_service import FigureProjectService
from polynexus.gui.plot_gallery_service import build_active_manifest_gallery_entries
from polynexus.gui.widgets.chart_editor import ChartEditor
from polynexus.gui.widgets.chart_editor_save_mixin import ChartEditorSaveMixin


class _BundleStatusStub:
    def __init__(self):
        self.text = ""

    def setText(self, value):
        self.text = str(value)


class _BundleSessionStub:
    def __init__(self):
        self.saved = False

    def mark_saved(self):
        self.saved = True


class _BundleHarness(ChartEditorSaveMixin):
    def __init__(self):
        self._editor_dirty = True
        self._status_label = _BundleStatusStub()
        self._edit_session = _BundleSessionStub()

    def _set_editor_dirty(self, dirty):
        self._editor_dirty = bool(dirty)


class _SignalRecorder:
    def __init__(self):
        self.values = []

    def emit(self, value):
        self.values.append(value)


class _StatusRecorder:
    def __init__(self):
        self.text = ""

    def setText(self, value):
        self.text = value


def _manifest_save_harness(mixin, entry, document):
    class _Harness(mixin):
        def __init__(self):
            self._source_entry_context = entry
            self._source_path = entry.preview_path
            self._target_path = entry.primary_path
            self._figure_document = deepcopy(document)
            self.figure_saved = _SignalRecorder()
            self._status_label = _StatusRecorder()
            self.legacy_saves = []

        def _generated_document_for_save(self):
            return deepcopy(self._figure_document)

        def _save_to_path(self, path):
            self.legacy_saves.append(str(path))

        def set_source_figure(
            self,
            path,
            *,
            source_entry_context=None,
            force_static=False,
        ):
            self._source_path = str(path)
            self._source_entry_context = source_entry_context
            self._force_static_source_mode = bool(force_static)
            self._figure_document = load_figure_document(
                source_entry_context.document_path
            )

    return _Harness()


def test_chart_editor_reuses_save_and_style_helpers_from_save_mixin() -> None:
    spec = importlib.util.find_spec("polynexus.gui.widgets.chart_editor_save_mixin")
    assert spec is not None

    module = importlib.import_module("polynexus.gui.widgets.chart_editor_save_mixin")
    mixin = module.ChartEditorSaveMixin

    assert ChartEditor.save_to_target is mixin.save_to_target
    assert ChartEditor.publish_complete_assets is mixin.publish_complete_assets
    assert ChartEditor._save_manifest_working is mixin._save_manifest_working
    assert (
        ChartEditor._refresh_manifest_project_entry
        is mixin._refresh_manifest_project_entry
    )
    assert ChartEditor.save_as is mixin.save_as
    assert ChartEditor._save_to_path is mixin._save_to_path
    assert (
        ChartEditor._save_generated_document_figure
        is mixin._save_generated_document_figure
    )
    assert (
        ChartEditor._generated_document_for_save
        is mixin._generated_document_for_save
    )
    assert ChartEditor._backup_current_static_source is mixin._backup_current_static_source
    assert ChartEditor._collect_style_state is mixin._collect_style_state
    assert ChartEditor._annotation_state is mixin._annotation_state
    assert ChartEditor._should_save_static_canvas is mixin._should_save_static_canvas
    assert ChartEditor._apply_saved_style is mixin._apply_saved_style
    assert (
        ChartEditor._apply_generated_document_style_controls
        is mixin._apply_generated_document_style_controls
    )
    assert ChartEditor._set_line_edit is mixin._set_line_edit
    assert ChartEditor._set_combo is mixin._set_combo


def test_chart_editor_save_mixin_save_to_target_delegates_to_save_as_without_target() -> None:
    module = importlib.import_module("polynexus.gui.widgets.chart_editor_save_mixin")

    class _Window(module.ChartEditorSaveMixin):
        def __init__(self):
            self._target_path = ""
            self.calls = []

        def save_as(self, fmt=None):
            self.calls.append(("save_as", fmt))

        def _save_to_path(self, path):
            self.calls.append(("save_to_path", path))

    window = _Window()

    window.save_to_target()

    assert window.calls == [("save_as", None)]


def test_chart_editor_save_mixin_generated_document_for_save_merges_style_state() -> None:
    module = importlib.import_module("polynexus.gui.widgets.chart_editor_save_mixin")

    class _Window(module.ChartEditorSaveMixin):
        def __init__(self):
            self._figure_document = {
                "mode": "draft",
                "style": {
                    "colour_scheme": "Old",
                    "font": "OldFont",
                    "line_width": "Thin",
                    "figure_size": "Legacy",
                    "grid_on": False,
                    "grid_alpha": 0.1,
                    "bg_color": "#000000",
                    "dpi": 72,
                    "title": "Old title",
                    "xlabel": "Old x",
                    "ylabel": "Old y",
                    "keep": "untouched",
                },
            }
            self._style_state = {
                "colour_scheme": "Wong (SCI)",
                "font": "Small",
                "line_width": "Normal",
                "figure_size": "Small (4in)",
                "grid_on": True,
                "grid_alpha": 0.4,
                "bg_color": "#FFFFFF",
                "dpi": 300,
                "title": "New title",
                "xlabel": "New x",
                "ylabel": "New y",
            }

        def _collect_style_state(self):
            return deepcopy(self._style_state)

    window = _Window()

    document = window._generated_document_for_save()

    assert document["mode"] == "object"
    assert document["style"]["colour_scheme"] == "Wong (SCI)"
    assert document["style"]["font"] == "Small"
    assert document["style"]["line_width"] == "Normal"
    assert document["style"]["figure_size"] == "Small (4in)"
    assert document["style"]["grid_on"] is True
    assert document["style"]["grid_alpha"] == 0.4
    assert document["style"]["bg_color"] == "#FFFFFF"
    assert document["style"]["dpi"] == 300
    assert document["style"]["title"] == "New title"
    assert document["style"]["xlabel"] == "New x"
    assert document["style"]["ylabel"] == "New y"
    assert document["style"]["keep"] == "untouched"
    assert window._figure_document["mode"] == "draft"


def test_manifest_save_edits_creates_working_revision_without_legacy_export(
    ir_definition,
    tmp_path,
) -> None:
    module = importlib.import_module("polynexus.gui.widgets.chart_editor_save_mixin")
    initial = FigurePipeline().run(
        output_root=tmp_path,
        run_id="run-1",
        technique="ir",
        definitions=(ir_definition,),
    )
    run_root = tmp_path / "runs" / "run-1"
    entry = build_active_manifest_gallery_entries(tmp_path)[0]
    document = load_figure_document(entry.document_path)
    document["objects"][0]["style"]["color"] = "#D55E00"
    formal_before = {
        role: (run_root / initial.figures[0].assets[role]).read_bytes()
        for role in ("svg", "png", "pdf")
    }
    window = _manifest_save_harness(module.ChartEditorSaveMixin, entry, document)

    window.save_to_target()

    refreshed = window._source_entry_context
    assert window.legacy_saves == []
    assert refreshed.working_revision == 2
    assert refreshed.published_revision == 1
    assert "revisions/r0002/" in refreshed.preview_path.replace("\\", "/")
    assert window._source_path == refreshed.preview_path
    assert window._figure_document["objects"][0]["style"]["color"] == "#D55E00"
    assert window.figure_saved.values == [refreshed.preview_path]
    assert all(
        (run_root / initial.figures[0].assets[role]).read_bytes()
        == formal_before[role]
        for role in formal_before
    )


def test_manifest_publish_refreshes_complete_publication_without_new_working_save(
    ir_definition,
    tmp_path,
) -> None:
    module = importlib.import_module("polynexus.gui.widgets.chart_editor_save_mixin")
    initial = FigurePipeline().run(
        output_root=tmp_path,
        run_id="run-1",
        technique="ir",
        definitions=(ir_definition,),
    )
    entry = build_active_manifest_gallery_entries(tmp_path)[0]
    document = load_figure_document(entry.document_path)
    document["objects"][0]["style"]["line_width"] = 1.8
    FigureProjectService(tmp_path).save_working(
        run_id="run-1",
        figure_id=initial.figures[0].figure_id,
        document=document,
    )
    working_entry = build_active_manifest_gallery_entries(tmp_path)[0]
    window = _manifest_save_harness(
        module.ChartEditorSaveMixin,
        working_entry,
        load_figure_document(working_entry.document_path),
    )

    window.publish_complete_assets()

    refreshed = window._source_entry_context
    assert window.legacy_saves == []
    assert refreshed.working_revision == 2
    assert refreshed.published_revision == 2
    assert refreshed.publication_status == "quality_failed"
    assert all(
        "publications/r0002/assets/" in asset.path.replace("\\", "/")
        for asset in refreshed.assets
    )
    assert window._source_path == refreshed.preview_path
    assert window._figure_document["export"]["published_revision"] == 2
    assert window.figure_saved.values == [refreshed.preview_path]


def test_chart_editor_save_mixin_bundle_success_marks_session_saved(tmp_path):
    harness = _BundleHarness()

    result = harness._save_edit_bundle(
        tmp_path / "edited.png",
        {"version": 1, "objects": []},
        b"image",
        {"font": "Small"},
        [],
    )

    assert result is not None and result.ok is True
    assert harness._edit_session.saved is True
    assert harness._editor_dirty is True


def test_chart_editor_save_mixin_bundle_failure_keeps_dirty_and_reports_status(
    tmp_path, monkeypatch
):
    harness = _BundleHarness()
    target = tmp_path / "edited.png"
    target.write_bytes(b"old")
    monkeypatch.setattr(
        Path,
        "replace",
        lambda *_: (_ for _ in ()).throw(OSError("disk full")),
    )

    result = harness._save_edit_bundle(
        target,
        {"version": 1, "objects": []},
        b"new",
    )

    assert result is None
    assert harness._editor_dirty is True
    assert "Save failed" in harness._status_label.text
    assert harness._edit_session.saved is False
