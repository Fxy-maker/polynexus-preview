# SAXS Temperature Review Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small, sequence-specific review card to the SAXS temperature results page so users can see sequence state and take the next action without changing analysis science or result-table semantics.

**Architecture:** Add a pure presentation helper that reads existing batch rows, evidence summaries, and already-localized summary text. Add a guarded Qt card to the existing Results tab, refresh it from the existing result-summary and confirmation paths, and wire its actions to existing tab navigation and confirmation methods.

**Tech Stack:** Python 3.11+, PySide6, pytest, existing PolyNexus i18n/theme/result-table services.

---

## File map

- Create `polynexus/gui/saxs_temperature_review_service.py`: pure UI model normalization; no Qt imports and no science recalculation.
- Create `tests/test_saxs_temperature_review_service.py`: pure-model tests for complete, incomplete, confirmed, non-temperature, and malformed inputs.
- Modify `polynexus/gui/main_window_results_mixin.py`: build the card, render its model, and connect actions.
- Modify `polynexus/gui/main_window_output_mixin.py`: refresh the card whenever the existing result summary refreshes.
- Modify `polynexus/gui/main_window_retranslate_mixin.py`: refresh card labels after language changes.
- Modify `polynexus/gui/i18n.py`: add Chinese and English card text.
- Add `tests/test_saxs_temperature_review_ui.py`: verify visibility and action routing without starting analysis.

### Task 1: Define the failing presentation-model tests

**Files:**
- Create: `tests/test_saxs_temperature_review_service.py`

- [ ] **Step 1: Add complete and incomplete sequence fixtures.**

Use the existing result shape from `tests/test_results_table_service.py`:

```python
from polynexus.gui.saxs_temperature_review_service import build_saxs_temperature_review_model


def _params():
    return {
        "batch_frames": 3,
        "_batch_data": [
            {"temperature_C": 180.0, "lc_reliability_status": "usable", "melting_window_status": "outside"},
            {"temperature_C": 190.0, "lc_reliability_status": "low_confidence", "melting_window_status": "near_onset"},
            {"temperature_C": 200.0, "lc_reliability_status": "usable", "melting_window_status": "within_window"},
        ],
    }


def _evidence():
    return {
        "batch_evidence": {
            "batch_structure_summary": {
                "diagnostic_only_rows": 0,
                "low_confidence_rows": 1,
                "within_window_rows": 1,
                "dominant_lc_reliability_status": "low_confidence",
            }
        },
        "feature_evidence": {
            "sequence_evidence": {"temperature_axis_confidence": 0.92}
        },
    }
```

- [ ] **Step 2: Write the visible-model assertion.**

```python
def test_temperature_review_model_counts_frames_and_exposes_next_action():
    model = build_saxs_temperature_review_model(
        _params(),
        submodule="saxs.temperature",
        analysis_evidence=_evidence(),
        summary_text="3 frames generated",
        risk_text="1 frame needs review",
        next_text="Review the temperature overview",
        confirmed=False,
    )

    assert model["visible"] is True
    assert model["frame_count"] == 3
    assert model["review_frame_count"] == 1
    assert model["melting_window_frame_count"] == 1
    assert model["temperature_axis_status"] == "ready"
    assert model["status"] == "review"
    assert model["next_text"] == "Review the temperature overview"
```

- [ ] **Step 3: Add fallback and non-temperature tests.**

```python
def test_temperature_review_model_hides_for_other_submodules():
    model = build_saxs_temperature_review_model(
        _params(), submodule="saxs.static", analysis_evidence={}
    )
    assert model == {"visible": False}


def test_temperature_review_model_does_not_crash_on_missing_evidence():
    model = build_saxs_temperature_review_model(
        {"batch_frames": 2, "_batch_data": [{}, {}]},
        submodule="saxs.temperature",
        analysis_evidence=None,
        confirmed=True,
    )
    assert model["visible"] is True
    assert model["frame_count"] == 2
    assert model["temperature_axis_status"] == "unknown"
    assert model["status"] == "confirmed"
```

- [ ] **Step 4: Run the new tests and verify the expected red state.**

Run:

```powershell
python -m pytest tests/test_saxs_temperature_review_service.py -q
```

Expected: collection fails with `ModuleNotFoundError` for `polynexus.gui.saxs_temperature_review_service`.

### Task 2: Implement the pure temperature-review model

**Files:**
- Create: `polynexus/gui/saxs_temperature_review_service.py`
- Test: `tests/test_saxs_temperature_review_service.py`

- [ ] **Step 1: Add defensive row and axis helpers.**

Implement these module-level values and functions without importing PySide6:

```python
REVIEW_LC_STATUSES = {"diagnostic_only", "low_confidence", "review", "failed", "error"}
WITHIN_WINDOW_STATUSES = {"within_window"}


def _rows(params):
    value = params.get("_batch_data") if isinstance(params, dict) else None
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _safe_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _axis_status(analysis_evidence):
    feature = analysis_evidence.get("feature_evidence", {}) if isinstance(analysis_evidence, dict) else {}
    sequence = feature.get("sequence_evidence", {}) if isinstance(feature, dict) else {}
    try:
        score = float(sequence.get("temperature_axis_confidence"))
    except (TypeError, ValueError):
        return "unknown"
    return "ready" if score >= 0.75 else "review"
```

- [ ] **Step 2: Implement `build_saxs_temperature_review_model`.**

Use this signature and return shape:

```python
def build_saxs_temperature_review_model(
    params,
    *,
    submodule="",
    analysis_evidence=None,
    summary_text="",
    risk_text="",
    next_text="",
    confirmed=False,
):
    if str(submodule or "").strip().lower() not in {"temperature", "saxs.temperature"}:
        return {"visible": False}

    params = params if isinstance(params, dict) else {}
    rows = _rows(params)
    summary = params.get("batch_structure_summary", {})
    summary = summary if isinstance(summary, dict) else {}
    review_count = _safe_int(summary.get("diagnostic_only_rows"))
    review_count += _safe_int(summary.get("low_confidence_rows"))
    if not review_count:
        review_count = sum(
            str(row.get("lc_reliability_status") or "").strip().lower() in REVIEW_LC_STATUSES
            for row in rows
        )
    window_count = _safe_int(summary.get("within_window_rows"))
    if not window_count:
        window_count = sum(
            str(row.get("melting_window_status") or "").strip().lower() in WITHIN_WINDOW_STATUSES
            for row in rows
        )
    axis_status = _axis_status(analysis_evidence)
    status = "confirmed" if confirmed else (
        "review" if review_count or axis_status == "review" or risk_text else "ready"
    )
    return {
        "visible": True,
        "status": status,
        "frame_count": _safe_int(params.get("batch_frames")) or len(rows),
        "review_frame_count": review_count,
        "melting_window_frame_count": window_count,
        "temperature_axis_status": axis_status,
        "summary_text": str(summary_text or ""),
        "risk_text": str(risk_text or ""),
        "next_text": str(next_text or ""),
        "confirmed": bool(confirmed),
    }
```

Missing or malformed fields must return safe zero/unknown values rather than raising.

- [ ] **Step 3: Run the pure tests and verify green.**

Run:

```powershell
python -m pytest tests/test_saxs_temperature_review_service.py -q
```

Expected: all tests pass.

### Task 3: Add the results-page card and action routing

**Files:**
- Modify: `polynexus/gui/main_window_results_mixin.py`
- Create: `tests/test_saxs_temperature_review_ui.py`

- [ ] **Step 1: Build the card and required widget attributes.**

Add `_build_saxs_temperature_review_panel()` next to the existing result summary/review builders. Create a hidden `QGroupBox` and these attributes:

```text
_saxs_temperature_review_group
_saxs_temperature_review_title
_saxs_temperature_review_status
_saxs_temperature_review_metrics
_saxs_temperature_review_summary
_saxs_temperature_review_risk
_saxs_temperature_review_next
_saxs_temperature_review_plots_btn
_saxs_temperature_review_config_btn
_saxs_temperature_review_confirm_btn
```

- [ ] **Step 2: Connect only existing navigation and confirmation methods.**

Use these exact connections:

```python
self._saxs_temperature_review_plots_btn.clicked.connect(lambda: self._jump_to_tab(3))
self._saxs_temperature_review_config_btn.clicked.connect(lambda: self._jump_to_tab(1))
self._saxs_temperature_review_confirm_btn.clicked.connect(self._toggle_current_result_confirmation)
```

Do not connect a new button to `_run_analysis`; returning to configuration must never start an implicit rerun.

- [ ] **Step 3: Insert the card after the existing summary group.**

In `_build_results_tab`, add:

```python
self._saxs_temperature_review_panel = self._build_saxs_temperature_review_panel()
layout.addWidget(self._saxs_temperature_review_panel)
```

Keep the existing result review, compare, confirm, and table sections in their current order.

- [ ] **Step 4: Implement `_refresh_saxs_temperature_review_panel`.**

Read the current submodule, current result source params, `self._current_analysis_evidence()`, the existing summary/risk/next labels, and `self._is_current_result_confirmed()`. Pass those values to the pure model. Hide the group for non-temperature results or absent results. For a visible model, render the four metrics, localized status, existing summary/risk/next text, and current confirmation button state. Tolerate a missing result source and deleted Qt objects.

- [ ] **Step 5: Add offscreen UI tests.**

Set `QT_QPA_PLATFORM=offscreen`, use a `QApplication`, populate a `saxs.temperature` context with `_batch_data`, call the refresher, and assert the group is visible. Repeat for `saxs.static` and assert it is hidden. Replace `_jump_to_tab` and `_run_analysis` on a lightweight harness, click the three buttons, and assert tab indices `3` and `1`, confirmation routing, and zero run calls.

- [ ] **Step 6: Run targeted UI tests.**

Run:

```powershell
python -m pytest tests/test_saxs_temperature_review_ui.py tests/test_main_window_results_mixin.py -q
```

Expected: all targeted tests pass.

### Task 4: Refresh from existing result and confirmation paths

**Files:**
- Modify: `polynexus/gui/main_window_output_mixin.py`
- Modify: `polynexus/gui/main_window_results_mixin.py`

- [ ] **Step 1: Refresh after `_set_results_summary`.**

At the end of `MainWindowOutputMixin._set_results_summary`, invoke the optional refresher after the existing review refresh:

```python
refresh_review = getattr(self, "_refresh_saxs_temperature_review_panel", None)
if callable(refresh_review):
    refresh_review()
```

This covers single-run, batch-run, and structured-table paths without duplicating calls at every early return.

- [ ] **Step 2: Refresh after confirmation changes.**

At the end of `_update_results_confirm_panel`, call the same optional refresher so the status changes immediately after `_toggle_current_result_confirmation`.

- [ ] **Step 3: Add a refresh regression assertion and run mixin tests.**

Use a harness counter to verify the refresher is called when a current result exists, then run:

```powershell
python -m pytest tests/test_main_window_results_mixin.py tests/test_main_window_output_mixin.py tests/test_saxs_temperature_review_service.py -q
```

Expected: all tests pass.

### Task 5: Add bilingual text and language-refresh wiring

**Files:**
- Modify: `polynexus/gui/i18n.py`
- Modify: `polynexus/gui/main_window_retranslate_mixin.py`
- Modify: `polynexus/gui/main_window_results_mixin.py`
- Modify: `tests/test_main_window_retranslate_mixin.py`

- [ ] **Step 1: Add Chinese and English keys.**

Add title, four statuses, four metric labels, three actions, and the unknown-axis label. Use this key family:

```python
"SAXS_TEMP_REVIEW_TITLE"
"SAXS_TEMP_REVIEW_STATUS_REVIEW"
"SAXS_TEMP_REVIEW_STATUS_READY"
"SAXS_TEMP_REVIEW_STATUS_CONFIRMED"
"SAXS_TEMP_REVIEW_STATUS_EMPTY"
"SAXS_TEMP_REVIEW_ACTION_PLOTS"
"SAXS_TEMP_REVIEW_ACTION_CONFIG"
"SAXS_TEMP_REVIEW_ACTION_CONFIRM"
```

Add matching values in both existing language dictionaries.

- [ ] **Step 2: Refresh translated card labels.**

Call `_refresh_saxs_temperature_review_panel()` near the end of `_retranslate_ui`. The refresher must translate status tokens and action labels every time; it must not preserve text from the previous language.

- [ ] **Step 3: Run language and UI regression tests.**

Run:

```powershell
python -m pytest tests/test_main_window_retranslate_mixin.py tests/test_ui_function_streamlining.py tests/test_saxs_temperature_review_ui.py -q
```

Expected: all tests pass.

### Task 6: Verify the complete scoped behavior

**Files:** The final verification task reads the scoped files above; no additional implementation files are expected.

- [ ] **Step 1: Run scoped SAXS and result regressions.**

```powershell
python -m pytest tests/test_saxs_results_table_service.py tests/test_results_table_service.py tests/test_analysis_history_service.py tests/test_results_review_service.py tests/test_main_window_results_mixin.py tests/test_main_window_output_mixin.py tests/test_saxs_temperature_review_service.py tests/test_saxs_temperature_review_ui.py -q
```

Expected: exit code 0 with zero failures.

- [ ] **Step 2: Run the complete suite.**

```powershell
python -m pytest -q
```

Expected: exit code 0 with zero failures. If unrelated pre-existing failures remain, record their exact node IDs and do not report the suite as passing.

- [ ] **Step 3: Check the final diff.**

```powershell
git diff --check
git status --short
git diff --stat
```

Expected: no whitespace errors; only service, UI, i18n, and test files are changed. Keep `.superpowers/` mockups out of the implementation commit.

- [ ] **Step 4: Manually exercise the closed loop with the repository temperature dataset.**

Launch the GUI with `polynexus --gui`, open `D:\PolyNexus\测试数据\saxs\pa6变温`, select `原位变温 SAXS`, and run the sequence. Verify: the Results tab shows the card; plots selects tab 3; config selects tab 1; confirm changes the card status; no action starts a second run automatically.

- [ ] **Step 5: Commit after fresh verification.**

```powershell
git add polynexus/gui/saxs_temperature_review_service.py polynexus/gui/main_window_results_mixin.py polynexus/gui/main_window_output_mixin.py polynexus/gui/main_window_retranslate_mixin.py polynexus/gui/i18n.py tests/test_saxs_temperature_review_service.py tests/test_saxs_temperature_review_ui.py tests/test_main_window_retranslate_mixin.py
git commit -m "feat: add SAXS temperature review loop"
```
