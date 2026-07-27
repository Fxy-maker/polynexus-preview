# SAXS Workbench Series Evidence Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended) or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show existing temperature/strain series quality evidence in the Results Workbench while preserving frame-level evidence and publication boundaries.

**Architecture:** The SAXS engine transports the already-computed series summary through the existing temperature/strain parameters payload. The SAXS table presentation formats only contract fields into existing review text channels; the Diagnostics table continues to serialize the full nested payload. History and Export reuse their current persistence/provenance paths.

**Tech Stack:** Python dataclasses and mappings, PySide6 presentation models, pytest, existing SAXS quality contracts, `scripts/verify.py`.

---

### Task 1: Add failing transport and presentation tests

**Files:**
- Create: `tests/test_saxs_workbench_series_evidence.py`

- [ ] **Step 1: Write the failing tests**

Add tests that construct a lightweight SAXS engine instance with existing
temperature/strain result objects and assert `get_parameters()` preserves the
series summary object by value. Add presentation tests using:

```python
from polynexus.gui.saxs_results_table_service import build_saxs_results_presentation


def test_mixed_series_evidence_is_visible_as_downgraded_review_text():
    params = {
        "batch_frames": 3,
        "_batch_data": [
            {"temperature_C": 20.0, "L_nm": 12.0},
            {"temperature_C": 40.0, "L_nm": 12.2},
            {"temperature_C": 60.0, "L_nm": None},
        ],
        "metric_evidence": {
            "porod": {
                "metric_name": "Porod",
                "frame_count": 3,
                "evidence_frame_count": 2,
                "usable_frame_count": 1,
                "diagnostic_frame_count": 1,
                "unusable_frame_count": 0,
                "missing_frame_count": 1,
                "coverage_fraction": 2 / 3,
                "level": "Diagnostic",
                "applicable": False,
                "level_counts": {"Quantitative": 0, "Trend": 1, "Diagnostic": 1, "Unusable": 0},
                "reason_codes": ["series_metric_missing_frames", "series_metric_diagnostic_frames"],
            }
        },
    }

    presentation = build_saxs_results_presentation(
        params, submodule="saxs.temperature", language="en"
    )

    assert "Porod" in presentation.risk_text or "Porod" in presentation.next_text
    assert "2/3" in (presentation.risk_text + presentation.next_text)
    assert "Diagnostic" in (presentation.risk_text + presentation.next_text)
    assert "series_metric_missing_frames" in presentation.diagnostics.rows[-1][0].display or any(
        "metric_evidence" == column.key for column in presentation.diagnostics.columns
    )
```

Also add a complete-series assertion that the text contains `Trend`, `2/2`,
and does not contain `Quantitative` as the series claim. Add a Chinese
localization smoke assertion that the output is non-empty and contains the
localized downgrade label.

- [ ] **Step 2: Run the new tests to verify RED**

Run:

```powershell
python -m pytest tests/test_saxs_workbench_series_evidence.py -q
```

Expected: collection or assertions fail because the engine does not transport
the series mapping and the presentation does not yet create review text.

### Task 2: Transport existing summaries through SAXS parameters

**Files:**
- Modify: `polynexus/core/saxs.py`
- Test: `tests/test_saxs_workbench_series_evidence.py`

- [ ] **Step 1: Add the minimal implementation**

In the temperature branch of `SAXS.get_parameters()`, immediately after
creating `params`, copy the existing mapping only when it is a mapping:

```python
metric_evidence = getattr(tr, "metric_evidence", None)
if isinstance(metric_evidence, dict) and metric_evidence:
    params["metric_evidence"] = {
        str(name): dict(summary)
        for name, summary in metric_evidence.items()
        if isinstance(summary, dict)
    }
```

Use the identical block against `sr` in the strain branch. Do not call the
quality builder, inspect q/I arrays, or modify `tr.metric_evidence`/
`sr.metric_evidence`. The existing `_build_batch_parameters_payload()` will
carry this non-underscore summary beside the frame rows.

- [ ] **Step 2: Run the transport tests GREEN**

Run:

```powershell
python -m pytest tests/test_saxs_workbench_series_evidence.py -k transport -q
```

Expected: the temperature and strain payload assertions pass and the original
summary dictionaries are unchanged.

### Task 3: Add deterministic Workbench review text

**Files:**
- Modify: `polynexus/gui/saxs_results_table_service.py`
- Test: `tests/test_saxs_workbench_series_evidence.py`

- [ ] **Step 1: Implement a presentation-only formatter**

Add a private helper that accepts `payload` and normalized language and returns
`tuple[str, str]` for `(risk_text, next_text)`. It must:

1. read only `payload.get("metric_evidence")` when it is a mapping;
2. sort metric names for deterministic output;
3. display `evidence_frame_count/frame_count`, level, and non-zero diagnostic,
   unusable, or missing counts;
4. include reason codes only for downgraded summaries;
5. return empty strings when no valid summaries exist;
6. use existing localization helpers or add exact English/Chinese i18n keys;
7. never change the level, `applicable`, counts, or nested payload.

For a downgraded summary, place the compact quality warning in `risk_text`
and a short review action in `next_text`. For a complete summary, place the
Trend/coverage statement in `next_text` and leave `risk_text` empty. Pass the
two strings into the existing `ResultsTablePresentation` return value.

- [ ] **Step 2: Run presentation tests GREEN**

Run:

```powershell
python -m pytest tests/test_saxs_workbench_series_evidence.py -k presentation -q
```

Expected: complete and mixed summaries produce stable English/Chinese text;
Diagnostics still contains the serialized `metric_evidence` column.

### Task 4: Verify Workbench, History, Figure, and Export propagation

**Files:**
- Test: `tests/test_saxs_workbench_series_evidence.py`

- [ ] **Step 1: Add focused consumer assertions**

Prove in `tests/test_saxs_workbench_series_evidence.py` that
`build_results_table_model()` for `saxs.temperature` carries the presentation
`risk_text`/`next_text`, that `profile_for("saxs.temperature")` keeps its
figure candidates unchanged, and that `persist_analysis_run()` stores
`metric_evidence` inside the parameters/result payload without mutation.

- [ ] **Step 2: Run the focused consumer matrix**

Run:

```powershell
python -m pytest tests/test_saxs_workbench_series_evidence.py tests/test_saxs_workbench_figure_contracts.py tests/test_results_workbench_profiles.py tests/test_analysis_run_service.py tests/test_saxs_export_bundle.py -q
```

Expected: all focused tests pass; figure IDs/roles and Export quality
provenance are unchanged.

### Task 5: Verify, document, and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-27-saxs-workbench-series-evidence-visibility.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: this plan

- [ ] **Step 1: Run required verification**

Run the task-scoped verifier and `git diff --check`; record exact counts and
the known pre-existing `main_window_shell_mixin.py:154` Ruff blocker if it
appears.

- [ ] **Step 2: Run the applicable SAXS matrix**

Run the focused Workbench/History/Figure/Export matrix plus the existing SAXS
quality and preprocessing gates relevant to changed files. Do not claim a
full repository pass unless the full command actually completes successfully.

- [ ] **Step 3: Update durable state and checkpoint**

Mark only verified acceptance items, list limitations, and run:

```powershell
python scripts/auto_commit.py --message "feat(saxs): surface series evidence in workbench" --files polynexus/core/saxs.py polynexus/gui/saxs_results_table_service.py tests/test_saxs_workbench_series_evidence.py docs/agent/tasks/2026-07-27-saxs-workbench-series-evidence-visibility.md docs/superpowers/specs/2026-07-27-saxs-workbench-series-evidence-visibility-design.md docs/superpowers/plans/2026-07-27-saxs-workbench-series-evidence-visibility.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

Do not push, merge, deploy, or clean unrelated files.

## Plan self-review

- Existing series summaries are transported; no evidence is recomputed.
- The GUI formatter is read-only and has no scientific thresholds.
- Complete series claims remain Trend-capped.
- Downgrade details remain visible in both review text and Diagnostics.
- Figure routing and Export provenance are tested as unchanged boundaries.
