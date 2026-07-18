# Origin Editor Usability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the Origin editor canvas usable while adding a collapsible Inspector, fully editable Bézier annotations, and robust Origin data-source preparation.

**Architecture:** The `ChartEditor` remains the composition root. A drawer mixin owns only Inspector visibility and splitter geometry, while the existing edit session remains the only source of persisted object state. `curve` becomes a canonical figure object rendered by both Qt and Matplotlib. Origin adapters consume a shared source-preparation result rather than resolving and materializing input differently in each adapter.

**Tech Stack:** Python 3, PySide6, Matplotlib QtAgg, Pytest, existing figure edit session/commands, Origin adapter chain.

---

## File structure

- Create: `polynexus/gui/widgets/chart_editor_inspector_drawer_mixin.py` — Inspector drawer visibility, remembered width, selection-triggered reveal policy.
- Modify: `polynexus/gui/widgets/chart_editor.py` — compose the drawer and vertical creation toolbar; remove fixed inspector sizing assumptions.
- Modify: `polynexus/gui/widgets/chart_editor_layout_mixin.py` — add the Curve action and the Inspector toggle in the header, preserving toolbar synchronization.
- Modify: `polynexus/gui/widgets/chart_editor_edit_session_mixin.py` and `polynexus/gui/widgets/chart_editor_generated_interaction_mixin.py` — route the curve tool through the existing edit session.
- Modify: `polynexus/core/figure_objects.py`, `polynexus/core/figure_edit_capabilities.py`, `polynexus/core/figure_document.py` — recognize and normalize canonical curve geometry and capabilities.
- Modify: `polynexus/gui/widgets/annotation_canvas.py`, `polynexus/gui/widgets/annotation_render_adapter.py`, `polynexus/gui/widgets/chart_editor_generated_document_mixin.py`, `polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py`, and `polynexus/gui/figure_render_adapter.py` — render, select, and edit one curve representation in static and generated modes.
- Create: `polynexus/origin/source_preparation.py` — resolve, validate, and materialize Origin source CSVs with structured failures.
- Modify: `polynexus/origin/path_resolution.py` — expose ordered source candidates so diagnostics and resolution use the same roots.
- Modify: `polynexus/origin/package_exporter.py`, `polynexus/origin/originpro_adapter.py`, `polynexus/origin/com_labtalk_adapter.py`, and `polynexus/origin/mapping.py` — reuse prepared sources and preserve/warn about curve export.
- Modify: `polynexus/gui/i18n.py` — Curve and Inspector drawer labels in the existing translation catalogue.
- Modify: focused existing tests under `tests/test_chart_editor_layout.py`, `tests/test_annotation_canvas.py`, `tests/test_chart_editor_generated_interaction_mixin.py`, `tests/test_chart_editor_generated_document_mixin.py`, `tests/test_origin_mapping.py`, `tests/test_origin_package_exporter.py`, `tests/test_originpro_adapter.py`, `tests/test_origin_com_adapter.py`, and `tests/test_chart_editor_origin_export.py`.

### Task 1: Establish the structured-task baseline

**Files:**
- Create: `docs/agent/tasks/2026-07-18-origin-editor-usability.md`
- Create: `docs/superpowers/plans/2026-07-18-origin-editor-usability.md`

- [ ] **Step 1: Verify the task card names every requested boundary and the required verification commands**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-18-origin-editor-usability.md --changed --types
```

Expected: the task-aware verifier accepts the card and reports the documentation-only baseline.

- [ ] **Step 2: Commit the approved task baseline**

```powershell
git add docs/agent/tasks/2026-07-18-origin-editor-usability.md docs/superpowers/plans/2026-07-18-origin-editor-usability.md
git commit -m "docs: plan Origin editor usability work"
```

Expected: one documentation commit records the approved scope before product code changes.

### Task 2: Make the Inspector a drawer without changing screen-rendered figure size

**Files:**
- Create: `polynexus/gui/widgets/chart_editor_inspector_drawer_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/widgets/chart_editor_layout_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_document_mixin.py`
- Modify: `polynexus/gui/i18n.py`
- Test: `tests/test_chart_editor_layout.py`

- [ ] **Step 1: Write failing drawer and canvas-size regression tests**

```python
def test_chart_editor_drawer_closes_and_restores_left_splitter_width(qtbot):
    editor = ChartEditor()
    qtbot.addWidget(editor)
    editor.resize(1100, 720)
    editor.show()
    qtbot.waitUntil(lambda: editor._canvas.width() > 300)

    editor._set_inspector_collapsed(True, manual=True)
    collapsed_width = editor._canvas.width()
    assert editor._inspector_panel.isHidden()

    editor._set_inspector_collapsed(False)
    assert editor._canvas.width() < collapsed_width
    assert editor._editor_splitter.sizes()[1] >= editor._inspector_minimum_width


def test_figure_size_change_does_not_reduce_visible_canvas_geometry(qtbot):
    editor = ChartEditor()
    qtbot.addWidget(editor)
    editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))
    editor.resize(1100, 720)
    editor.show()
    qtbot.waitUntil(lambda: editor._canvas.width() > 300)
    before = editor._canvas.size()

    editor._figsize_cb.setCurrentText("Small (4in)")
    qtbot.waitUntil(lambda: editor._canvas.width() > 300)

    assert editor._canvas.width() == before.width()
    assert editor._canvas.height() == before.height()
```

- [ ] **Step 2: Run the new tests to confirm the current fixed-width/screen-size behavior fails them**

Run:

```powershell
python -m pytest tests/test_chart_editor_layout.py -q
```

Expected: the drawer API is absent and the figure-size assertion exposes the fixed physical-size render behavior.

- [ ] **Step 3: Add an isolated drawer controller**

```python
class ChartEditorInspectorDrawerMixin:
    _inspector_minimum_width = 280

    def _set_inspector_collapsed(self, collapsed: bool, *, manual: bool = False) -> None:
        self._inspector_closed_manually = bool(manual and collapsed)
        if collapsed:
            self._inspector_last_width = max(
                self._inspector_minimum_width, self._editor_splitter.sizes()[1]
            )
            self._inspector_panel.hide()
            self._editor_splitter.setSizes([max(1, self._editor_splitter.width()), 0])
            return
        self._inspector_panel.show()
        self._editor_splitter.setSizes([
            max(1, self._editor_splitter.width() - self._inspector_last_width),
            self._inspector_last_width,
        ])

    def _reveal_inspector_for_selection(self) -> None:
        if not self._inspector_closed_manually:
            self._set_inspector_collapsed(False)
```

Compose the mixin before `ChartEditorLayoutMixin`; wrap `_inspector_tabs` in `_inspector_panel`; add a header toggle that uses the existing translation system; build the creation toolbar beside the shared canvas host with `Qt.Vertical`; and remove the header copy of that toolbar.

- [ ] **Step 4: Keep logical/export figure dimensions out of the live widget resize path**

```python
def _apply_formal_editor_style(self, figure, artist_map):
    if figure is None or not hasattr(self, "_bg_color"):
        return
    figure.set_facecolor(self._bg_color)
    if not getattr(self, "_rendering_for_editor_viewport", False):
        figure.set_size_inches(*self._fig_size, forward=False)
```

Set `_rendering_for_editor_viewport` only around the generated editor-view render and leave export/save renderers on the persisted `self._fig_size` path. Wire object-selection callbacks to `_reveal_inspector_for_selection()` and preserve manual close state.

- [ ] **Step 5: Run the focused layout suite**

Run:

```powershell
python -m pytest tests/test_chart_editor_layout.py tests/test_chart_editor_style_context.py tests/test_chart_editor_generated_document_mixin.py -q
```

Expected: PASS; existing style hydration remains intact while the visible canvas no longer follows logical figure inches.

- [ ] **Step 6: Commit the drawer slice**

```powershell
git add polynexus/gui/widgets/chart_editor_inspector_drawer_mixin.py polynexus/gui/widgets/chart_editor.py polynexus/gui/widgets/chart_editor_layout_mixin.py polynexus/gui/widgets/chart_editor_generated_document_mixin.py polynexus/gui/i18n.py tests/test_chart_editor_layout.py
git commit -m "fix: keep Origin editor canvas stable"
```

### Task 3: Add canonical Bézier curves and expose all creation tools on the canvas

**Files:**
- Modify: `polynexus/core/figure_objects.py`
- Modify: `polynexus/core/figure_edit_capabilities.py`
- Modify: `polynexus/core/figure_document.py`
- Modify: `polynexus/gui/widgets/chart_editor_layout_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_edit_session_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_interaction_mixin.py`
- Modify: `polynexus/gui/widgets/annotation_canvas.py`
- Modify: `polynexus/gui/widgets/annotation_render_adapter.py`
- Test: `tests/test_annotation_canvas.py`
- Test: `tests/test_chart_editor_generated_interaction_mixin.py`

- [ ] **Step 1: Write failing canonical-object and creation tests**

```python
def test_normalize_figure_object_preserves_bezier_control_geometry():
    curve = normalize_figure_object(
        {"type": "curve", "x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.7,
         "control_x": 0.45, "control_y": 0.05}
    )
    assert curve["type"] == "curve"
    assert curve["bounds"]["control_x"] == 0.45
    assert capabilities_for(curve).geometry is True


def test_annotation_canvas_creates_and_persists_bezier_curve(qtbot, image_path):
    canvas = AnnotationCanvas()
    qtbot.addWidget(canvas)
    assert canvas.load_image(str(image_path))
    curve_id = canvas.add_curve_annotation(20, 80, 180, 80, 100, 20)
    curve = canvas.selected_annotation()
    assert curve["id"] == curve_id
    assert curve["type"] == "curve"
    assert curve["control_y"] < curve["y1"]
```

- [ ] **Step 2: Run the tests to confirm `curve` is currently rejected or absent**

Run:

```powershell
python -m pytest tests/test_annotation_canvas.py tests/test_chart_editor_generated_interaction_mixin.py tests/test_origin_mapping.py -q
```

Expected: FAIL because no canonical `curve` type or curve creation method exists.

- [ ] **Step 3: Define the object contract and capability once**

```python
KNOWN_FIGURE_OBJECT_TYPES.add("curve")
GEOMETRY_KEYS = (
    "x", "y", "width", "height", "x1", "y1", "x2", "y2", "control_x", "control_y"
)
DEFAULT_OBJECT_NAMES["curve"] = "Curve"

elif object_type == "curve":
    base.update(
        style=True, color=True, line_width=True, line_style=True,
        geometry=True, deletable=True, reorderable=True,
    )
```

Use the same normalized `x1`, `y1`, `x2`, `y2`, `control_x`, and `control_y` keys in static and generated paths; do not introduce a second curve-only persistence format.

- [ ] **Step 4: Render and edit curves in the static annotation path**

```python
def add_curve_annotation(self, x1, y1, x2, y2, control_x, control_y) -> str:
    return self._add_curve_annotation(
        "curve", x1, y1, x2, y2, control_x, control_y
    )

def _curve_path(self, annotation: dict) -> QPainterPath:
    path = QPainterPath(QPointF(self._denormalize_x(annotation["x1"]), self._denormalize_y(annotation["y1"])))
    path.quadTo(
        QPointF(self._denormalize_x(annotation["control_x"]), self._denormalize_y(annotation["control_y"])),
        QPointF(self._denormalize_x(annotation["x2"]), self._denormalize_y(annotation["y2"])),
    )
    return path
```

Make the control handle selectable and draggable, emit `object_edit_requested` with only the changed geometry, and update the object list/Inspector from the existing edit session. Add direct text focus after text placement and leave line, arrow, and rectangle creation on their existing drag path.

- [ ] **Step 5: Render and edit curves in generated-document mode**

```python
from matplotlib.path import Path
from matplotlib.patches import PathPatch

path = Path(
    [(x1, y1), (control_x, control_y), (x2, y2)],
    [Path.MOVETO, Path.CURVE3, Path.CURVE3],
)
patch = PathPatch(path, fill=False, edgecolor=color, linewidth=line_width, linestyle=line_style)
ax.add_patch(patch)
return [patch]
```

Add `curve` to the toolbar and generated tool allow-lists. On release, create one `AddObjectCommand` payload with the midpoint as the initial control point. Extend generated selection handles and drag execution to update endpoint or control geometry through `UpdateGeometryCommand`; select the created curve and return the active tool to `select`.

- [ ] **Step 6: Run static and generated curve regressions**

Run:

```powershell
python -m pytest tests/test_annotation_canvas.py tests/test_chart_editor_generated_interaction_mixin.py tests/test_chart_editor_generated_document_mixin.py tests/test_chart_editor_generated_geometry_mixin.py tests/test_chart_editor.py -q
```

Expected: PASS; curve creation, control-point editing, save/reload, selection, and existing line behavior all pass.

- [ ] **Step 7: Commit the annotation slice**

```powershell
git add polynexus/core/figure_objects.py polynexus/core/figure_edit_capabilities.py polynexus/core/figure_document.py polynexus/gui/widgets/chart_editor_layout_mixin.py polynexus/gui/widgets/chart_editor_edit_session_mixin.py polynexus/gui/widgets/chart_editor_generated_interaction_mixin.py polynexus/gui/widgets/annotation_canvas.py polynexus/gui/widgets/annotation_render_adapter.py polynexus/gui/widgets/chart_editor_generated_document_mixin.py polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py polynexus/gui/figure_render_adapter.py polynexus/gui/i18n.py tests/test_annotation_canvas.py tests/test_chart_editor_generated_interaction_mixin.py tests/test_chart_editor_generated_document_mixin.py tests/test_chart_editor_generated_geometry_mixin.py
git commit -m "feat: add editable Origin curve annotations"
```

### Task 4: Prepare Origin sources once while preserving declared-file provenance

**Files:**
- Create: `polynexus/origin/source_preparation.py`
- Modify: `polynexus/origin/path_resolution.py`
- Modify: `polynexus/origin/package_exporter.py`
- Modify: `polynexus/origin/originpro_adapter.py`
- Modify: `polynexus/origin/com_labtalk_adapter.py`
- Modify: `polynexus/origin/mapping.py`
- Modify: `polynexus/gui/widgets/chart_editor_origin_mixin.py`
- Test: `tests/test_origin_package_exporter.py`
- Test: `tests/test_originpro_adapter.py`
- Test: `tests/test_origin_com_adapter.py`
- Test: `tests/test_origin_mapping.py`
- Test: `tests/test_chart_editor_origin_export.py`

- [ ] **Step 1: Write failing pure-inline and declared-path diagnostic tests**

```python
def test_package_exporter_materializes_values_when_no_path_is_declared(tmp_path):
    request = ExportRequest(
        document={"data_sources": [{
            "id": "inline-source",
            "columns": [{"name": "x"}, {"name": "y"}],
            "values": {"x": [1, 2], "y": [3, 4]},
        }]},
        output_root=tmp_path / "out", mode="package",
    )
    result = PackageExporter().export(request)
    assert result.success
    assert (result.artifacts[0] / "data/inline-source.csv").is_file()


def test_declared_missing_source_does_not_fallback_to_inline_values(tmp_path):
    result = PackageExporter().export(
        ExportRequest(document={"data_sources": [{
            "id": "bad", "path": "lost.csv", "values": {"x": [1], "y": [2]},
        }]}, output_root=tmp_path / "out")
    )
    assert result.status == "failed"
    assert "bad" in result.message
    assert "lost.csv" in result.message
    assert "attempted roots" in result.message
```

- [ ] **Step 2: Run the export tests to confirm current adapters do not share strict preparation**

Run:

```powershell
python -m pytest tests/test_origin_package_exporter.py tests/test_originpro_adapter.py tests/test_origin_com_adapter.py tests/test_chart_editor_origin_export.py -q
```

Expected: FAIL because all adapters do not yet prepare a non-empty missing `path` consistently or report the ordered attempted roots.

- [ ] **Step 3: Create one source-preparation contract**

```python
from collections.abc import Sequence

@dataclass(frozen=True)
class PreparedOriginSource:
    source_id: str
    path: Path
    materialized: bool

class OriginSourcePreparationError(FileNotFoundError):
    def __init__(self, source_id: str, raw_path: str, attempted_roots: Sequence[Path]):
        super().__init__(
            f"data source '{source_id}' is unavailable: {raw_path}; "
            f"attempted roots: {', '.join(map(str, attempted_roots))}"
        )

def prepare_origin_sources(sources, request, data_root: Path) -> Sequence[PreparedOriginSource]:
    data_root.mkdir(parents=True, exist_ok=True)
    prepared: list[PreparedOriginSource] = []
    for source in sources:
        source_id = str(source.source_id).strip()
        raw_path = str(source.path).strip()
        candidates = source_path_candidates(raw_path, request) if raw_path else ()
        resolved = resolve_source_path(raw_path, request) if raw_path else None
        target = data_root / f"{source_id}.csv"
        if raw_path:
            if resolved is not None and resolved.is_file():
                if resolved.resolve() != target.resolve():
                    shutil.copy2(resolved, target)
                prepared.append(PreparedOriginSource(source_id, target, False))
                continue
            raise OriginSourcePreparationError(source_id, raw_path, candidates)
        if source.values:
            _write_source_values(target, source.columns, source.values)
            prepared.append(PreparedOriginSource(source_id, target, True))
            continue
        raise OriginSourcePreparationError(source_id, raw_path, candidates)
    return tuple(prepared)
```

Add `source_path_candidates(raw_path, request)` in `path_resolution.py`; it returns the existing ordered candidates for `source_root`, figure-file directories, and compatibility working directory. A non-empty `raw_path` always has precedence and failure is terminal for that source. `_write_source_values()` is only used for a source with no path and writes the declared column order (or the `values` key order when no columns are declared). `data_root` must be inside the caller's approved staging or temporary directory.

- [ ] **Step 4: Route every adapter through the same preparation path**

```python
with TemporaryDirectory(prefix="polynexus-origin-") as temporary:
    prepared = prepare_origin_sources(model.sources, request, Path(temporary))
    for source in prepared:
        facade.from_csv(source.path)
```

`PackageExporter` passes its staging `data/` directory so the prepared CSVs become final bundle assets. Direct adapters use a temporary directory only for the duration of synchronous import. Add `curve` to Origin mapping as a preserved package object plus an explicit direct-adapter warning when native curve creation is unavailable.

- [ ] **Step 5: Surface the structured failure without changing GUI dispatch**

```python
if result.status == "failed" and result.message:
    message = f"{tr('EDITOR_EXPORT_ORIGIN_FAILED')}: {result.message}"
```

Keep `ChartEditorOriginMixin` as an `ExportResult` consumer; it must not perform path resolution or technique-specific source decisions.

- [ ] **Step 6: Run the focused Origin suites**

Run:

```powershell
python -m pytest tests/test_origin_mapping.py tests/test_origin_package_exporter.py tests/test_originpro_adapter.py tests/test_origin_com_adapter.py tests/test_origin_contracts.py tests/test_chart_editor_origin_export.py -q
```

Expected: PASS; existing run-root paths keep working, no-path inline sources work for package/direct adapters, and a declared stale path fails with the source and attempted roots.

- [ ] **Step 7: Commit the Origin source slice**

```powershell
git add polynexus/origin/source_preparation.py polynexus/origin/path_resolution.py polynexus/origin/package_exporter.py polynexus/origin/originpro_adapter.py polynexus/origin/com_labtalk_adapter.py polynexus/origin/mapping.py polynexus/gui/widgets/chart_editor_origin_mixin.py tests/test_origin_mapping.py tests/test_origin_package_exporter.py tests/test_originpro_adapter.py tests/test_origin_com_adapter.py tests/test_chart_editor_origin_export.py
git commit -m "fix: prepare Origin export data sources consistently"
```

### Task 5: Verify the cumulative change and record durable task evidence

**Files:**
- Modify: `docs/agent/tasks/2026-07-18-origin-editor-usability.md`
- Modify: `docs/agent/memory/active-work.md`
- Create: `docs/acceptance/2026-07-18-origin-editor-usability.md`

- [ ] **Step 1: Run the complete focused editor and Origin regression matrix**

Run:

```powershell
python -m pytest tests/test_chart_editor_layout.py tests/test_chart_editor.py tests/test_annotation_canvas.py tests/test_chart_editor_generated_interaction_mixin.py tests/test_chart_editor_generated_document_mixin.py tests/test_chart_editor_generated_geometry_mixin.py tests/test_origin_mapping.py tests/test_origin_package_exporter.py tests/test_originpro_adapter.py tests/test_origin_com_adapter.py tests/test_origin_contracts.py tests/test_chart_editor_origin_export.py -q
```

Expected: PASS with no skipped test masking the Qt or source-preparation behavior.

- [ ] **Step 2: Run project verification for the structured task and the branch boundary**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-18-origin-editor-usability.md --changed --types
python scripts/verify.py --changed --types --full --boundary --base origin/main
```

Expected: both commands report the actual changed-file and integration-boundary result without unrelated workspace files.

- [ ] **Step 3: Perform the manual acceptance pass and record exact evidence**

Use the desktop editor to verify these actions in order: open a generated figure; collapse and re-open Inspector; switch to Style and change figure size; create and reshape a curve; create/edit a text object; export a run-relative data-source figure; export a pathless inline-data source; confirm that a document with a declared missing path and inline values fails without fallback; export a document with neither source nor values. Record observed result, command output, and any limitation in `docs/acceptance/2026-07-18-origin-editor-usability.md`.

- [ ] **Step 4: Update the task card and durable active-work memory**

Change the task card status to `implementation complete`, list each verification command and result, and append a concise completed-work entry to `docs/agent/memory/active-work.md`. Do not add raw logs, data files, or source-code copies to memory.

- [ ] **Step 5: Commit verification evidence**

```powershell
git add docs/agent/tasks/2026-07-18-origin-editor-usability.md docs/agent/memory/active-work.md docs/acceptance/2026-07-18-origin-editor-usability.md
git commit -m "docs: record Origin editor usability verification"
```

## Plan self-review

- Spec coverage: Tasks 2 through 4 cover the confirmed drawer, screen-size, tool, curve, persistence, relative-path, inline-data, and error-feedback requirements; Task 5 covers the required focused and integration verification.
- Boundary coverage: `ChartEditor` remains a view/controller; persistent changes use the edit session and figure document; Origin path and data handling stays in the Origin service boundary.
- Compatibility coverage: existing static annotations, generated figure objects, run-relative resolution, and no-Origin package export each have explicit regression runs.
- Placeholder scan: this plan contains no unresolved design decisions or deferred implementation placeholders.
