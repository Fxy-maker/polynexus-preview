from datetime import datetime
from types import SimpleNamespace

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from polynexus.gui.figure_window_service import (
    chart_viewer_status_line,
    current_chart_raw_data,
    normalize_figure_path,
    open_convergence_viewer,
    open_chart_editor,
    open_chart_viewer,
    refresh_saved_figure_in_gallery,
    resolve_chart_editor_entry,
    show_chart_preview,
)
from polynexus.core.figure_document import save_generated_figure_document
from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.gui.plot_gallery_service import build_active_manifest_gallery_entries


class _FakeSignal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class _FakeViewer:
    def __init__(self):
        self.edit_requested = _FakeSignal()
        self.status_message = _FakeSignal()
        self.window_title = ""
        self.loaded = None
        self.resized = None
        self.shown = False
        self.raised = False
        self.activated = False
        self.entry = None
        self.data_resolution = None

    def setWindowTitle(self, title):
        self.window_title = title

    def load_figure(self, filepath, raw_data=None, *, entry=None, data_resolution=None):
        self.loaded = (filepath, raw_data)
        self.entry = entry
        self.data_resolution = data_resolution

    def resize(self, width, height):
        self.resized = (width, height)

    def show(self):
        self.shown = True

    def raise_(self):
        self.raised = True

    def activateWindow(self):
        self.activated = True


class _FakeEditor:
    def __init__(self):
        self.figure_saved = _FakeSignal()
        self.window_title = ""
        self.source_figure = ""
        self.source_entry = None
        self.force_static = None
        self.resized = None
        self.shown = False

    def setWindowTitle(self, title):
        self.window_title = title

    def set_source_figure(self, filepath):
        self.source_figure = filepath

    def set_source_figure_entry(self, entry, *, force_static=False):
        self.source_entry = entry
        self.force_static = force_static
        self.source_figure = getattr(entry, "editable_path", "") or getattr(entry, "primary_path", "") or getattr(entry, "preview_path", "")

    def resize(self, width, height):
        self.resized = (width, height)

    def show(self):
        self.shown = True


class _FakePreview:
    def __init__(self):
        self.visible = False
        self.loaded = ""
        self.entry = None

    def setVisible(self, visible):
        self.visible = bool(visible)

    def load_figure(self, filepath):
        self.loaded = filepath

    def set_entry_context(self, entry):
        self.entry = entry


class _FakeGallery:
    def __init__(self, paths):
        self._paths = list(paths)
        self.refreshed = []
        self.loaded = []
        self.selected = None

    def figure_paths(self):
        return list(self._paths)

    def refresh_figure(self, filepath):
        self.refreshed.append(filepath)

    def load_files(self, filepaths):
        self.loaded.append(list(filepaths))
        self._paths = list(filepaths)

    def select_figure(self, filepath, emit=False):
        self.selected = (filepath, emit)


class _FakeButton:
    def __init__(self):
        self.enabled = False

    def setEnabled(self, enabled):
        self.enabled = bool(enabled)


def test_normalize_figure_path_and_current_chart_raw_data_extract_values():
    assert normalize_figure_path(True, r"D:\fallback.png") == r"D:\fallback.png"
    assert normalize_figure_path("  D:/figures/result.png  ") == "D:/figures/result.png"

    assert current_chart_raw_data({"raw_data": {"x": [1, 2]}}) == {"x": [1, 2]}
    assert current_chart_raw_data(SimpleNamespace(raw_data={"y": [3, 4]})) == {"y": [3, 4]}
    assert current_chart_raw_data(SimpleNamespace(raw_data="nope")) is None


def test_chart_viewer_status_line_formats_timestamp_and_color():
    line = chart_viewer_status_line(
        "Saved figure",
        "success",
        timestamp=datetime(2026, 7, 8, 13, 45, 22),
    )

    assert line == '[13:45:22] <span style="color:#16a34a;">Saved figure</span>'


def test_show_chart_preview_enables_button_and_loads_figure():
    preview = _FakePreview()
    button = _FakeButton()

    path = show_chart_preview(preview, r"D:\figures\result.png", view_button=button)

    assert path == r"D:\figures\result.png"
    assert preview.visible is True
    assert preview.loaded == r"D:\figures\result.png"
    assert button.enabled is True


def test_show_chart_preview_passes_entry_context_when_preview_supports_it():
    preview = _FakePreview()
    button = _FakeButton()
    entry = SimpleNamespace(state="static_background", title="summary panel")

    path = show_chart_preview(
        preview,
        r"D:\figures\summary_panel.png",
        view_button=button,
        entry=entry,
    )

    assert path == r"D:\figures\summary_panel.png"
    assert preview.entry is entry


def test_open_chart_viewer_and_editor_configure_windows():
    viewer = open_chart_viewer(
        r"D:\figures\result.png",
        {"x": [1, 2]},
        viewer=None,
        viewer_factory=_FakeViewer,
        edit_requested_handler=lambda *_: None,
        status_message_handler=lambda *_: None,
    )

    assert "result.png" in viewer.window_title
    assert viewer.loaded == (r"D:\figures\result.png", {"x": [1, 2]})
    assert viewer.resized == (1180, 820)
    assert viewer.shown is True
    assert viewer.raised is True
    assert viewer.activated is True
    assert len(viewer.edit_requested.callbacks) == 1
    assert len(viewer.status_message.callbacks) == 1

    editor = open_chart_editor(
        r"D:\figures\result.png",
        editor=None,
        editor_factory=_FakeEditor,
        saved_handler=lambda *_: None,
    )

    assert "result.png" in editor.window_title
    assert editor.source_figure == r"D:\figures\result.png"
    assert editor.resized == (1000, 650)
    assert editor.shown is True
    assert len(editor.figure_saved.callbacks) == 1


def test_open_chart_viewer_binds_entry_data_resolution(monkeypatch, tmp_path):
    from polynexus.gui import figure_window_service as module

    entry = SimpleNamespace(run_root=str(tmp_path), title="Series A")
    document = {
        "objects": [{"data_ref": "source-a"}],
        "data_sources": [
            {
                "id": "source-a",
                "kind": "inline",
                "data": {"x": [1], "y": [2]},
            }
        ],
    }
    monkeypatch.setattr(module, "load_figure_document", lambda _path: document)

    viewer = open_chart_viewer(
        str(tmp_path / "figure.png"),
        {"wrong": [99]},
        entry=entry,
        viewer_factory=_FakeViewer,
    )

    assert viewer.entry is entry
    assert viewer.data_resolution.headers == ("x", "y")
    assert viewer.data_resolution.rows == ((1, 2),)


def test_open_chart_editor_uses_entry_context_and_title():
    entry = SimpleNamespace(
        figure_id="Fig_1_overview",
        title="Series Overview",
        preview_path=r"D:\figures\Fig_1_overview.png",
        primary_path=r"D:\figures\Fig_1_overview.svg",
        editable_path=r"D:\figures\Fig_1_overview.svg",
        state="object_editing",
        document_mode="object",
    )

    editor = open_chart_editor(
        r"D:\figures\Fig_1_overview.svg",
        entry=entry,
        force_static=True,
        editor=None,
        editor_factory=_FakeEditor,
        saved_handler=lambda *_: None,
    )

    assert "Series Overview" in editor.window_title
    assert editor.source_entry is entry
    assert editor.force_static is True
    assert editor.source_figure == r"D:\figures\Fig_1_overview.svg"


def test_open_chart_editor_downgrades_mismatched_generated_document_to_static(tmp_path):
    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    figure_path.write_bytes(b"png")

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="other_figure",
        objects=[],
    )

    entry = SimpleNamespace(
        figure_id="generated",
        title="Generated Figure",
        preview_path=str(figure_path),
        primary_path=str(figure_path),
        editable_path=str(figure_path),
        state="object_editing",
        document_mode="object",
    )

    editor = open_chart_editor(
        str(figure_path),
        entry=entry,
        editor=None,
        editor_factory=_FakeEditor,
        saved_handler=lambda *_: None,
    )

    assert editor.force_static is True
    assert editor.source_entry is entry


def test_open_chart_editor_downgrades_multi_panel_generated_document_to_static(tmp_path):
    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    figure_path.write_bytes(b"png")

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated",
        style={"panels": ["overview", "waterfall"]},
        objects=[],
    )

    entry = SimpleNamespace(
        figure_id="generated",
        title="Generated Figure",
        preview_path=str(figure_path),
        primary_path=str(figure_path),
        editable_path=str(figure_path),
        state="object_editing",
        document_mode="object",
    )

    editor = open_chart_editor(
        str(figure_path),
        entry=entry,
        editor=None,
        editor_factory=_FakeEditor,
        saved_handler=lambda *_: None,
    )

    assert editor.force_static is True
    assert editor.source_entry is entry


def test_open_chart_viewer_and_editor_ignore_blank_paths():
    viewer = _FakeViewer()
    editor = _FakeEditor()

    assert open_chart_viewer("", viewer=viewer) is viewer
    assert viewer.loaded is None

    assert open_chart_editor("", editor=editor) is editor
    assert editor.source_figure == ""


def test_manifest_object_capability_does_not_downgrade_formal_layout(
    ir_definition,
    tmp_path,
):
    FigurePipeline().run(
        output_root=tmp_path,
        run_id="run-1",
        technique="ir",
        definitions=(ir_definition,),
    )
    entry = build_active_manifest_gallery_entries(tmp_path)[0]

    request = resolve_chart_editor_entry(entry.primary_path, entry=entry)

    assert request.force_static is False
    assert request.entry is entry


def test_open_convergence_viewer_handles_success_warning_and_critical_paths():
    class _FakeConvergenceViewer:
        def __init__(self, parent=None):
            self.parent = parent
            self.destroyed = _FakeSignal()
            self.attribute_calls = []
            self.shown = False

        def setAttribute(self, attr):
            self.attribute_calls.append(attr)

        def show(self):
            self.shown = True

    closed = []
    warnings = []
    criticals = []
    calls = []

    viewer = open_convergence_viewer(
        None,
        viewer_factory=lambda parent=None: _FakeConvergenceViewer(parent=parent),
        closed_handler=lambda *_: closed.append("closed"),
        warning_handler=lambda exc: warnings.append(str(exc)),
        critical_handler=lambda exc: criticals.append(str(exc)),
        logger=SimpleNamespace(warning=lambda *args, **kwargs: calls.append((args, kwargs))),
    )

    assert viewer.shown is True
    assert viewer.attribute_calls
    assert len(viewer.destroyed.callbacks) == 1
    assert closed == []
    assert warnings == []
    assert criticals == []
    assert calls == []

    reused = open_convergence_viewer(viewer, viewer_factory=lambda parent=None: None)
    assert reused is viewer

    warning_viewer = open_convergence_viewer(
        None,
        viewer_factory=lambda parent=None: (_ for _ in ()).throw(SystemExit("boom")),
        warning_handler=lambda exc: warnings.append(str(exc)),
        critical_handler=lambda exc: criticals.append(str(exc)),
        logger=SimpleNamespace(warning=lambda *args, **kwargs: calls.append((args, kwargs))),
    )
    assert warning_viewer is None
    assert warnings == ["boom"]

    critical_viewer = open_convergence_viewer(
        None,
        viewer_factory=lambda parent=None: (_ for _ in ()).throw(RuntimeError("broken")),
        warning_handler=lambda exc: warnings.append(str(exc)),
        critical_handler=lambda exc: criticals.append(str(exc)),
        logger=SimpleNamespace(warning=lambda *args, **kwargs: calls.append((args, kwargs))),
    )
    assert critical_viewer is None
    assert criticals == ["broken"]
    assert calls


def test_refresh_saved_figure_in_gallery_refreshes_existing_entry_without_duplication():
    gallery = _FakeGallery([r"D:\figures\old.png"])

    existed = refresh_saved_figure_in_gallery(gallery, r"D:\figures\old.png")

    assert existed is True
    assert gallery.refreshed == [r"D:\figures\old.png"]
    assert gallery.loaded == []
    assert gallery.selected == (r"D:\figures\old.png", False)


def test_refresh_saved_figure_in_gallery_loads_new_figure_when_missing():
    gallery = _FakeGallery([r"D:\figures\old.png"])

    existed = refresh_saved_figure_in_gallery(gallery, r"D:\figures\new.png")

    assert existed is False
    assert gallery.refreshed == []
    assert gallery.loaded == [[r"D:\figures\old.png", r"D:\figures\new.png"]]
    assert gallery.selected == (r"D:\figures\new.png", False)


def test_refresh_saved_figure_in_gallery_regroups_new_path_without_duplication():
    gallery = _FakeGallery(
        [r"D:\figures\temperature_overview.png", r"D:\figures\temperature_overview.svg"]
    )

    existed = refresh_saved_figure_in_gallery(gallery, r"D:\figures\temperature_overview.pdf")

    assert existed is False
    assert gallery.refreshed == []
    assert gallery.loaded == [[
        r"D:\figures\temperature_overview.png",
        r"D:\figures\temperature_overview.svg",
        r"D:\figures\temperature_overview.pdf",
    ]]
    assert gallery.selected == (r"D:\figures\temperature_overview.pdf", False)
