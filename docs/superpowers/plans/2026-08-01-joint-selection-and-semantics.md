# Joint Selection and Result Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Joint compare only explicitly selected batches, expose source provenance, distinguish missing data from conflicts, and keep assignment-limited solid-C out of Xc comparison.

**Architecture:** Keep the existing `JointBatchRow` batch boundary and latest-run-per-technique transport contract, but make GUI selection explicit and add a detached source-preflight projection. Validation rows gain a status distinction so unavailable inputs are not counted as warnings. Reports and exports consume the same detached data without changing technique engines.

**Tech Stack:** Python, PySide6, pytest, SQLite-backed `SampleDB`, existing Joint validation/report and Figure Manifest lifecycle.

---

### Task 1: Lock the explicit-selection GUI contract

**Files:**
- Modify: `polynexus/gui/widgets/joint_analysis_hub.py:59-67, 261-279`
- Test: `tests/test_joint_analysis_hub.py`

- [ ] **Step 1: Write the failing test**

Add a Qt regression that creates a hub with two candidate rows, calls
`set_db()`/`refresh()`, and asserts `selected_rows()` is empty. Keep a second
assertion that calling `_select_recommended()` explicitly selects only rows
with at least two techniques. Use the existing offscreen QApplication setup
and test fixture style in `tests/test_joint_analysis_hub.py`.

- [ ] **Step 2: Run the focused test and verify the failure**

Run:

```powershell
python -m pytest -q tests/test_joint_analysis_hub.py -k "refresh or recommended"
```

Expected: the refresh assertion fails because `refresh()` currently invokes
`_select_recommended()`.

- [ ] **Step 3: Implement the minimal behavior**

Remove the `_select_recommended()` call from `refresh()` and leave the explicit
button connection unchanged. Keep `_select_recommended()` as a user-triggered
operation. Ensure `_populate_table()` initializes every check box unchecked and
`_update_summary()` continues to disable Run when there is no selection.

- [ ] **Step 4: Run the focused test and verify the pass**

Run:

```powershell
python -m pytest -q tests/test_joint_analysis_hub.py
```

Expected: all existing GUI hub tests and the new selection regression pass.

- [ ] **Step 5: Commit the atomic GUI change**

```powershell
python scripts/auto_commit.py --message "fix(joint): require explicit batch selection" --files polynexus/gui/widgets/joint_analysis_hub.py tests/test_joint_analysis_hub.py
```

### Task 2: Add detached source-preflight projection

**Files:**
- Modify: `polynexus/core/joint/dataset.py:177-278`
- Modify: `polynexus/gui/main_window_joint_diagnostics_mixin.py:93-132`
- Test: `tests/test_joint_hub_dataset.py`

- [ ] **Step 1: Write the failing core test**

Add a test that builds one selected batch with DSC and SAXS runs, calls
`build_joint_hub_report()`, and asserts the report contains a JSON-safe
`source_preflight` entry for each available technique with `sample_id`,
`batch_id`, `technique`, `submodule`, `run_id`, `created_at`, `source_path`,
`condition_values`, `evidence_status`, and `evidence_reasons`. Add a second
batch with a different run and assert it is a separate row rather than being
merged into the first row.

- [ ] **Step 2: Run the focused test and verify the failure**

```powershell
python -m pytest -q tests/test_joint_hub_dataset.py -k "preflight or separate"
```

Expected: the new `source_preflight` assertion fails because the report only
contains summary rows and validation provenance today.

- [ ] **Step 3: Implement the projection**

Add a small core helper that iterates the already selected `JointBatchRow.runs`
and returns detached dictionaries. Resolve source path from the run's
`results_summary`/`parameters`/`output_dir` using existing stored fields, never
from a guessed filename. Attach this projection to each summary row and to the
top-level report. Do not alter `collect_joint_dataset()`'s batch grouping or
latest-run selection.

Update the export writer to include `source_preflight` as a JSON/CSV-safe
summary field. Preserve existing figure manifest publication and avoid sending
Qt objects into the core DTO.

- [ ] **Step 4: Run the focused core and export tests**

```powershell
python -m pytest -q tests/test_joint_hub_dataset.py tests/test_main_window_joint_diagnostics_mixin.py
```

Expected: all focused tests pass with the new detached provenance fields.

- [ ] **Step 5: Commit the projection change**

```powershell
python scripts/auto_commit.py --message "feat(joint): expose selected source preflight" --files polynexus/core/joint/dataset.py polynexus/gui/main_window_joint_diagnostics_mixin.py tests/test_joint_hub_dataset.py tests/test_main_window_joint_diagnostics_mixin.py
```

### Task 3: Separate `SKIP`, `DIFF`, and non-comparable validation

**Files:**
- Modify: `polynexus/core/joint/validation.py`
- Modify: `polynexus/core/joint/dataset.py`
- Modify: `polynexus/core/joint/conclusion.py`
- Test: `tests/test_joint_hub_dataset.py`

- [ ] **Step 1: Write failing validation tests**

Add tests for these exact cases:

```python
assert skipped.status == "SKIP"
assert skipped.passed is True
assert skipped.severity == "INFO"
assert report["ai_context"]["issue_count"] == 0
```

Use missing `delta_Hf` for `Tm_GT` and missing `L_corr` for
`L_consistency`. Add a non-comparable condition fixture and assert its row has
`status == "NOT_COMPARABLE"` without an automatic technique winner.

- [ ] **Step 2: Run the focused tests and verify the failure**

```powershell
python -m pytest -q tests/test_joint_hub_dataset.py -k "skip or comparable"
```

Expected: current rows have warning-like skipped checks and the new status
assertions fail.

- [ ] **Step 3: Implement status-aware validation**

Extend `CrossValidationResult` with a JSON-safe `status` defaulting to
`"OK"`. Return `status="SKIP"`, `severity="INFO"`, and `passed=True` for
missing inputs. Keep failed numeric comparisons as `status="DIFF"` while
retaining existing evidence-weighted WARN/ERROR severity. Add
`status="NOT_COMPARABLE"` at the dataset boundary when source conditions or
explicit evidence policy prevent comparison; do not infer identity from
filenames.

Update report serialization and AI-context aggregation to count only `DIFF`
and real technique issue rows as issues. The conclusion remains fail-closed,
but a report containing only `SKIP` rows must not become `conditional` because
of invented warnings.

- [ ] **Step 4: Run the focused validation matrix**

```powershell
python -m pytest -q tests/test_joint_hub_dataset.py tests/test_joint_lifecycle_closure.py tests/test_joint_real_data_lifecycle.py
```

Expected: focused Joint tests pass and skipped checks no longer inflate issue
counts.

- [ ] **Step 5: Commit the status change**

```powershell
python scripts/auto_commit.py --message "fix(joint): distinguish skipped checks from conflicts" --files polynexus/core/joint/validation.py polynexus/core/joint/dataset.py polynexus/core/joint/conclusion.py tests/test_joint_hub_dataset.py
```

### Task 4: Exclude assignment-limited solid-C and correct the PA6 fixture

**Files:**
- Modify: `polynexus/core/joint/dataset.py`
- Modify: `tests/test_joint_real_data_lifecycle.py`
- Test: `tests/test_joint_hub_dataset.py`

- [ ] **Step 1: Write the failing solid-C and fixture tests**

Add a test with an NMR run whose structure evidence has
`Xc_assignment_status="assignment_limited"` and an `Xc_pct` value. Assert the
Joint summary retains the NMR evidence but leaves `nmr_Xc_pct` unavailable and
does not emit an NMR Xc comparison row. Update the real fixture source
resolver to require a path under `saxs/普通小角` containing `PA6` and add an
assertion that the resolved path does not contain `PAD8` or `8-000-s`.

- [ ] **Step 2: Run the focused tests and verify the failure**

```powershell
python -m pytest -q tests/test_joint_hub_dataset.py tests/test_joint_real_data_lifecycle.py -k "nmr or real"
```

Expected: the current report exposes the assignment-limited NMR Xc and the
real fixture resolver selects the unrelated first `8-000-s` source.

- [ ] **Step 3: Implement the gate and fixture correction**

Make `_xc_pct_for(row, "nmr")` return `NaN` whenever the run's structure
evidence is assignment-limited or its axis is uncalibrated. Keep the run in
`source_preflight` and issue families. Change `_real_sources()` to select the
PA6 static SAXS path under `普通小角` and preserve source/run provenance.

- [ ] **Step 4: Run the focused real-data checks**

```powershell
python -m pytest -q tests/test_joint_hub_dataset.py tests/test_joint_real_data_lifecycle.py
```

Expected: all focused tests pass; the lifecycle still proves transport only and
does not imply scientific approval.

- [ ] **Step 5: Commit the source/gate change**

```powershell
python scripts/auto_commit.py --message "fix(joint): gate limited NMR Xc and use PA6 fixture" --files polynexus/core/joint/dataset.py tests/test_joint_hub_dataset.py tests/test_joint_real_data_lifecycle.py
```

### Task 5: Full task verification and checkpoint

**Files:**
- Modify: only files listed by the actual implementation diff.
- Update: `docs/acceptance/2026-08-01-joint-selection-and-semantics.md`
- Update: `docs/agent/memory/active-work.md` and `current-state.md` only for durable facts that changed.

- [ ] **Step 1: Run the focused GUI/core/real matrix**

```powershell
python -m pytest -q tests/test_joint_hub_dataset.py tests/test_joint_analysis_hub.py tests/test_joint_coordinator.py tests/test_joint_figure_provider.py tests/test_joint_lifecycle_closure.py tests/test_joint_real_data_lifecycle.py
```

Expected: complete pytest summary with exit code `0`.

- [ ] **Step 2: Run the structured verifier and boundary audit**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-01-joint-selection-and-semantics.md --changed --types
python scripts/boundary_audit.py --root D:\PolyNexus --json
git diff --check
```

Expected: verifier exit `0`, quality/preprocessing and required static checks
pass, boundary audit exit `0`, and no whitespace errors.

- [ ] **Step 3: Update acceptance evidence with exact outputs**

Record only complete summaries and exit codes. State that this task proves
selection/source provenance and status separation, not scientific precedence or
publication approval.

- [ ] **Step 4: Create the explicit final allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "feat(joint): require explicit source selection" --files polynexus/core/joint/__init__.py polynexus/core/joint/conclusion.py polynexus/core/joint/dataset.py polynexus/core/joint/validation.py polynexus/gui/main_window_joint_diagnostics_mixin.py polynexus/gui/widgets/joint_analysis_hub.py tests/test_joint_analysis_hub.py tests/test_joint_hub_dataset.py tests/test_joint_real_data_lifecycle.py docs/agent/tasks/2026-08-01-joint-selection-and-semantics.md docs/acceptance/2026-08-01-joint-selection-and-semantics.md docs/superpowers/plans/2026-08-01-joint-selection-and-semantics.md
```

Do not include pre-existing user changes, generated outputs, real datasets, or
temporary test directories.
