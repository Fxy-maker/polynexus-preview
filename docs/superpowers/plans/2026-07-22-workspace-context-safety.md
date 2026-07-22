# Workspace Context Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the active technique, submodule, source, run, and result ownership explicit so switching context cannot present an unrelated result or figure as current.

**Architecture:** Add a Qt-independent immutable `WorkspaceContext` value object, then let `MainWindow` maintain one current snapshot plus per-result snapshots. Existing widgets continue to render through their current mixins; the workspace mixin becomes the projection boundary that updates context labels, stale-result messaging, and gallery/editor guards. No scientific or figure-document schema changes are required.

**Tech Stack:** Python dataclasses/enums, PySide6 labels and signals, existing MainWindow mixins, pytest/pytest-qt-compatible offscreen tests, repository verifier.

---

## File map

- Create: `polynexus/gui/workspace_context.py` — immutable context and result-status contract with no Qt imports.
- Create: `tests/test_workspace_context.py` — pure context identity/status regression tests.
- Modify: `polynexus/gui/main_window.py:1330-1385` — initialize context snapshots while preserving legacy fields.
- Modify: `polynexus/gui/main_window_workspace_mixin.py` — build context snapshots, format context summaries, and project stale state to the existing header/result/gallery surfaces.
- Modify: `polynexus/gui/main_window_navigation_mixin.py` — mark context changes and clear only the active preview pointer when the user changes technique/submodule.
- Modify: `polynexus/gui/main_window_history_mixin.py:340-430,526-625` — record the persisted run id and result context for fresh and restored history runs.
- Modify: `polynexus/gui/main_window_run_mixin.py:400-475` — record completed/error/batch result context at the publication boundary.
- Modify: `polynexus/gui/main_window_results_mixin.py:20-130,200-330` — expose a visible stale-context banner and prevent “current result” helpers from reading another context.
- Modify: `polynexus/gui/main_window_figure_mixin.py:15-95` — prevent gallery/viewer/editor routes from silently binding raw data from another context.
- Modify: `polynexus/gui/main_window_retranslate_mixin.py` — retranslate the new context/stale labels without allowing one optional widget failure to stop the group.
- Modify: `polynexus/gui/i18n.py` — add Chinese/English strings for context summary, stale result, and source/run labels.
- Modify: `tests/test_main_window_workspace_mixin.py` — test context projection with a Qt-free fake window.
- Modify: `tests/test_main_window_results_mixin.py` — test stale result gating and visible banner state.
- Modify: `tests/test_main_window_figure_mixin.py` — test stale gallery/editor/viewer guards.
- Modify: `tests/test_main_window_history_mixin.py` and `tests/test_main_window_run_mixin.py` — test context capture at completion and restore boundaries.

## Task 1: Define the immutable context contract

**Files:**
- Create: `polynexus/gui/workspace_context.py`
- Test: `tests/test_workspace_context.py`

- [ ] **Step 1: Write failing identity and status tests.**

Add tests covering normalization, context identity, status transitions, and
staleness. The expected public contract is:

```python
from polynexus.gui.workspace_context import (
    WorkspaceContext,
    WorkspaceResultStatus,
)


def test_context_normalizes_identity_fields_and_builds_stable_key():
    context = WorkspaceContext(
        technique=" SAXS ",
        submodule=" saxs.temperature ",
        source_path="D:/run/sample.edf",
        input_mode=" sequence ",
        output_dir="D:/run/polynexus_output",
    )

    assert context.technique == "saxs"
    assert context.submodule == "saxs.temperature"
    assert context.input_mode == "sequence"
    assert context.identity_key == (
        "saxs",
        "saxs.temperature",
        "d:/run/sample.edf",
        "sequence",
        "d:/run/polynexus_output",
    )


def test_result_context_is_current_only_for_same_identity_and_run():
    active = WorkspaceContext(
        technique="saxs",
        source_path="D:/run/sample.edf",
        output_dir="D:/run/polynexus_output",
        run_id="run-1",
        result_status=WorkspaceResultStatus.COMPLETE,
    )
    same = active.with_result(run_id="run-1")
    other_run = active.with_result(run_id="run-2")
    other_source = active.with_source("D:/run/other.edf")

    assert active.result_matches(same)
    assert not active.result_matches(other_run)
    assert not active.result_matches(other_source)
    assert other_run.result_status is WorkspaceResultStatus.STALE


def test_empty_and_cancelled_contexts_have_explicit_status():
    assert WorkspaceContext.empty().result_status is WorkspaceResultStatus.EMPTY
    cancelled = WorkspaceContext.empty().with_result(
        run_id="run-cancelled",
        result_status=WorkspaceResultStatus.CANCELLED,
    )
    assert cancelled.result_status is WorkspaceResultStatus.CANCELLED
```

- [ ] **Step 2: Run the pure tests and verify they fail for the missing contract.**

Run:

```powershell
python -m pytest tests/test_workspace_context.py -q
```

Expected: collection fails because `polynexus.gui.workspace_context` does not
exist.

- [ ] **Step 3: Implement the minimal immutable contract.**

Implement `WorkspaceResultStatus` with `EMPTY`, `CONFIGURED`, `RUNNING`,
`COMPLETE`, `FAILED`, `CANCELLED`, and `STALE`. Implement frozen
`WorkspaceContext` with normalized string fields, `identity_key`, `empty()`,
`with_result()`, `with_source()`, and `result_matches()`. `result_matches()`
must require equal identity keys, a non-empty equal run id, and a complete
result status; it must never compare result payloads.

- [ ] **Step 4: Run the pure tests.**

Run:

```powershell
python -m pytest tests/test_workspace_context.py -q
```

Expected: all context tests pass.

- [ ] **Step 5: Commit the isolated contract.**

```powershell
python scripts/auto_commit.py --message "feat(gui): add workspace context contract" --files polynexus/gui/workspace_context.py tests/test_workspace_context.py
```

## Task 2: Project context into MainWindow state and labels

**Files:**
- Modify: `polynexus/gui/main_window.py`
- Modify: `polynexus/gui/main_window_workspace_mixin.py`
- Modify: `polynexus/gui/main_window_navigation_mixin.py`
- Modify: `polynexus/gui/i18n.py`
- Test: `tests/test_main_window_workspace_mixin.py`

- [ ] **Step 1: Add failing projection tests.**

Use a Qt-free fake object with the existing `_update_workspace_context()`
dependencies. Assert that it stores a `WorkspaceContext`, normalizes source
identity, and writes a summary containing technique, submodule, source, and
run id. Assert that changing technique produces a new identity and does not
reuse the previous run id.

```python
def test_workspace_context_projection_includes_run_identity():
    window = FakeWorkspaceWindow(
        technique="saxs",
        submodule="saxs.temperature",
        filepath="D:/run/sample.edf",
        output_dir="D:/run/polynexus_output",
        run_id="run-42",
    )

    window._update_workspace_context()

    assert window._workspace_context.run_id == "run-42"
    assert "saxs" in window._workspace_context_summary.text().lower()
    assert "run-42" in window._workspace_context_summary.text()


def test_switching_technique_marks_previous_result_as_stale():
    window = FakeWorkspaceWindow(technique="saxs", run_id="run-1")
    window._record_result_context()
    window._current_technique = "waxs"

    window._update_workspace_context()

    assert window._result_context_is_current("saxs") is False
    assert window._workspace_context.technique == "waxs"
```

- [ ] **Step 2: Run the projection tests to verify the missing behavior.**

```powershell
python -m pytest tests/test_main_window_workspace_mixin.py -q
```

Expected: the new assertions fail because no context snapshot/result registry
or context summary widget exists.

- [ ] **Step 3: Add context state without deleting legacy fields.**

Initialize `_workspace_context` and `_result_contexts` in `MainWindow.__init__`.
Add workspace-mixin helpers with these signatures:

```python
def _workspace_context_snapshot(self, *, result_status=None, run_id=None):
    status = result_status or WorkspaceResultStatus.EMPTY
    return WorkspaceContext(
        technique=str(getattr(self, "_current_technique", "") or ""),
        submodule=str(getattr(self, "_current_submodule_id", "") or ""),
        source_path=str(getattr(self, "_current_filepath", "") or ""),
        input_mode=str(getattr(self, "_current_input_mode", "") or ""),
        output_dir=str(getattr(self, "_output_dir", "") or ""),
        run_id=str(run_id if run_id is not None else getattr(self, "_last_persisted_run_id", "") or ""),
        result_status=status,
        result_origin=str(self._current_result_origin() or ""),
    )


def _record_result_context(self, technique=None, *, status="complete", run_id=None):
    context = self._workspace_context_snapshot(
        result_status=WorkspaceResultStatus(str(status).lower()),
        run_id=run_id,
    )
    key = str(technique or context.technique or "").strip().lower()
    if key:
        self._result_contexts[key] = context
    return context


def _result_context_is_current(self, technique=None) -> bool:
    key = str(technique or self._workspace_context.technique or "").strip().lower()
    stored = self._result_contexts.get(key)
    return bool(stored and self._workspace_context.result_matches(stored))


def _workspace_context_summary_text(self, context) -> str:
    source = context.source_path or tr("WORKFLOW_NO_DATA")
    run_id = context.run_id or tr("WORKSPACE_RUN_NOT_PERSISTED")
    return tr("WORKSPACE_CONTEXT_SUMMARY", context.technique or "-", context.submodule or "-", source, run_id)
```

`_workspace_context_snapshot()` must read existing legacy fields, so existing
import/navigation code remains source-compatible. `_update_workspace_context()`
stores the snapshot and updates a new header summary label while preserving the
existing title/subtitle text.

- [ ] **Step 4: Add navigation invalidation and translation keys.**

Call a small `_invalidate_context_bound_views()` helper from both technique and
submodule selection. It clears only `_current_figure_path` and preview selection;
it does not delete persisted results or history. Add translated labels for
`WORKSPACE_CONTEXT_SUMMARY`, `WORKSPACE_RESULT_STALE`, and
`WORKSPACE_RESULT_SOURCE` in both language dictionaries.

- [ ] **Step 5: Run the projection tests and focused existing navigation tests.**

```powershell
python -m pytest tests/test_main_window_workspace_mixin.py tests/test_main_window_navigation_mixin.py -q
```

Expected: all new and existing tests pass.

- [ ] **Step 6: Commit the context projection.**

```powershell
python scripts/auto_commit.py --message "feat(gui): project workspace context" --files polynexus/gui/main_window.py polynexus/gui/main_window_workspace_mixin.py polynexus/gui/main_window_navigation_mixin.py polynexus/gui/i18n.py tests/test_main_window_workspace_mixin.py
```

## Task 3: Gate results, gallery, and history by context

**Files:**
- Modify: `polynexus/gui/main_window_history_mixin.py`
- Modify: `polynexus/gui/main_window_run_mixin.py`
- Modify: `polynexus/gui/main_window_results_mixin.py`
- Modify: `polynexus/gui/main_window_figure_mixin.py`
- Modify: `polynexus/gui/main_window_retranslate_mixin.py`
- Test: `tests/test_main_window_results_mixin.py`
- Test: `tests/test_main_window_figure_mixin.py`
- Test: `tests/test_main_window_history_mixin.py`
- Test: `tests/test_main_window_run_mixin.py`

- [ ] **Step 1: Add failing stale-result tests.**

Cover four boundaries:

```python
def test_current_results_payload_is_empty_for_other_context():
    window = _FakeResultWindow.with_complete_result(technique="saxs", run_id="run-1")
    window._current_technique = "waxs"

    assert window._current_results_payload() == {}


def test_results_banner_names_the_context_that_owns_stale_result():
    window = _FakeResultWindow.with_complete_result(technique="saxs", run_id="run-1")
    window._current_technique = "waxs"
    window._update_result_context_banner()

    assert window._results_context_banner.isVisible()
    assert "saxs" in window._results_context_banner.text().lower()
    assert "run-1" in window._results_context_banner.text()


def test_history_restore_records_restored_run_id_and_context():
    window = _FakeHistoryWindow()
    record = _history_record(technique="saxs", run_id="run-history-7")

    assert window._restore_history_record(record) is True
    assert window._last_persisted_run_id == "run-history-7"
    assert window._result_contexts["saxs"].run_id == "run-history-7"


def test_viewer_does_not_bind_raw_data_from_stale_technique():
    window = _FakeFigureWindow.with_complete_result(technique="saxs", run_id="run-1")
    window._current_technique = "waxs"

    window._open_current_figure_viewer("D:/run/figure.svg")

    assert window.viewer_kwargs["raw_data"] is None
```

The tests must assert that the last complete result remains recoverable in
`_results`, while current-result helpers and viewer/editor routes do not treat
it as the active result.

- [ ] **Step 2: Record result context at publication boundaries.**

After `_persist_analysis_run()` receives the database run id, call
`_record_result_context()` with the active context and that id. For batch and
joint completion use the same result status and context identity. On history
restore set `_last_persisted_run_id` from the selected record id before
displaying the restored payload, then record the restored context.

- [ ] **Step 3: Add a visible stale banner and current-result gate.**

Add a small `QLabel` above `ResultsTablePanel` with object name
`workspace_result_context_banner`. It remains hidden for a matching complete
result. When a stored result exists for another context, show the translated
stale message with its technique/source/run id and keep the table read-only.
Update `_current_results_payload()` and `_current_results_record()` to use
`_result_context_is_current()` before reading `_results`.

- [ ] **Step 4: Gate gallery and viewer/editor routes.**

When `_populate_plots()` runs without a current complete result context, clear
the active gallery preview and show the existing empty/next-action state. When
opening a viewer/editor, pass raw data only if the selected gallery entry's
run root and figure id match the active context; otherwise pass no raw data and
let the entry-specific provenance resolver remain authoritative.

- [ ] **Step 5: Run the context-boundary matrix.**

```powershell
python -m pytest tests/test_main_window_results_mixin.py tests/test_main_window_figure_mixin.py tests/test_main_window_history_mixin.py tests/test_main_window_run_mixin.py -q
```

Expected: all context-boundary tests pass and existing history/gallery routes
remain green.

- [ ] **Step 6: Commit M1 and update task evidence.**

Update `docs/agent/tasks/2026-07-22-editor-workflow-convergence.md` with the
focused test count and known limitations, then run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-22-editor-workflow-convergence.md --changed --types
python scripts/verify.py --changed --types
python scripts/auto_commit.py --message "feat(gui): make result context explicit" --files polynexus/gui/main_window_history_mixin.py polynexus/gui/main_window_run_mixin.py polynexus/gui/main_window_results_mixin.py polynexus/gui/main_window_figure_mixin.py polynexus/gui/main_window_retranslate_mixin.py tests/test_main_window_results_mixin.py tests/test_main_window_figure_mixin.py tests/test_main_window_history_mixin.py tests/test_main_window_run_mixin.py docs/agent/tasks/2026-07-22-editor-workflow-convergence.md
```

Expected: both verifiers pass; no generated outputs or pre-existing untracked
drafts are included in the commit.

## Self-review checklist

- The design's context, stale-result, history, gallery, and export-boundary
  requirements are covered by Tasks 1–3.
- No scientific or document schema changes are introduced in M1.
- All new types and helper names are defined before their use in later tasks.
- Each behavior change has a focused test and an exact verification command.
- The plan intentionally leaves run cancellation, editor capability UI,
  export-intent split, shell drawer, and boundary cleanup for later plans after
  the context contract is stable.
