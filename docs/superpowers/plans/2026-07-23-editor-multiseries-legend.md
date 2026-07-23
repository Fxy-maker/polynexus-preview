# Editor Multi-Series Legend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show an editable compact legend with unmodified sample names by
default for object-mode charts that contain multiple visible data series.

**Architecture:** Keep the object document as the sole source of truth. The
object store decides whether a missing legend should be materialized, while the
existing generated-document renderer continues to use each `plot_series.name`
as its Matplotlib label and applies the persisted legend geometry. A newly
created legend contains only presentation defaults; later rename, hide, and
drag actions continue through the existing object and command paths.

**Tech Stack:** Python 3.12, PySide6, Matplotlib, pytest.

---

## File map

- `polynexus/core/figure_object_store.py` — materializes an automatic legend
  only for two or more named, visible plot-series objects and supplies its
  stable presentation defaults.
- `polynexus/gui/widgets/chart_editor_generated_document_mixin.py` — consumes
  the automatic `ncol` default when rendering the existing Matplotlib legend.
- `tests/test_figure_object_store.py` — unit coverage for object-document
  eligibility and preservation of explicit legend state.
- `tests/test_chart_editor.py` — offscreen GUI coverage for rendered sample
  names, rename synchronization, and compact multi-series layout.

### Task 1: Define automatic-legend eligibility in the object store

**Files:**

- Modify: `tests/test_figure_object_store.py:130-196`
- Modify: `polynexus/core/figure_object_store.py:109-164`

- [ ] **Step 1: Write the failing unit tests**

  Replace the one-named-series expectation with a two-named-visible-series
  document and add a one-series document. Assert that the two-series document
  gains exactly one legend with default style, while the one-series document
  remains unchanged. Add an existing invisible legend and assert it is neither
  replaced nor changed.

  ```python
  assert FigureObjectStore(two_series).ensure_legend_object() is True
  assert two_series["objects"][-1]["style"] == {
      "loc": "upper right", "ncol": 1,
  }
  assert FigureObjectStore(one_series).ensure_legend_object() is False
  assert FigureObjectStore(explicit_hidden).ensure_legend_object() is False
  assert explicit_hidden["objects"][-1]["visible"] is False
  ```

- [ ] **Step 2: Run the unit tests to verify they fail**

  Run:

  ```powershell
  $env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
  python -m pytest tests/test_figure_object_store.py -q
  ```

  Expected: failure because the current store creates a legend for one named
  series and emits an empty style dictionary.

- [ ] **Step 3: Implement the minimal store change**

  Replace the lifecycle-panel `show_legend` gate with a count of named visible
  `plot_series` objects. Leave an existing legend untouched. When the count is
  at least two, append the existing legend schema with `style` defaults of
  `{"loc": "upper right", "ncol": 2 if series_count > 3 else 1}`. Retain
  `panel_id` when a single lifecycle panel exists, but do not use its provider
  default as a user opt-out.

  ```python
  named_visible_series = [
      obj for obj in objects
      if isinstance(obj, dict)
      and obj.get("type") == "plot_series"
      and obj.get("visible", True) is not False
      and obj.get("deleted") is not True
      and str(obj.get("name", "") or "").strip()
  ]
  if len(named_visible_series) < 2:
      return False
  ```

- [ ] **Step 4: Run the object-store unit tests to verify they pass**

  Run the command from Step 2.

  Expected: all `tests/test_figure_object_store.py` tests pass.

- [ ] **Step 5: Commit the atomic core/test checkpoint**

  ```powershell
  python scripts/auto_commit.py `
    --message "fix(editor): default legends for multi-series figures" `
    --files polynexus/core/figure_object_store.py tests/test_figure_object_store.py
  ```

### Task 2: Render the compact persisted legend and prove name synchronization

**Files:**

- Modify: `tests/test_chart_editor.py:8026-8094`
- Modify: `polynexus/gui/widgets/chart_editor_generated_document_mixin.py:953-989`

- [ ] **Step 1: Write failing offscreen editor regressions**

  Create a five-series figure named `PA6-250-170-S_0_00000` through
  `PA6-250-220-S_0_00000`, without a legend object. Open it through
  `ChartEditor`, assert that the rendered legend text exactly matches these
  names and that its `_ncols` value is `2`. Rename one series through the
  existing name control/update action, then assert the next rendered legend
  includes only the revised sample name.

  ```python
  legend = editor._figure.axes[0].get_legend()
  assert [text.get_text() for text in legend.get_texts()] == sample_names
  assert legend._ncols == 2
  editor._annotation_text_edit.setText("PA6-250-195-S-revised")
  editor._on_annotation_update_text()
  assert "PA6-250-195-S-revised" in [
      text.get_text() for text in editor._figure.axes[0].get_legend().get_texts()
  ]
  ```

- [ ] **Step 2: Run the new offscreen regression to verify it fails**

  Run:

  ```powershell
  $env:QT_QPA_PLATFORM='offscreen'
  $env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
  python -m pytest tests/test_chart_editor.py -k "multiseries_legend" -q
  ```

  Expected: failure because current rendering does not apply the persisted
  `ncol` default.

- [ ] **Step 3: Implement the minimal renderer change**

  In `_apply_generated_document_axes_style`, calculate `ncol` from the legend
  style and pass it to both existing `ax.legend(...)` calls. Use the already
  rendered handles to determine the fallback for legacy documents.

  ```python
  ncol = int(legend_style.get("ncol") or (2 if len(handles) > 3 else 1))
  legend_kwargs = {
      "fontsize": self._tick_size,
      "frameon": False,
      "ncol": ncol,
  }
  if anchor_x is not None and anchor_y is not None:
      ax.legend(
          loc=str(legend_style.get("loc", "") or "upper left"),
          bbox_to_anchor=(float(anchor_x), float(anchor_y)),
          bbox_transform=ax.transAxes,
          **legend_kwargs,
      )
  else:
      ax.legend(**legend_kwargs)
  ```

- [ ] **Step 4: Run focused GUI and object-store coverage to verify it passes**

  Run:

  ```powershell
  $env:QT_QPA_PLATFORM='offscreen'
  $env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
  python -m pytest tests/test_figure_object_store.py tests/test_chart_editor.py -k "legend or figure_object_store" -q
  ```

  Expected: all selected tests pass, with only known Matplotlib layout warnings
  if emitted by the existing suite.

- [ ] **Step 5: Commit the atomic renderer/test checkpoint**

  ```powershell
  python scripts/auto_commit.py `
    --message "fix(editor): render compact sample-name legends" `
    --files polynexus/gui/widgets/chart_editor_generated_document_mixin.py tests/test_chart_editor.py
  ```

### Task 3: Verify the task and record durable state

**Files:**

- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Run the complete focused matrix**

  ```powershell
  $env:QT_QPA_PLATFORM='offscreen'
  $env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
  python -m pytest tests/test_figure_object_store.py tests/test_chart_editor.py -q
  ```

  Expected: all tests pass; record any pre-existing Qt/Matplotlib warning
  separately from failures.

- [ ] **Step 2: Run the repository gate**

  ```powershell
  $env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
  python scripts/verify.py --changed --types
  ```

  Expected: exit code 0, including the memory check, compile/lint/type checks
  selected for changed files, quality gate, and whitespace check.

- [ ] **Step 3: Update active-work memory with exact evidence**

  Add the commit hashes, focused test count, default verifier result, and the
  unchanged limitation that user-provided explicit legend position/visibility
  is preserved.

- [ ] **Step 4: Commit the durable-state update**

  ```powershell
  python scripts/auto_commit.py `
    --message "docs(editor): record multi-series legend verification" `
    --files docs/agent/memory/active-work.md
  ```
