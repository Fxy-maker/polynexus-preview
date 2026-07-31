# SAXS EDF Metadata and Pixel-Quality Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing SAXS EDF report with header-backed metadata and conservative processed-image classifications without changing scientific gates.

**Architecture:** Keep the current `header -> cfg -> preprocess -> DetectorQualityReport` flow. Add small normalization helpers and JSON-safe report fields at the existing boundaries; do not introduce a new DTO or duplicate reader refactor. Preserve per-frame report alignment already implemented by the raw-detector transport slice.

**Tech Stack:** Python, NumPy, dataclasses, pytest, EDF/fabio reader, repository verifier.

---

### Task 1: Add failing tests for the real-style EDF semantics

**Files:**
- Create: `tests/test_saxs_edf_metadata_quality.py`
- Modify: `tests/test_saxs_raw_detector_quality_transport.py`

- [ ] **Step 1: Write tests for metadata normalization and report fields.**

Use a real-style header mapping containing `DetectorModel`, `Saturation="0"`,
`CountCutoff`, `ThresholdSetting`, `FlatField`, `Dummy`, `DDummy`, and
`BackgroundCorrectionConstant`. Assert the desired normalized metadata and
that `geometry_provenance.validity` and `mask_provenance.validity` remain
`not_assessed`.

- [ ] **Step 2: Write the pixel-classification test.**

Construct an image containing repeated `-0.0024174`, one `-2.0`, one positive
pixel, and no zero values. Assert the raw nonpositive count remains visible,
the background-floor count is separated, and dummy-sentinel count is
separated.

- [ ] **Step 3: Write the saturation semantics test.**

Assert that `Saturation="0"` leaves saturation unresolved and does not count
zero pixels as saturated. Assert that an explicit positive `Saturation="9"`
still marks an image pixel equal to `9` as saturated, and that
`ThresholdSetting` alone never becomes the saturation threshold.

- [ ] **Step 4: Add the four-frame sequence regression.**

Use four temporary EDF files with the same header and distinct small image
arrays. Load them through the existing directory path and assert four report
slots, independent source paths, complete metadata inventory per frame, and no
cross-frame report reuse.

- [ ] **Step 5: Run the new tests and verify RED.**

Run:

```powershell
python -m pytest -q tests/test_saxs_edf_metadata_quality.py tests/test_saxs_raw_detector_quality_transport.py -vv
```

Expected: the new assertions fail because the metadata inventory and pixel
classification fields do not yet exist, while the existing transport tests
continue to identify the current behavior.

### Task 2: Normalize known EDF header fields without changing geometry behavior

**Files:**
- Modify: `polynexus/core/saxs_engine/io.py`
- Modify: `polynexus/core/saxs_engine/preprocess.py`

- [ ] **Step 1: Add a read-only known-field normalization helper.**

Normalize case and separator variants for the known fields, preserve raw text
where needed, convert finite numeric values only, and return JSON-safe values.
Do not treat `ThresholdSetting` as saturation. Add `Dummy` and `DDummy`
extraction so the EDF mask rule is used when explicitly present rather than
only the configuration default.

- [ ] **Step 2: Pass header-derived dummy configuration to the existing mask path.**

Create a copied config for per-image preprocessing, update only finite explicit
`Dummy`/`DDummy` values, and keep the existing `_build_mask()` algorithm. Do
not mutate a shared series config from one frame's header.

- [ ] **Step 3: Run the focused tests.**

Run:

```powershell
python -m pytest -q tests/test_saxs_edf_metadata_quality.py -vv
```

Expected: metadata and mask-source tests pass or advance to the report-field
assertions; no existing geometry tests regress.

### Task 3: Extend the detector report conservatively

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `polynexus/core/saxs_engine/preprocess.py`

- [ ] **Step 1: Add explicit classification counts to `DetectorQualityReport`.**

Add JSON-safe fields for `background_floor_pixel_count`,
`masked_sentinel_pixel_count`, and `unexpected_negative_pixel_count`. Keep
`nonpositive_pixel_count`, `masked_pixel_count`, and existing reason codes for
backward compatibility.

- [ ] **Step 2: Add metadata presence/source fields.**

Add a report payload containing normalized detector identity and processing
metadata plus `metadata_status` (`complete`/`partial`) and
`metadata_source="edf_header"` when fields are present. Keep geometry and mask
validity unchanged as `not_assessed`.

- [ ] **Step 3: Make saturation handling explicit.**

Only a finite positive `Saturation` value is an explicit saturation threshold.
For zero, absent, or invalid values, report the existing unknown state and
include `CountCutoff` only as metadata. Preserve the existing positive-value
test behavior.

- [ ] **Step 4: Run the focused RED-to-GREEN cycle.**

Run:

```powershell
python -m pytest -q tests/test_saxs_edf_metadata_quality.py tests/test_saxs_raw_detector_quality_transport.py -vv
```

Expected: all new metadata, classification, saturation, and transport tests
pass.

### Task 4: Verify four-frame and repository boundaries

**Files:**
- Modify: `docs/agent/tasks/2026-07-31-saxs-edf-metadata-quality-classification.md`

- [ ] **Step 1: Run the focused SAXS matrix.**

```powershell
python -m pytest -q tests/test_saxs_edf_metadata_quality.py tests/test_saxs_raw_detector_quality_transport.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_2d_evidence_propagation.py -vv
```

- [ ] **Step 2: Run the required structured verifier.**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-edf-metadata-quality-classification.md --changed --types
```

- [ ] **Step 3: Run `git diff --check` and inspect the allowlist.**

Confirm no unrelated pre-existing changes are staged or included.

- [ ] **Step 4: Create the atomic checkpoint.**

After verification, run:

```powershell
python scripts/auto_commit.py `
  --message "fix(saxs): classify EDF detector metadata and pixels" `
  --files docs/agent/tasks/2026-07-31-saxs-edf-metadata-quality-classification.md docs/superpowers/specs/2026-07-31-saxs-edf-metadata-quality-classification-design.md docs/superpowers/plans/2026-07-31-saxs-edf-metadata-quality-classification.md polynexus/core/saxs_engine/io.py polynexus/core/saxs_engine/preprocess.py polynexus/core/saxs_engine/saxs_quality_contracts.py tests/test_saxs_edf_metadata_quality.py
```
