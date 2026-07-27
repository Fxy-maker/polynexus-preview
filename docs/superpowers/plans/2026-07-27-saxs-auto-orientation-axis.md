# SAXS Automatic In-Plane Orientation Axis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add configurable and conservative automatic in-plane orientation-axis detection to the SAXS Herman path.

**Architecture:** Keep axis resolution and detector-plane Herman math in the SAXS anisotropy core. Pass the existing `SAXSConfig` through the canonical strain adapter and expose axis provenance through the existing orientation evidence contract. The GUI and result-table transport remain unchanged.

**Tech Stack:** Python, NumPy, SciPy trapezoidal integration, pytest, existing PolyNexus verification scripts.

---

### Task 1: Add the scientific configuration and regression tests

**Files:**
- Modify: `polynexus/core/saxs_engine/config.py`
- Test: `tests/test_saxs_2d_detector_orientation_evidence.py`

- [x] **Step 1: Add tests for explicit and automatic axis behavior**

Create synthetic 36-bin azimuth profiles with a known axis and assert that an
explicit finite axis is reported as configured, a missing axis is detected
within one angular bin, and a flat profile is unavailable in auto mode.

- [x] **Step 2: Run the focused tests before implementation**

Run:

```powershell
python -m pytest tests/test_saxs_2d_detector_orientation_evidence.py -q
```

Expected: FAIL because `SAXSConfig` and `AnisotropyResult` do not yet expose
the selected-axis behavior.

- [x] **Step 3: Add optional config fields**

Add `orientation_axis_deg: Optional[float] = None`,
`orientation_auto_min_strength: float = 0.08`, and
`orientation_auto_min_bins: int = 12` beside the existing azimuth settings.

- [x] **Step 4: Run the tests again**

The tests should still fail on the missing core behavior, proving the tests
exercise the intended regression rather than only the dataclass field.

### Task 2: Implement core axis resolution and 2D Herman weighting

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_anisotropy.py`

- [x] **Step 1: Add a failing test for detector-plane weighting**

Use a synthetic profile concentrated around a configured 90° axis and assert
that the factor is materially positive; this fails with the legacy fixed-zero
axis and `abs(sin(chi))` weighting.

- [x] **Step 2: Implement the minimal helpers**

Add a helper that validates a profile, subtracts its tenth-percentile floor,
computes the normalized second harmonic, rejects weak/insufficient profiles,
and returns `(axis_deg, strength, confidence, source, reason)`. Add a helper
that computes the detector-plane Herman factor using
`phi = angle(chi - axis)` and direct baseline-subtracted intensity weights.

- [x] **Step 3: Resolve the axis in `analyze_anisotropy()`**

Use a finite `cfg.orientation_axis_deg` first. Otherwise call the automatic
helper on the selected q* profile. Store axis degree/source/strength/confidence
on `AnisotropyResult`; keep `f_herman` non-finite when automatic detection is
not reliable.

- [x] **Step 4: Publish axis provenance in evidence**

Include finite axis fields and the source string in the existing orientation
fit evidence. Preserve JSON-safe finite/None conversion and existing quality
levels.

- [x] **Step 5: Run focused tests**

Run:

```powershell
python -m pytest tests/test_saxs_2d_detector_orientation_evidence.py -q
```

Expected: PASS.

### Task 3: Connect the configured axis through strain transport

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`
- Test: `tests/test_saxs_batch_parameters.py`

- [x] **Step 1: Add a strain regression using a rotated synthetic 2D payload**

Call the existing strain-series entry point with `SAXSConfig` carrying an
explicit non-90° axis and assert the finite per-frame Herman result plus axis
evidence source `configured`.

- [x] **Step 2: Pass `cfg` into `herman_from_sector_data()`**

Extend the internal optional argument and forward it to
`analyze_anisotropy()` without changing the existing sector payload contract.

- [x] **Step 3: Run focused SAXS transport/table tests**

Run:

```powershell
python -m pytest tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_batch_parameters.py tests/test_saxs_results_table_service.py -q
```

Expected: all focused tests pass.

### Task 4: Verify, review, and checkpoint

**Files:**
- Review: all files in the task allowlist from the task card.

- [x] **Step 1: Run the complete SAXS matrix**

Run the task card's full SAXS command and record its exact count and warnings.

- [x] **Step 2: Run the structured verifier**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-auto-orientation-axis.md --changed --types
```

- [x] **Step 3: Inspect the cumulative diff**

Confirm only the explicit allowlist is staged and all pre-existing release,
memory, generated, and temporary files remain untouched.

- [x] **Step 4: Create the local checkpoint**

```powershell
python scripts/auto_commit.py `
  --message "feat(saxs): detect in-plane orientation axis" `
  --files polynexus/core/saxs_engine/config.py polynexus/core/saxs_engine/__init__.py polynexus/core/saxs_engine/saxs_anisotropy.py polynexus/core/saxs_engine/saxs_strain.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_batch_parameters.py docs/agent/tasks/2026-07-27-saxs-auto-orientation-axis.md docs/superpowers/specs/2026-07-27-saxs-auto-orientation-axis-design.md docs/superpowers/plans/2026-07-27-saxs-auto-orientation-axis.md
```

The checkpoint is local only; do not push or merge.
