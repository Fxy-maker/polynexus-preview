# Task: SAXS raw detector geometry and mask provenance transport

**Status:** checkpointed (fresh verification complete; checkpoint hash is reported in handoff)

## Goal

Carry explicit per-field detector geometry provenance and existing mask provenance
with the raw-detector quality report through preprocessing and Figure evidence.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`: optional JSON-safe
  provenance fields on the detector report.
- `polynexus/core/saxs_engine/preprocess.py`: read-only construction from the
  existing effective config, header, and `_build_mask()` result.
- `polynexus/core/saxs_engine/figure_evidence.py`: explicit allowlist transport.
- `tests/test_saxs_raw_detector_quality_transport.py`: regression coverage.

## Non-goals

- No detector calibration, geometry validity assessment, or beam-center
  scientific interpretation.
- No mask inference beyond the existing `saxs_config.dummy_value` mask result.
- No new threshold, quality-level change, physical gate, rescue, interpolation,
  frame copying, AI action, or publication approval.
- No changes to sector-map provenance; it remains separate from raw-detector
  provenance and receives no inferred geometry/mask fields.

## Acceptance criteria

- [x] Header-backed raw reports expose `geometry_provenance` with effective
  values, per-field `header`/`config_default`/`invalid_header` source labels,
  an aggregate `source`, and `validity="not_assessed"`.
- [x] Missing or invalid header fields are distinguished from accepted header
  fields without changing existing quality levels or reason codes.
- [x] Raw reports expose `mask_provenance` with `source` equal to
  `saxs_config.dummy_value` or `none`, configured state, image shape, and
  `validity="not_assessed"`.
- [x] All new nested values are strict JSON-safe, and existing sector-map
  reports remain free of raw geometry/mask claims.
- [x] Figure frame and series projections retain both provenance fields through
  the existing explicit allowlist.

## Implementation plan

1. [x] Add focused RED tests for complete, mixed, invalid, and absent geometry
   headers, configured/unconfigured masks, strict JSON, and Figure projection.
2. [x] Add optional provenance fields to `DetectorQualityReport` and its builder,
   preserving old callers and sector-map reports.
3. [x] Build provenance in raw preprocessing from explicit header parsing, effective
   config values, and the existing mask result without changing integration.
4. [x] Add the fields to the Figure evidence detector allowlist and verify source
   separation.
5. [x] Run focused tests, the exact SAXS matrix, the structured verifier, diff
   checks, and create the explicit allowlist checkpoint.

## Verification

Required commands:

```powershell
python -m pytest -q tests/test_saxs_raw_detector_quality_transport.py -vv --basetemp C:\Temp\PolyNexus_saxs_raw_detector_provenance
& python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName) --basetemp C:\Temp\PolyNexus_saxs_raw_detector_provenance_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-raw-detector-provenance.md --changed --types
git diff --check
```

The initial verifier invocation used repository `.pytest_tmp` and returned
`229 passed, 54 errors` because Windows denied cleanup of the pre-existing
`.pytest_tmp` directory while unrelated GUI/IR Python processes were alive.
The required verifier was then rerun with
`PYTEST_ADDOPTS=--basetemp=C:\Temp\PolyNexus_saxs_raw_detector_provenance_verify`
and exited `0`: task/memory, Ruff, compile/type, quality `283 passed`,
preprocessing `106 passed`, and whitespace all passed. An unrelated or
unfinished full/boundary process is not treated as evidence for this task.

## Verification record

- TDD RED: `4 failed, 5 passed, 2 warnings`; failures were the expected
  missing provenance fields and Figure allowlist projection.
- TDD GREEN: focused raw transport/provenance suite `9 passed, 2 warnings`.
- Consumer matrix: Workbench/Export/Figure consumers `64 passed`.
- Exact SAXS matrix: `377 passed, 6 warnings` using external basetemp
  `C:\Temp\PolyNexus_saxs_raw_detector_provenance_matrix`.
- Compile and Ruff focused checks passed.
- Structured verifier rerun with external basetemp exited `0`; quality gate
  reported `283 passed`, preprocessing reported `106 passed`, and whitespace
  passed.
- `git diff --check` passed before checkpoint.

## Checkpoint

The explicit allowlist checkpoint is created with `scripts/auto_commit.py` after
this verification record is written. No push or merge is performed.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-28-saxs-raw-detector-provenance.md`
- `docs/superpowers/specs/2026-07-28-saxs-raw-detector-provenance-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-raw-detector-provenance.md`
- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/preprocess.py`
- `polynexus/core/saxs_engine/figure_evidence.py`
- `tests/test_saxs_raw_detector_quality_transport.py`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`

## Scientific limitation

The payload records where values came from; `not_assessed` explicitly means
that geometry calibration and mask scientific validity remain outside this
automated transport task and require instrument-aware human review.
