# Editor Responsive Sidebar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep ChartEditor inspector controls usable in a compact sidebar without horizontal clipping.

**Architecture:** Use existing `QFormLayout` pages but enable row wrapping and prohibit horizontal scrollbars. Constrain the object tree to a practical maximum height and replace the annotation batch action strip with a wrapping grid so it cannot force page width.

**Tech Stack:** Python, PySide6, pytest.

---

### Task 1: Define compact inspector regression coverage

**Files:**
- Modify: `D:/PolyNexus/tests/test_chart_editor_workflow.py`

- [ ] Add an offscreen Qt test that shows a generated editor at 900×700, resizes the inspector panel to 280px, and asserts every inspector page has `ScrollBarAlwaysOff` horizontally, each form uses `WrapAllRows`, the object tree maximum height is bounded, and the batch action layout is a grid.
- [ ] Run the new test with `QT_QPA_PLATFORM=offscreen` and the isolated pytest base directory; confirm it fails before implementation.

### Task 2: Reflow the inspector

**Files:**
- Modify: `D:/PolyNexus/polynexus/gui/widgets/chart_editor.py:494-1010`

- [ ] In `make_page`, set `QScrollArea` horizontal-scroll policy to `Qt.ScrollBarAlwaysOff`, set the panel horizontal size policy to ignored/expanding, and set its `QFormLayout` row-wrap policy to `QFormLayout.WrapAllRows`.
- [ ] Store inspector page scroll areas in `self._inspector_scroll_pages` for regression inspection.
- [ ] Limit `_object_list` to a 300px maximum height while retaining its 96px minimum height.
- [ ] Replace the annotation batch `QHBoxLayout` with a three-column `QGridLayout`; add each existing button by row/column, preserve callbacks and object names, and set all columns to stretch equally.
- [ ] Run the compact regression and verify it passes.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `D:/PolyNexus/docs/agent/memory/active-work.md`

- [ ] Run `tests/test_chart_editor_workflow.py`, `tests/test_chart_editor_curve.py`, and `tests/test_chart_editor_context_menu.py` with offscreen Qt.
- [ ] Record the responsive-sidebar behavior and verification evidence.
- [ ] Run `PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt' python scripts/verify.py --changed --types`.
- [ ] Commit with `python scripts/auto_commit.py --message "fix(editor): reflow compact inspector sidebar" --files docs/agent/memory/active-work.md docs/superpowers/plans/2026-07-23-editor-responsive-sidebar.md polynexus/gui/widgets/chart_editor.py tests/test_chart_editor_workflow.py`.
