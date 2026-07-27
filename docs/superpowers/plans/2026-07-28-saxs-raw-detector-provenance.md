# SAXS Raw Detector Geometry and Mask Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transport explicit raw-detector geometry and mask provenance through the detector report and Figure evidence without changing scientific gates.

**Architecture:** The quality contract carries optional JSON-safe mappings. Preprocessing builds them from the original header, effective `SAXSConfig`, and the existing `_build_mask()` output; Figure evidence projects them through its detector allowlist. Sector-map reports keep their existing source and behavior.

**Tech Stack:** Python, dataclasses, NumPy, pytest, strict JSON serialization, repository verifier.

---

### Task 1: Establish the provenance contract tests

**Files:**
- Modify: `tests/test_saxs_raw_detector_quality_transport.py`

- [x] **Step 1: Add a complete-header test.**

Call `preprocess_pipeline` with a two-dimensional image and explicit
`WaveLength`, `PixelSize`, `SampleDistance`, `Center_1`, and `Center_2` header
values. Assert `geometry_provenance["source"] == "header"`, every field source
is `header`, the effective values are present, the mask source is
`saxs_config.dummy_value`, and strict JSON serialization succeeds.

- [x] **Step 2: Add mixed/invalid/none mask tests.**

Use a header containing only wavelength and an invalid pixel size. Assert the
per-field states are `header`, `invalid_header`, or `config_default` as
applicable and that `validity` stays `not_assessed`. Use a config with
`dummy_val=np.nan` to assert mask source `none`, `configured is False`, and
`shape is None`; do not assert any inferred mask pixels.

- [x] **Step 3: Add Figure allowlist and sector separation assertions.**

Build a frame and series with a raw report containing both provenance mappings.
Assert both appear in frame and series records and strict JSON serialization
passes. Build a sector-map report without provenance and assert it does not gain
either field.

- [x] **Step 4: Run the tests before production edits.**

Run:

```powershell
python -m pytest -q tests/test_saxs_raw_detector_quality_transport.py -vv --basetemp C:\Temp\PolyNexus_saxs_raw_detector_provenance_red
```

Expected result: the new assertions fail because the report has no provenance
fields and the Figure allowlist drops unknown keys; existing tests may pass.

### Task 2: Add optional detector-report provenance fields

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`

- [x] **Step 1: Extend the dataclass and builder.**

Add `geometry_provenance: Mapping[str, Any] | None = None` and
`mask_provenance: Mapping[str, Any] | None = None` after the existing detector
fields. Add matching optional keyword parameters to
`build_detector_quality_report` and pass them into the dataclass. Keep defaults
`None` so sector-map and legacy callers remain unchanged.

- [x] **Step 2: Run the focused tests.**

Run the RED command again. The direct contract assertions should now reach the
preprocessing payload and fail only for missing preprocessing construction or
Figure projection.

### Task 3: Build provenance at the preprocessing boundary

**Files:**
- Modify: `polynexus/core/saxs_engine/preprocess.py`

- [x] **Step 1: Add explicit header classification helpers.**

Normalize header keys using the same known aliases as geometry extraction,
classify each field without using image values, and serialize effective config
values as ordinary Python floats. Treat a missing key as `config_default` and a
present non-finite, non-positive, or unparseable value as `invalid_header`.
Convert the existing dummy-mask state to the `source/configured/shape` mapping.

- [x] **Step 2: Pass mappings to the existing report builder.**

Compute provenance beside the existing `_build_mask()` call and pass both
mappings to `build_detector_quality_report`. Do not alter integration, mask
construction, quality rules, or reason-code generation.

- [x] **Step 3: Run focused tests and inspect unchanged quality behavior.**

Run the focused test command and confirm existing level/reason assertions still
match. The expected new result is a fully passing focused suite with only the
repository's existing warnings.

### Task 4: Bind provenance to Figure evidence

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_evidence.py`

- [x] **Step 1: Extend the explicit detector allowlist.**

Add `geometry_provenance` and `mask_provenance` to `_DETECTOR_EVIDENCE_FIELDS`.
Do not broaden the projection to arbitrary detector keys and do not modify
sector-map generation.

- [x] **Step 2: Run the focused Figure assertions.**

Run the raw detector transport test file and confirm frame/series Figure
records retain both mappings while sector-map payloads remain separate.

### Task 5: Verify, record, and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-28-saxs-raw-detector-provenance.md`

- [x] **Step 1: Run the exact SAXS matrix.**

Run `python -m pytest -q tests/test_saxs_*.py -q` with an external basetemp and
record the actual count, warnings, and exit code.

- [x] **Step 2: Run the structured verifier and diff checks.**

Run the task-scoped `scripts/verify.py` command and `git diff --check`; record
only final readable results.

- [x] **Step 3: Review the allowlist and checkpoint.**

Confirm `git diff --name-only` contains only the explicit allowlist, then run:

```powershell
python scripts/auto_commit.py `
  --message "feat(saxs): transport detector provenance" `
  --files docs/agent/tasks/2026-07-28-saxs-raw-detector-provenance.md docs/superpowers/specs/2026-07-28-saxs-raw-detector-provenance-design.md docs/superpowers/plans/2026-07-28-saxs-raw-detector-provenance.md polynexus/core/saxs_engine/saxs_quality_contracts.py polynexus/core/saxs_engine/preprocess.py polynexus/core/saxs_engine/figure_evidence.py tests/test_saxs_raw_detector_quality_transport.py
```

Record the resulting commit hash and leave all pre-existing parallel files
untouched.
