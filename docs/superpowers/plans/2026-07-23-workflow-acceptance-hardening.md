# Workflow Acceptance Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining evidence and usability gaps in the six-milestone editor workflow without changing scientific semantics or renderer contracts.

**Architecture:** Preserve the existing `WorkspaceContext`, editor capability descriptor, and worker lifecycle contracts. First align stale regression expectations with the current direct-canvas feedback contract, then add a Qt-independent diagnostic payload service and a small cancellation state contract. Only after those tests are green will we decide whether a narrowly scoped MainWindow boundary extraction is justified.

**Tech Stack:** Python dataclasses, PySide6, pytest, existing GUI mixins and services.

---

### Task 1: Align direct-canvas feedback regression expectations

**Files:**
- Modify: `tests/test_chart_editor.py`
- Test: `tests/test_chart_editor.py::test_chart_editor_real_canvas_escape_key_clears_selection_and_restores_hover_feedback`

- [x] **Step 1: Reproduce the failure**

Run:

```powershell
python -m pytest tests/test_chart_editor.py::test_chart_editor_real_canvas_escape_key_clears_selection_and_restores_hover_feedback -q --basetemp "$env:TEMP/polynexus-chart-editor-acceptance"
```

Expected: the assertion expecting only `EDITOR_SELECTED_STATUS_OBJECT` fails because the current status also describes body and endpoint dragging.

- [x] **Step 2: Update the focused assertion to the current contract**

Assert the selected prefix and the actionable endpoint guidance:

```python
status_text = editor._status_label.text()
assert status_text.startswith(tr("EDITOR_SELECTED_STATUS_OBJECT", "Line: Guide"))
assert "endpoint" in status_text.lower()
```

- [x] **Step 3: Run the focused test**

Expected: one test passes and no editor source changes are required.

- [x] **Step 4: Commit the test contract update**

```powershell
python scripts/auto_commit.py --message "test(editor): accept actionable selection feedback" --files tests/test_chart_editor.py
```

### Task 2: Make user-triggered errors copyable and recoverable

**Files:**
- Create: `polynexus/gui/error_diagnostic_service.py`
- Modify: `polynexus/gui/main_window.py`
- Modify: `polynexus/gui/main_window_run_mixin.py`
- Modify: `polynexus/gui/main_window_retranslate_mixin.py`
- Modify: `polynexus/gui/i18n.py`
- Test: `tests/test_error_diagnostic_service.py`

- [x] **Step 1: Write the pure diagnostic payload test**

```python
def test_diagnostic_payload_contains_operation_message_and_recovery():
    payload = build_error_diagnostic(
        operation="analysis",
        message="bad input",
        detail="traceback line",
        recovery="retry",
    )
    assert payload.copy_text.startswith("analysis: bad input")
    assert "traceback line" in payload.copy_text
    assert payload.recovery == "retry"
```

- [x] **Step 2: Implement the Qt-independent payload builder**

Expose an immutable payload with `title`, `copy_text`, and `recovery`; normalize empty detail and recovery text without throwing.

- [x] **Step 3: Add a copy-diagnostics action to the main error path**

Store the last payload on `_on_error`, expose a `Copy diagnostics` button beside retry, and copy only the generated payload to `QApplication.clipboard()`.

- [x] **Step 4: Verify and commit**

```powershell
python -m pytest tests/test_error_diagnostic_service.py tests/test_main_window_run_mixin.py -q
python scripts/auto_commit.py --message "feat(gui): add copyable error diagnostics" --files polynexus/gui/error_diagnostic_service.py tests/test_error_diagnostic_service.py polynexus/gui/main_window.py polynexus/gui/main_window_run_mixin.py polynexus/gui/main_window_retranslate_mixin.py polynexus/gui/i18n.py
```

### Task 3: Verify cancellation state without publishing partial results

**Files:**
- Create: `polynexus/gui/run_state_service.py`
- Modify: `polynexus/gui/main_window_run_mixin.py`
- Modify: `polynexus/gui/main_window_workers.py`
- Test: `tests/test_run_state_service.py`

- [x] **Step 1: Write state transition tests**

Cover `idle -> running -> cancelling -> cancelled`, `running -> failed`, and the rule that `should_publish_result` is false for cancelled state.

- [x] **Step 2: Implement the immutable state contract**

Use enum values `idle`, `running`, `cancelling`, `cancelled`, `failed`, `complete` and a pure transition helper.

- [x] **Step 3: Replace ad-hoc cancellation flags at the GUI publication boundary**

Keep worker interruption behavior unchanged, but derive `_run_cancel_requested` and publication guards from the state helper.

- [x] **Step 4: Run tests and commit**

```powershell
python -m pytest tests/test_run_state_service.py tests/test_main_window_workers.py tests/test_main_window_run_mixin.py -q
python scripts/auto_commit.py --message "feat(gui): formalize run cancellation state" --files polynexus/gui/run_state_service.py tests/test_run_state_service.py polynexus/gui/main_window_run_mixin.py polynexus/gui/main_window_workers.py
```

### Task 4: Acceptance evidence and boundary decision

**Files:**
- Modify: `docs/agent/tasks/2026-07-22-editor-workflow-convergence.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run stable focused Qt batches with an external basetemp**

Run the workflow matrix, ChartEditor targeted batches, and the structured verifier. Record any remaining Qt access violation with the exact test path.

- [x] **Step 2: Decide M6 scope from evidence**

Do not refactor `main_window.py` broadly if the behavior matrix is green. Record the existing service boundaries and any remaining architecture debt instead.

- [x] **Step 3: Update durable state and commit evidence**

Record exact pass counts, known limitations, and pre-existing untracked files left untouched.
