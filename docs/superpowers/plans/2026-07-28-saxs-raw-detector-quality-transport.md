# SAXS Raw Detector Quality Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transport explicit EDF raw-detector quality evidence through SAXS preprocessing and aligned frame/series results without changing scientific gates.

**Architecture:** `preprocess_pipeline` creates the existing raw-detector quality DTO from the image, `_build_mask()` output, and explicit header fields. `SAXSEngine` keeps a parallel report list aligned with loaded frames, while temperature and strain APIs attach reports by their existing source indices before calling their existing series aggregators.

**Tech Stack:** Python, NumPy, dataclasses, pytest, repository verifier, EDF/fabio reader.

---

### Task 1: Add the failing raw-detector contract tests

**Files:**
- Create: `tests/test_saxs_raw_detector_quality_transport.py`

- [x] **Step 1: Write tests for header-backed preprocessing and alignment.**

```python
def test_preprocess_pipeline_publishes_explicit_raw_detector_report(monkeypatch):
    processed = preprocess_pipeline(
        image,
        cfg,
        detector_header={"Saturation": "9", "Center_1": "2", "Center_2": "2"},
    )
    report = processed["detector_quality_report"]
    assert report["source_kind"] == "raw_detector"
    assert report["saturation_detection_available"] is True
    assert report["saturated_pixel_count"] == 1
    assert report["beam_center"] == [2.0, 2.0]
    json.dumps(report, allow_nan=False)
```

The test image contains one explicit `_build_mask()` dummy pixel and one
explicit saturation pixel. Add companion assertions for a header without
`Saturation`/center fields (`detector_saturation_unknown` and
`beam_center_missing`) and for an image whose maximum is not a declared limit.
Add a small engine test that two loaded image reports stay aligned with two
conditions and that temperature/strain results retain the reports by source
index. Keep the existing sector-map source-kind assertion in the same focused
file.

- [x] **Step 2: Run the focused tests and record the expected RED.**

Run: `python -m pytest -q tests/test_saxs_raw_detector_quality_transport.py -vv`

Expected before production changes: FAIL because `preprocess_pipeline` does
not accept `detector_header` and does not return `detector_quality_report`.

### Task 2: Implement the minimum preprocessing transport

**Files:**
- Modify: `polynexus/core/saxs_engine/preprocess.py`

- [x] **Step 1: Add read-only header helpers and an optional keyword.**

Normalize only known header key spellings, convert explicit finite saturation,
and return a center only when both known center fields are finite. Call
`build_detector_quality_report(image, mask=_build_mask(image, cfg),
saturation_value=..., source_kind="raw_detector", beam_center=...)` and put
`report.to_dict()` in the payload. Do not alter any integration arrays.

- [x] **Step 2: Run the focused contract tests.**

Run: `python -m pytest -q tests/test_saxs_raw_detector_quality_transport.py -vv`

Expected: preprocessing contract tests PASS; engine alignment tests may still
fail until Task 3 is complete.

### Task 3: Preserve aligned reports in SAXSEngine and series APIs

**Files:**
- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/core/saxs_batch_helpers.py`
- Modify: `polynexus/core/saxs_export_bundle.py`
- Modify: `polynexus/core/saxs_engine/core.py`
- Modify: `polynexus/core/saxs_engine/figure_evidence.py`
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`

- [x] **Step 1: Store one report slot per loaded frame and keep source kinds separate.**

Initialize/reset `_detector_quality_reports` beside `_sector_data_list`, append
the preprocessing report for image frames and `None` for 1D frames, including
the directory fallback path. Pass `detector_header=header` at every image
preprocessing call. For single-frame preprocessing publish the same report in
`result.raw_data` and assign it to the `SAXSResult` after `analyze_single`.

- [x] **Step 2: Add optional aligned report inputs to temperature and strain.**

Accept `detector_quality_reports=None` after the existing optional series
arguments. Sort the report list with the same `sort_idx` as the q/I inputs, set
each point's raw report from its original `source_index`, and leave `None` when
the slot is absent. Run the already existing
`build_series_detector_quality_report` unchanged for raw reports while
preserving the existing sector-map report field.

- [x] **Step 3: Pass reports from engine entry points.**

Pass the list from `analyze_temperature` and `analyze_strain`; set each static
batch `SAXSResult.raw_detector_quality_report` from its matching slot before
existing evidence copying. Add the field to `saxs_batch_helpers.py` and
`SAXSResult`. Do not pass sector-map payloads through this list.

- [x] **Step 4: Run focused tests and the existing 2D propagation tests.**

Run: `python -m pytest -q tests/test_saxs_raw_detector_quality_transport.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_2d_detector_orientation_evidence.py -vv`

Expected: all focused tests PASS and sector-map reports remain
`source_kind="sector_map"`.

### Task 4: Verify real and repository boundaries

**Files:**
- Modify: `docs/agent/tasks/2026-07-28-saxs-raw-detector-quality-transport.md`

- [x] **Step 1: Run the exact SAXS matrix.**

Run: `python -m pytest -q tests/test_saxs*.py tests/test_saxs_* -q` using an
external pytest temp root if the repository has an active basetemp lock.
Record the actual count, warnings, and exit code.

- [x] **Step 2: Run the structured verifier.**

Run: `python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-raw-detector-quality-transport.md --changed --types`

Record whether the check passed, timed out, or failed; do not classify an
unfinished full verifier as a pass.

- [x] **Step 3: Replay PAD8 without writing into the repository.**

Run the existing real SAXS replay/walkthrough command with an external output
directory. Confirm five source-aligned raw reports, explicit saturation
availability from the EDF headers, and conservative quality levels. Confirm
the existing sector-map reports remain sector-map reports.

- [x] **Step 4: Review the diff and create the explicit checkpoint.**

Use `git diff --check`, `git diff --stat`, and `git diff --name-only` to confirm
only the allowlist changed. After fresh verification, run:

```powershell
python scripts/auto_commit.py `
  --message "feat(saxs): transport raw detector quality evidence" `
  --files docs/agent/tasks/2026-07-28-saxs-raw-detector-quality-transport.md docs/superpowers/specs/2026-07-28-saxs-raw-detector-quality-transport-design.md docs/superpowers/plans/2026-07-28-saxs-raw-detector-quality-transport.md polynexus/core/saxs_engine/preprocess.py polynexus/core/saxs.py polynexus/core/saxs_batch_helpers.py polynexus/core/saxs_export_bundle.py polynexus/core/saxs_engine/core.py polynexus/core/saxs_engine/figure_evidence.py polynexus/core/saxs_engine/saxs_temperature.py polynexus/core/saxs_engine/saxs_strain.py tests/test_saxs_raw_detector_quality_transport.py
```

Record the resulting commit hash and leave unrelated tracked/untracked files
untouched.

Checkpoint created: `ebff128`; the helper staged and committed only the
allowlist above and did not push.
