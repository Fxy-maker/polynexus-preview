# SAXS Static Figure Dirty Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the static SAXS Figure provider tolerate per-element q/intensity conversion failures without changing scientific eligibility or publication semantics.

**Architecture:** Keep the hardening at the existing `figure_static._numeric_pairs` boundary. A private helper creates a detached float projection with invalid elements represented as `NaN`; the existing paired finite/positive/minimum checks remain unchanged and determine whether a Figure is emitted.

**Tech Stack:** Python, NumPy, pytest, repository `scripts/verify.py`, explicit-allowlist `scripts/auto_commit.py`.

---

### Task 1: Prove the dirty static Figure failure

**Files:**
- Modify: `tests/test_saxs_static_figure_panels.py`
- Do not modify production code in this task.

- [x] **Step 1: Add a failing regression test**

Append a test that replaces the first static frame's q/intensity lists with
object arrays containing invalid tokens, then asks the real static provider to
build definitions:

```python
def test_dirty_projection_keeps_valid_static_pairs() -> None:
    engine = _static_engine()
    engine._q_list[0] = np.asarray(["0.10", "bad-q", "0.40", "0.80"], dtype=object)
    engine._I_list[0] = np.asarray(["100.0", "70.0", "bad-intensity", "8.0"], dtype=object)

    definitions = build_static_saxs_figure_definitions(engine)
    comparison = next(item for item in definitions if item.figure_id == "saxs.static.comparison")
    profile = next(
        source for source in comparison.data_sources
        if source.source_id == "static-frame-000-profile"
    )

    assert profile.values["q_nm1"] == (0.1, 0.8)
    assert profile.values["intensity_au"] == (100.0, 8.0)


def test_all_invalid_static_profile_remains_fail_closed() -> None:
    engine = _static_engine()
    engine._q_list[0] = np.asarray(["bad-q", "also-bad"], dtype=object)
    engine._I_list[0] = np.asarray(["bad-intensity", "also-bad"], dtype=object)

    definitions = build_static_saxs_figure_definitions(engine)

    comparison = next(item for item in definitions if item.figure_id == "saxs.static.comparison")
    assert "static-frame-000-profile" not in {
        source.source_id for source in comparison.data_sources
    }
```

- [x] **Step 2: Run the focused test and verify RED**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_static_figure_dirty_red'
python -m pytest -q tests/test_saxs_static_figure_panels.py -k dirty_projection
```

Expected: the first test fails with the existing `ValueError` from
`np.asarray(..., dtype=float)`; the all-invalid test may pass because it is
already fail-closed. Record the exact summary and do not count a collection
error as RED evidence.

### Task 2: Add the minimal elementwise projection

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_static.py` near `_numeric_pairs`.

- [x] **Step 1: Add the private helper**

Place this helper immediately before `_numeric_pairs`:

```python
def _elementwise_float_array(values: Any) -> np.ndarray:
    source = np.asarray(values).reshape(-1)
    projected = np.full(source.shape, np.nan, dtype=float)
    for index, value in enumerate(source):
        try:
            projected[index] = float(value)
        except (OverflowError, TypeError, ValueError):
            continue
    return projected
```

- [x] **Step 2: Route both numeric-pair inputs through the helper**

Replace only the two whole-array conversions in `_numeric_pairs`:

```python
    try:
        x = _elementwise_float_array(x_values)
        y = _elementwise_float_array(y_values)
    except (TypeError, ValueError):
        return None
```

Keep the existing length, finite, positive, minimum-count, and return logic
unchanged.

- [x] **Step 3: Run focused GREEN and the clean regression**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_static_figure_dirty_green'
python -m pytest -q tests/test_saxs_static_figure_panels.py -k dirty_projection
python -m pytest -q tests/test_saxs_static_figure_panels.py
```

Expected: both dirty tests pass and the complete static panel file passes.

### Task 3: Verify the task and record evidence

**Files:**
- Modify: `docs/agent/tasks/2026-07-29-saxs-static-figure-dirty-projection.md`
- Create: `docs/acceptance/2026-07-29-saxs-static-figure-dirty-projection.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run the structured verifier**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-static-figure-dirty-projection.md --changed --types
```

Expected: exit code `0`; report exact quality/preprocessing counts, Ruff,
compile, type, task, and whitespace results. If any test fails, repair with a
new regression cycle before proceeding.

- [x] **Step 2: Run the exact SAXS matrix with external storage**

Run the repository's SAXS test matrix using a unique external basetemp under
`D:\PolyNexus-test-runs` or an explicitly named external directory. Report a
pass only if pytest prints its final summary and exits `0`; otherwise record
timeout/no-summary accurately.

- [x] **Step 3: Run non-destructive storage and diff checks**

Run:

```powershell
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
git status --short
```

The clean command must remain dry-run. Do not execute `--apply`, delete,
move, or migrate any test directory.

- [x] **Step 4: Write acceptance evidence and update active work**

Record exact RED/GREEN/verifier/matrix/storage outcomes, the unchanged
scientific gates, known limitations, and the pre-existing workspace changes in
the acceptance note and task card. Add one concise active-work entry pointing
to this task and its evidence; do not edit `current-state.md`.

- [x] **Step 5: Inspect the explicit diff allowlist**

Run:

```powershell
git diff -- polynexus/core/saxs_engine/figure_static.py tests/test_saxs_static_figure_panels.py docs/agent/tasks/2026-07-29-saxs-static-figure-dirty-projection.md docs/superpowers/specs/2026-07-29-saxs-static-figure-dirty-projection-design.md docs/superpowers/plans/2026-07-29-saxs-static-figure-dirty-projection.md docs/acceptance/2026-07-29-saxs-static-figure-dirty-projection.md docs/agent/memory/active-work.md
```

Confirm no unrelated or parallel path is present before checkpointing.

- [x] **Step 6: Create the checkpoint**

After all verification evidence is recorded, run only with the explicit
allowlist:

```powershell
python scripts/auto_commit.py `
  --message "fix(saxs): tolerate dirty static figure profiles" `
  --files `
    polynexus/core/saxs_engine/figure_static.py `
    tests/test_saxs_static_figure_panels.py `
    docs/agent/tasks/2026-07-29-saxs-static-figure-dirty-projection.md `
    docs/superpowers/specs/2026-07-29-saxs-static-figure-dirty-projection-design.md `
    docs/superpowers/plans/2026-07-29-saxs-static-figure-dirty-projection.md `
    docs/acceptance/2026-07-29-saxs-static-figure-dirty-projection.md `
    docs/agent/memory/active-work.md
```

Expected: one local commit containing only the allowlisted changed files; no
push, merge, deploy, or cleanup of unrelated worktree files.
