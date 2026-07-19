# Origin Single-Graph Fidelity Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with TDD and verification checkpoints.

**Goal:** Make native OriginPro export render every figure series from its own source in one graph while preserving series names, colors, line widths, labels, and axis scales.

**Architecture:** Keep `OriginProAdapter` responsible for mapping each `OriginPlotSpec.data_ref` to the facade and keep `_OriginProFacade` responsible for Origin workbook/worksheet ownership. The facade will create one workbook with one worksheet per source, one graph reused by all plots, and apply plot/axis presentation after the correct source is selected. COM/LabTalk and package fallback adapters remain unchanged.

**Tech Stack:** Python 3, pandas, optional `originpro`, pytest, Ruff.

---

### Task 1: Lock the source binding and presentation contract with failing tests

**Files:**
- Modify: `tests/test_originpro_adapter.py`

- [x] **Step 1: Add an adapter regression for distinct source references.**

  Extend the fake facade's `add_plot` event to accept `data_ref` and `name`, then create two CSV sources and two `plot_series` objects. Assert the export calls `add_plot` with the matching source IDs in plot order and preserves each style mapping.

- [x] **Step 2: Add facade regressions for worksheet selection and plot styling.**

  Use fake sheets, frames, graph, layer, and plot objects. Assert that adding plots for `source-a` and `source-b` passes the corresponding sheet and column indexes, sets the plot color/width, and sets the Y column long name to the series name. Assert a missing `data_ref` raises a clear `KeyError`.

- [x] **Step 3: Add a facade regression for graph labels.**

  Assert that `configure_figure` sets the graph long name and the X/Y axis titles, then applies the existing linear/log10 scale mapping and rescale.

- [x] **Step 4: Run only the new tests and confirm the expected red failure.**

  Run:

  ```powershell
  python -m pytest tests/test_originpro_adapter.py -q
  ```

  Expected: FAIL because the current facade always uses the last dataframe, does not accept `data_ref`/`name`, and does not apply plot presentation.

### Task 2: Implement per-source worksheets and one styled graph

**Files:**
- Modify: `polynexus/origin/originpro_adapter.py`

- [x] **Step 1: Store the workbook, sheets, and dataframes by source ID.**

  Keep the first worksheet returned by `new_sheet`, obtain its parent workbook through `get_book`, add later worksheets with `book.add_sheet`, and store each sheet/dataframe under `source_id`. `from_csv` must read into the currently selected source sheet and reject an unknown/empty source ID.

- [x] **Step 2: Pass plot source identity and name through the adapter.**

  Call the facade as:

  ```python
  facade.add_plot(
      plot.x_column,
      plot.y_column,
      dict(plot.style),
      data_ref=plot.data_ref,
      name=plot.name,
  )
  ```

  The facade must select the stored sheet/frame for `data_ref`, rather than consulting the last imported frame.

- [x] **Step 3: Apply plot style and legend names.**

  Use the returned Origin `Plot` object when available. Set `plot.color` from a valid document color, apply a positive numeric `line_width` through Origin's `set_cmd("-w ...")` units, and set the source Y column long name to the series name before plotting. Keep unsupported/missing style fields at Origin defaults.

- [x] **Step 4: Configure graph title and axis labels without changing fallback adapters.**

  Add `configure_figure(title, xlabel, ylabel, x_scale, y_scale)`. Set the graph long name when a title exists, set the first layer's X/Y axis titles when labels exist, map `log` to `log10`, and rescale once after all plots and scale changes. Retain `configure_axes` as a compatibility wrapper if tests or callers use it.

- [x] **Step 5: Run the focused adapter tests and confirm green.**

  Run:

  ```powershell
  python -m pytest tests/test_originpro_adapter.py tests/test_origin_mapping.py -q
  ```

  Expected: PASS, including the new per-source, style, label, and axis regressions.

### Task 3: Verify integration and record evidence

**Files:**
- Modify: `docs/agent/tasks/2026-07-19-origin-single-graph-fidelity.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [x] **Step 1: Run ChartEditor and static checks.**

  Run:

  ```powershell
  python -m pytest tests/test_chart_editor.py -q
  python -m ruff check polynexus/origin/originpro_adapter.py tests/test_originpro_adapter.py
  python -m compileall -q polynexus/origin tests/test_originpro_adapter.py
  git diff --check
  ```

- [x] **Step 2: Attempt the repository-prescribed verifier.**

  Run:

  ```powershell
  python scripts/verify.py --task docs/agent/tasks/2026-07-19-origin-single-graph-fidelity.md --changed --types
  ```

  Record the exact result, including the known missing-script outcome if it remains unavailable.

- [x] **Step 3: Perform a real OriginPro smoke export.**

  Use the existing configured Origin installation and the current SAXS waterfall object document. Confirm the result is `success/originpro`, the saved `.opju` contains one graph with five plotted series, each series has its own color/name, and the Y axis is logarithmic. Do not close or kill the user's Origin process.

- [x] **Step 4: Update durable task evidence.**

  Mark only verified acceptance criteria in the task card and update memory with exact commands/results, the real smoke limitation if any, and pre-existing untracked files left untouched.

- [x] **Step 5: Run the repository checkpoint helper with an explicit allowlist.**

  After all verification is complete, run:

  ```powershell
  python scripts/auto_commit.py `
    --message "fix(origin): preserve native multi-series graph fidelity" `
    --files polynexus/origin/originpro_adapter.py tests/test_originpro_adapter.py docs/agent/tasks/2026-07-19-origin-single-graph-fidelity.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md docs/superpowers/plans/2026-07-19-origin-single-graph-fidelity.md
  ```

  The helper must create one atomic local checkpoint and must not push or merge.
