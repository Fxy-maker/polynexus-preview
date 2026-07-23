# Inline Text Editor Visuals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the intrusive native canvas text input frame with a lightweight editing surface that retains a visible caret and subtle text-region guide.

**Architecture:** The existing shared `_InlineTextEdit` remains the only direct-text input widget. Its construction in `ChartEditorInlineTextMixin` becomes responsible for visual chrome only; geometry, focus, commit, cancel, and generated/static payload paths stay unchanged. A focused Qt workflow regression describes the visual contract without depending on screenshot pixels.

**Tech Stack:** Python 3.12, PySide6 `QLineEdit`, pytest-qt-style application fixture.

---

### Task 1: Specify the lightweight inline editor appearance

**Files:**
- Modify: `D:/PolyNexus/tests/test_chart_editor_workflow.py`

- [x] **Step 1: Write the failing test**

```python
def test_inline_text_editor_uses_canvas_editing_chrome(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    editor._begin_generated_text_box((0.2, 0.3), (0.5, 0.5), QRect(20, 20, 240, 28))

    inline_editor = editor._inline_text_editor
    assert inline_editor.isVisible()
    assert inline_editor.hasFrame() is False
    assert inline_editor.placeholderText() == ""
    assert "border: 1px dashed" in inline_editor.styleSheet()
    assert "background: transparent" in inline_editor.styleSheet()
```

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_chart_editor_workflow.py -q -k inline_text_editor_uses_canvas_editing_chrome
```

Expected: FAIL because the current editor retains its native frame and `标注文字` placeholder.

### Task 2: Apply the canvas editing style

**Files:**
- Modify: `D:/PolyNexus/polynexus/gui/widgets/chart_editor_inline_text_mixin.py:24-35`

- [x] **Step 1: Configure the existing QLineEdit with transparent canvas chrome**

```python
editor.setObjectName("editor_inline_text")
editor.setFrame(False)
editor.setPlaceholderText("")
editor.setStyleSheet(
    "QLineEdit#editor_inline_text {"
    "background: transparent;"
    "border: 1px dashed rgba(47, 111, 191, 150);"
    "border-radius: 2px;"
    "padding: 0 4px;"
    "}"
)
```

Keep `returnPressed`, `editingFinished`, focus, and cancellation wiring untouched so the blink caret remains provided by Qt.

- [x] **Step 2: Run the focused visual regression**

Run the command from Task 1. Expected: `1 passed`.

- [x] **Step 3: Run the surrounding direct-text workflow suite**

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_chart_editor_workflow.py tests/test_chart_editor_curve.py tests/test_chart_editor_context_menu.py -q
```

Expected: all selected tests pass; existing Matplotlib tight-layout warnings may remain.

### Task 3: Record and verify the checkpoint

**Files:**
- Modify: `D:/PolyNexus/docs/agent/memory/active-work.md`

- [x] **Step 1: Record the visual behavior, focused evidence, and restart requirement**

Add a dated entry explaining that canvas text entry uses transparent, dashed editing chrome without a placeholder while preserving the Qt caret and existing keyboard behavior.

- [x] **Step 2: Run repository verification**

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python scripts/verify.py --changed --types
```

Expected: Ruff, compile, quality gate, preprocess gate, memory check, and whitespace check pass.

- [x] **Step 3: Commit the verified task**

```powershell
python scripts/auto_commit.py `
  --message "fix(editor): simplify inline text entry chrome" `
  --files docs/agent/memory/active-work.md docs/superpowers/plans/2026-07-23-inline-text-editor-visuals.md polynexus/gui/widgets/chart_editor_inline_text_mixin.py tests/test_chart_editor_workflow.py
```
