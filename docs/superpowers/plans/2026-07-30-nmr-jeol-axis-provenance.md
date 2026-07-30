# NMR JEOL Axis Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve raw JEOL axis metadata and make the NMR ppm-axis calibration boundary explicit.

**Architecture:** Keep parsing in `nmr_engine.io`, carry the JSON-safe axis status through the NMR run projection, and publish it in the existing NMR evidence bundle. The fallback remains the current default axis whenever vendor units are not explicitly confirmed.

**Tech Stack:** Python, NumPy, pytest, existing PolyNexus evidence contracts.

---

### Task 1: Add the failing real-file and evidence tests

**Files:**
- Modify: `tests/test_nmr_engine.py`
- Test: `测试数据/NMR/固体nmr碳谱/CXD_20250409_HC_cpmas-1-1.jdf`

- [x] **Step 1: Write tests for raw JEOL fields and fail-closed axis status**

```python
def test_jeol_solid_c_exposes_raw_axis_fields_without_claiming_ppm_calibration():
    path = _nmr_root() / "固体nmr碳谱" / "CXD_20250409_HC_cpmas-1-1.jdf"
    spec = load_project(str(path), sample_state="solid", nucleus="13C")[0]

    params = spec.metadata["params"]
    assert params["SCANS"] is not None
    assert np.isfinite(params["X_OFFSET"])
    assert np.isfinite(params["X_SWEEP"])
    assert spec.metadata["ppm_axis_source"] == "default_range"
    assert spec.metadata["ppm_axis_reason"] == "jeol_metadata_units_unconfirmed"
    assert spec.metadata["ppm_axis_calibrated"] is False
```

- [x] **Step 2: Run the focused test and confirm the failure is the missing record parse or provenance fields**

Run: `python -m pytest tests/test_nmr_engine.py -q -k jeol_solid_c_exposes_raw_axis_fields_without_claiming_ppm_calibration`

Expected: FAIL because the current reader returns `None` for the real JEOL record fields and does not expose the axis provenance keys.

### Task 2: Implement the minimal reader and evidence contract

**Files:**
- Modify: `polynexus/core/nmr_engine/io.py`
- Modify: `polynexus/core/nmr.py`
- Modify: `polynexus/core/analysis_evidence_nmr.py`

- [x] **Step 1: Read observed 64-byte records without changing payload interpretation**

Support the real record alignment and preserve raw integer/double/text values in `params`. Keep the old alignment as a compatibility fallback.

- [x] **Step 2: Add an explicit default-axis reason and calibration boolean**

Set `ppm_axis_source`, `ppm_axis_reason`, `ppm_axis_units`, and `ppm_axis_calibrated` from the existing safe axis decision. Do not use frequency-like values as ppm.

- [x] **Step 3: Project the status through NMR parameters and evidence**

Expose the values through the NMR run projection and `_nmr_analysis_bundle()`
contracts so Results, export, and history receive the same provenance.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/acceptance/2026-07-30-nmr-jeol-axis-provenance.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run focused reader/evidence tests**

Run: `python -m pytest tests/test_nmr_engine.py -q`

- [x] **Step 2: Run real lifecycle tests**

Run: `python -m pytest tests/test_nmr_lifecycle_closure.py -q`

- [x] **Step 3: Run the structured verifier and create the explicit allowlist checkpoint**

Run: `python scripts/verify.py --task docs/agent/tasks/2026-07-30-nmr-jeol-axis-provenance.md --changed --types`

Then run `python scripts/auto_commit.py --message "feat(nmr): expose JEOL axis provenance" --files ...` with only the allowlist files above.
