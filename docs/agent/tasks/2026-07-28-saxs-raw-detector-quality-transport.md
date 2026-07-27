# Task: SAXS raw detector quality transport

**Status:** checkpointed (`ebff128`)

## Goal

Preserve explicit EDF raw-detector quality evidence through the existing SAXS
frame and series result contracts.

## Affected boundaries

`polynexus/core/saxs_engine/preprocess.py` creates the report;
`polynexus/core/saxs.py` aligns reports with loaded frames;
`polynexus/core/saxs_engine/saxs_temperature.py` and
`polynexus/core/saxs_engine/saxs_strain.py` attach source-indexed reports; and
`polynexus/core/saxs_batch_helpers.py`,
`polynexus/core/saxs_engine/figure_evidence.py`, and
`polynexus/core/saxs_export_bundle.py` transport the separate raw field.

## Non-goals

- No detector saturation guessing from maxima or histogram shape.
- No inferred mask, interpolation, frame copying, or automatic rescue.
- No new physical threshold, quality-level promotion, Figure role, AI behavior,
  or publication eligibility change.
- No edits to real datasets, generated outputs, GUI review hints, scratch
  directories, or parallel work.

## Acceptance criteria

- [x] An EDF-backed preprocessing payload contains a strict JSON-safe
   `detector_quality_report` with `source_kind="raw_detector"`.
- [x] Explicit finite `Saturation` is counted; missing saturation remains unknown;
   the image maximum is never treated as a limit.
- [x] The existing `_build_mask()` result is counted without changing integration.
- [x] A header beam center is reported only when both coordinates are present;
   config defaults alone do not close that evidence gap.
- [x] Static, temperature, and strain routes retain frame alignment and reuse the
   existing series detector summary. Sector-map reports remain separate.
- [x] Existing quality and physical gates remain unchanged and real PAD8 replay
   remains conservative.

## Implementation plan

1. Add focused RED tests for explicit/missing EDF detector evidence and
   directory-frame alignment.
2. Add the read-only raw-detector report to preprocessing using only explicit
   header values and `_build_mask()`.
3. Transport the aligned raw field through static, temperature, and strain
   result DTOs while preserving sector-map evidence in its existing field.
4. Run focused tests, the SAXS matrix, the structured verifier, and an external
   PAD8 replay, then create the explicit allowlist checkpoint.

## Verification

Required commands:

```powershell
python -m pytest -q tests/test_saxs_raw_detector_quality_transport.py -vv
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-raw-detector-quality-transport.md --changed --types
git diff --check
```

The full/boundary verifier already running in another process is tracked
separately and is not treated as a pass until its final stdout and exit code
are available.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-28-saxs-raw-detector-quality-transport.md`
- `docs/superpowers/specs/2026-07-28-saxs-raw-detector-quality-transport-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-raw-detector-quality-transport.md`
- `polynexus/core/saxs_engine/preprocess.py`
- `polynexus/core/saxs.py`
- `polynexus/core/saxs_batch_helpers.py`
- `polynexus/core/saxs_export_bundle.py`
- `polynexus/core/saxs_engine/core.py`
- `polynexus/core/saxs_engine/figure_evidence.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_raw_detector_quality_transport.py`

## Verification record

- TDD RED: focused run with the shared repository basetemp produced `2 failed,
  1 error, 1 warning`; the two failures were the expected missing
  `detector_header` API. Re-running the directory case with external basetemp
  produced `1 failed`, caused by the absent aligned report list.
- TDD GREEN: `python -m pytest -q
  tests/test_saxs_raw_detector_quality_transport.py -vv --basetemp
  C:\Temp\PolyNexus_saxs_raw_detector_green2_20260728` -> `5 passed, 1
  warning`.
- Focused 2D matrix: raw transport plus existing 2D propagation/orientation
  tests -> `27 passed, 1 warning`.
- Exact SAXS matrix: all `tests/test_saxs_*.py` -> `371 passed, 5 warnings`.
  Warnings are the existing Arial CJK glyph warnings plus the focused missing
  geometry warning.
- Structured verifier: `python scripts/verify.py --task
  docs/agent/tasks/2026-07-28-saxs-raw-detector-quality-transport.md --changed
  --types` -> exit `0`; task/memory, Ruff, compile/type, quality `283 passed`,
  preprocessing `106 passed`, and whitespace all passed.
- Real PAD8 replay from `D:\PolyNexus\测试数据\saxs\PAD8原位拉伸` -> load and
  strain analysis succeeded with `5` aligned raw reports, each
  `source_kind=raw_detector`, explicit saturation and header beam center;
  raw series `source_kinds=["raw_detector"]`, level `Unusable`; sector series
  `source_kinds=["sector_map"]`; `validation_passed=True`; strict JSON passed.
- Full/boundary verifier started before this task remains in progress at
  checkpoint time (pytest child PID `18132`, no final summary yet). It is not
  counted as a pass.

## Checkpoint

`ebff128` was created by `scripts/auto_commit.py` with the explicit allowlist
below. No push was performed. The full/boundary process is intentionally not
part of the pass evidence until it exits with a readable summary.

## Known limitation

Header geometry presence is transport evidence, not scientific calibration
approval. Human review must still confirm detector geometry, mask validity, and
the meaning of the beamline saturation field before publication use.
