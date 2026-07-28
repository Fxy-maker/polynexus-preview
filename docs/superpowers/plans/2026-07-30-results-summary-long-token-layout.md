# Results Summary Long-Token Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Results Summary evidence readable at narrow and native desktop widths even when a diagnostic reason contains long delimiter-free tokens.

**Architecture:** Keep the existing plain-text evidence contract and labels. Use a QLabel subclass that stores the source string unchanged while giving Qt invisible break opportunities for display-only layout; do not alter scientific text, evidence severity, or result semantics. Lock the behavior with a Qt regression that checks the label's minimum width and preserves the exact source text.

**Tech Stack:** Python, PySide6 `QLabel`/`QTextOption`, pytest, repository verification scripts.

---

### Task 1: Reproduce the long-token clipping

**Files:**
- Modify: `tests/test_saxs_results_evidence_layout.py`

- [x] **Step 1: Add one failing layout regression**

Add a test that sets a long delimiter-free diagnostic reason, resizes the
Results Summary to a 640-pixel label width, and asserts that the label needs
more than one line while retaining the exact text:

```python
def test_long_results_evidence_breaks_delimiter_free_reason_tokens():
    QApplication.instance() or QApplication([])
    window = MainWindow()
    risk_text = "Risk note | reasons=" + ("automated_validation_failed," * 40)
    try:
        window._set_results_summary("SAXS results", risk_text, "")
        window.show()
        window._results_summary_risk_label.setFixedWidth(640)
        QApplication.processEvents()

        label = window._results_summary_risk_label
        assert label.text() == risk_text
        assert label.heightForWidth(640) > label.fontMetrics().height()
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
```

- [x] **Step 2: Run the focused test and confirm the expected RED failure**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest -q tests/test_saxs_results_evidence_layout.py::test_long_results_evidence_breaks_delimiter_free_reason_tokens -vv
```

Expected result before the fix: failure because the delimiter-free token is
measured as one unbroken line.

### Task 2: Apply the minimal presentation fix

**Files:**
- Modify: `polynexus/gui/main_window_results_mixin.py`

- [x] **Step 1: Configure summary evidence labels to wrap anywhere**

Add a private QLabel subclass near the existing Qt imports. Its `setText`
stores the source string, calls the base implementation with zero-width spaces
between source characters, and its `text()` returns the source string. This
gives Qt break opportunities for long diagnostic tokens while preserving the
existing public plain-text contract. Use the subclass for the three Results
Summary labels and the matching Result Review evidence labels; keep all
existing size policies unchanged.

```python
class _WrappedEvidenceLabel(QLabel):
    def __init__(self, *args, **kwargs):
        self._source_text = ""
        super().__init__(*args, **kwargs)

    def setText(self, text):
        self._source_text = "" if text is None else str(text)
        super().setText("\u200b".join(self._source_text))

    def text(self):
        return self._source_text

self._results_summary_risk_label = _WrappedEvidenceLabel()
```

- [x] **Step 2: Run the focused regression and existing layout tests**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest -q tests/test_saxs_results_evidence_layout.py -vv
```

Expected result: all tests pass and the long source string remains unchanged.

### Task 3: Verify and record

**Files:**
- Create: `docs/agent/tasks/2026-07-30-results-summary-long-token-layout.md`
- Create: `docs/acceptance/2026-07-30-results-summary-long-token-layout.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run the structured verifier**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-30-results-summary-long-token-layout.md --changed --types
git diff --check
```

- [x] **Step 2: Run the native route recheck only if the focused GUI regression
  is green**

Use the existing native route harness with a fresh D: basetemp and capture
directory; record its actual exit code and summary. This confirms the fix does
not break the shared Results Workbench routes, but it does not replace human
visual or scientific review.

- [x] **Step 3: Create one explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(gui): wrap long results evidence" --files polynexus/gui/main_window_results_mixin.py tests/test_saxs_results_evidence_layout.py docs/superpowers/plans/2026-07-30-results-summary-long-token-layout.md docs/agent/tasks/2026-07-30-results-summary-long-token-layout.md docs/acceptance/2026-07-30-results-summary-long-token-layout.md docs/agent/memory/active-work.md
```

## Scope audit

- No analysis engines, evidence generation, thresholds, severity, publication
  roles, datasets, or cleanup commands change.
- The current uncommitted `docs/agent/memory/current-state.md` legacy-storage
  edit and all pytest scratch/capture directories remain outside the allowlist.
