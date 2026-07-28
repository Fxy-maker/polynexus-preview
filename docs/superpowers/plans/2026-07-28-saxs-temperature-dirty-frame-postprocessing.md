# SAXS Temperature Dirty-Frame Post-Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reuse the existing deterministic q/I sanitizer for temperature-series post-processing while retaining original dirty-input provenance.

**Architecture:** `analyze_single()` remains the owner of frame analysis and original quality reporting. `analyze_temperature_series()` creates a detached sanitized auxiliary profile for only the reference, invariant, and peak-tracking consumers that currently bypass the cleaned result. No new evidence or physics contract is added.

**Tech Stack:** Python, NumPy, pytest, SAXS quality contracts, repository verifier.

---

### Task 1: Establish the dirty-frame regression

**Files:**
- Create: `tests/test_saxs_temperature_dirty_frame_postprocessing.py`
- Read: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Read: `polynexus/core/saxs_engine/saxs_temperature.py`

- [x] **Step 1: Write the failing test.** Build a two-frame temperature fixture with q/I containing NaN, a non-positive intensity, and an unsorted pair. Monkeypatch `analyze_single()` with a frame result whose quality report is built from the original arrays. Monkeypatch invariant and Bragg helpers to assert `np.all(np.isfinite(q))`, `np.all(q > 0)`, `np.all(np.isfinite(I))`, and `np.all(I > 0)` before returning a finite value.

```python
def test_temperature_postprocessing_uses_surviving_profile_and_keeps_quality_actions(monkeypatch):
    from types import SimpleNamespace

    import numpy as np
    from polynexus.core.saxs_engine.config import SAXSConfig
    from polynexus.core.saxs_engine.core import LongPeriodResult, StructureParams
    from polynexus.core.saxs_engine.saxs_quality_contracts import build_data_quality_report
    from polynexus.core.saxs_engine.saxs_temperature import analyze_temperature_series

    q = np.array([0.04, np.nan, 0.02, 0.03], dtype=float)
    intensity = np.array([4.0, 5.0, -1.0, 3.0], dtype=float)
    seen = []

    def fake_analyze(q_values, intensity_values, cfg):
        del cfg
        report = build_data_quality_report(q_values, intensity_values)
        return SimpleNamespace(
            long_period=LongPeriodResult(L_best=10.0, L_confidence=0.8, method_used="bragg"),
            structure=StructureParams(L=10.0, lc=3.0, la=7.0, phi_c=0.3, confidence_lc=0.8),
            guinier_evidence=None,
            data_quality_report=report.to_dict(),
            metric_evidence={},
            detector_quality_report=None,
            orientation_evidence=None,
        )

    def invariant(q_values, intensity_values, cfg=None):
        del cfg
        assert np.all(np.isfinite(q_values))
        assert np.all(q_values > 0)
        assert np.all(np.isfinite(intensity_values))
        assert np.all(intensity_values > 0)
        seen.append((q_values.copy(), intensity_values.copy()))
        return 2.0

    import polynexus.core.saxs_engine.saxs_temperature as module
    monkeypatch.setattr(module, "analyze_single", fake_analyze)
    monkeypatch.setattr(module, "scattering_invariant", invariant)
    monkeypatch.setattr(module, "bragg_long_period", lambda q_values, i_values: (10.0, 0.6, {}))

    result = analyze_temperature_series(
        [170.0, 180.0], [q, q.copy()], [intensity, intensity.copy()], cfg=SAXSConfig()
    )
    assert result.Q_star_array.tolist() == [2.0, 2.0]
    assert seen
    assert "invalid_pairs_dropped" in result.temp_points[0].data_quality_report["actions"]
```

- [x] **Step 2: Run the RED test.**

Run:

```powershell
python -m pytest tests/test_saxs_temperature_dirty_frame_postprocessing.py::test_temperature_postprocessing_uses_surviving_profile_and_keeps_quality_actions -q --basetemp D:\PolyNexus\PolyNexus_saxs_temperature_dirty_postprocess_20260728
```

Expected: FAIL because the current temperature post-processing passes the raw dirty arrays into the patched invariant/Bragg helpers, so the finite-input assertion fails and the frame becomes unavailable.

### Task 2: Route post-processing through the existing sanitizer

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py` near the temperature loop and reference calculations.
- Test: `tests/test_saxs_temperature_dirty_frame_postprocessing.py`

- [x] **Step 1: Add the existing contract import.** Import `sanitize_1d_profile` from `saxs_quality_contracts`; do not add a second sanitizer.
- [x] **Step 2: Create one auxiliary profile per sorted frame.** Preserve `q_sorted`/`I_sorted` as original inputs for `analyze_single()`, and create `sanitized_sorted` with each item containing only `sanitize_1d_profile(q, I).q` and `.intensity`.
- [x] **Step 3: Use the auxiliary arrays only at post-processing call sites.** Use the reference item's sanitized arrays for `scattering_invariant()` and `bragg_long_period()`, the current item's arrays for `_safe_temperature_invariant()`, and the current item's arrays for `I_peak_tracking` lookup. If a sanitized profile is empty, pass empty arrays through existing fail-closed helpers and do not fabricate a value.

```python
sanitized_sorted = [sanitize_1d_profile(q, I) for q, I in zip(q_sorted, I_sorted)]
reference_profile = sanitized_sorted[ref_idx]
Q_solid, reference_invariant_warning = _safe_temperature_invariant(
    reference_profile.q,
    reference_profile.intensity,
    cfg,
    warning_code="temperature_reference_invariant_unavailable",
)
L_solid, _, _ = bragg_long_period(reference_profile.q, reference_profile.intensity)
# Continue through the existing reference-warning and frame loop logic.
profile = sanitized_sorted[i]
Q_star, invariant_warning = _safe_temperature_invariant(
    profile.q,
    profile.intensity,
    cfg_corrected,
    warning_code="temperature_frame_invariant_unavailable",
)
# Keep the existing phase and evidence aggregation unchanged.
idx = np.argmin(np.abs(profile.q - q_star))
I_peak_tracking[i] = profile.intensity[idx]
```

### Task 3: Verify fail-closed and clean-path boundaries

**Files:**
- Test: `tests/test_saxs_temperature_dirty_frame_postprocessing.py`
- Test: `tests/test_saxs_temperature_guinier_evidence.py`

- [x] **Step 1: Add the empty-profile regression.** Supply an all-invalid frame and assert it remains `Unusable`, retains its existing quality actions, and does not receive a fabricated `Q_star` or peak intensity.
- [x] **Step 2: Add a clean-path/source-order regression.** Use unsorted temperatures with clean q/I and assert temperature sorting and `source_index` mapping remain unchanged.
- [x] **Step 3: Run focused GREEN tests.** Confirm the dirty frame is salvaged only for existing post-processing metrics, while missing evidence and original quality defects remain explicit.

### Task 4: Full verification and checkpoint

**Files:**
- Update: task card, spec, plan, `docs/agent/memory/active-work.md`, and `docs/agent/memory/current-state.md`.

- [x] **Step 1: Run focused and exact SAXS matrices with isolated basetemp.** The focused temperature matrix returned `14 passed, 1 warning`; the exact SAXS matrix returned `425 passed, 8 warnings` in `31.15s`.
- [x] **Step 2: Run the task-scoped verifier and `git diff --check`.** The verifier exited `0` with quality `283`, preprocessing `106`, Ruff/compile/type, memory/task, and whitespace checks passing; the embedded runtime required process-local `Scripts` PATH injection.
- [x] **Step 3: Run fresh `--full --boundary`.** The fresh D:-isolated verifier returned `2869 passed, 17 skipped, 12 warnings` in `1686.81s`, exit code `0`; boundary audit passed.
- [x] **Step 4: Review cumulative diff and create one `scripts/auto_commit.py` checkpoint using only the explicit allowlist.** Leave parallel GUI/Joint/editor/scratch files untouched; the allowlisted checkpoint is created for this task.

### Verification record

The TDD RED was `1 failed, 3 warnings`; the focused dirty/empty regression was
`2 passed`; exact SAXS was `425 passed, 6 warnings`. A direct dirty-profile
replay returns finite `Q_star` values and preserves the original defect
actions. Fresh full/boundary passed `2869 passed, 17 skipped, 12 warnings` and
the boundary audit passed.
