# SAXS Temperature Frame Fail-Closed Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Isolate malformed temperature-frame invariant/reference calculations so unaffected 1D Guinier frames continue with explicit unavailable evidence.

**Architecture:** Keep the current temperature-series loop and output DTOs. Add narrow guarded calls around the existing reference and per-frame calculations; return `NaN` plus stable frame warnings on failure. No cross-frame fallback or scientific algorithm changes are introduced.

**Tech Stack:** Python, NumPy, pytest, existing SAXS quality contracts, repository verifier.

---

## File map

- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
  - Guard initial `scattering_invariant()` and `bragg_long_period()` references.
  - Guard each frame `scattering_invariant()` call.
  - Preserve existing arrays, source mapping, and downstream evidence builders.
- Modify: `tests/test_saxs_temperature_guinier_evidence.py`
  - Add middle-frame and reference-failure regressions.
- Modify: task/spec/plan only after verification. Durable memory is deliberately
  excluded because concurrent full-software audit edits are already present in
  both tracked memory files.

## Task 1: Middle-frame invariant failure RED

**Files:** `tests/test_saxs_temperature_guinier_evidence.py`

- [x] Add a test with three sorted temperatures and a monkeypatched invariant
  that raises only for the middle frame. Assert the result has three points,
  the middle `Q_star` is non-finite with a stable warning, and the final point
  still has its existing Guinier evidence and a finite `Q_star`.
- [x] Run:

```powershell
python -m pytest -q tests/test_saxs_temperature_guinier_evidence.py::<new_test>
```

Expected RED was observed: the injected invariant exception escaped from the
middle frame.

## Task 2: Reference failure RED

**Files:** `tests/test_saxs_temperature_guinier_evidence.py`

- [x] Add a test where the first invariant call and first long-period call
  raise, while later calls succeed. Assert all source frames remain present,
  later frames retain Guinier evidence, and the reference failure is represented
  by stable warning codes rather than a substituted reference.
- [x] Run the focused test and confirm RED for the unguarded reference calls.

## Task 3: Minimal GREEN implementation

**Files:** `polynexus/core/saxs_engine/saxs_temperature.py`

- [x] Add a local guarded-call helper near `analyze_temperature_series()`:

```python
def _safe_temperature_metric(call, *, warning_code, logger_message):
    try:
        value = call()
    except Exception:
        logger.warning(logger_message, exc_info=True)
        return np.nan, warning_code
    try:
        return (float(value), None) if np.isfinite(float(value)) else (np.nan, warning_code)
    except (TypeError, ValueError):
        return np.nan, warning_code
```

- [x] Use it for the initial invariant and long-period reference, retaining
  warning codes until the first `TemperaturePointResult` is created.
- [x] Use it around each frame invariant calculation. Set `tp.Q_star` to the
  returned value, append the warning code when present, and leave existing
  crystallinity logic unchanged so invalid references produce unavailable
  `Xc_relative` rather than a fabricated ratio.
- [x] Do not modify `analyze_single()`, sorting, sequence evidence, or quality
  thresholds.

## Task 4: GREEN and regression verification

- [x] Run the two new tests and the existing temperature Guinier/status tests.
- [x] Run the consumer matrix listed in the task card.
- [x] Run the complete SAXS matrix with the dedicated basetemp.
- [ ] Run the structured verifier with the task card and inspect the exact
  output; record any existing warnings or basetemp limitations.

## Task 5: Checkpoint

- [x] Run `git diff --check` and review only the five-file allowlist.
- [x] Record exact results and the remaining scientific-review limitation in
  the task card. Do not touch concurrent `active-work.md` or
  `current-state.md` edits.
- [x] Run:

```powershell
python scripts/auto_commit.py `
  --message "fix(saxs): isolate temperature frame failures" `
  --files polynexus/core/saxs_engine/saxs_temperature.py `
    tests/test_saxs_temperature_guinier_evidence.py `
    docs/agent/tasks/2026-07-27-saxs-temperature-frame-fail-closed.md `
    docs/superpowers/specs/2026-07-27-saxs-temperature-frame-fail-closed-design.md `
    docs/superpowers/plans/2026-07-27-saxs-temperature-frame-fail-closed.md
```
