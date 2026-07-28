# Task: SAXS strain sector payload fail-closed handling

**Status:** checkpointed locally after verification

## Goal

Prevent malformed strain sector/2D payloads from aborting the complete strain
series, while exposing an explicit Unusable orientation evidence record.

## Non-goals

- Do not change Herman, anisotropy, detector, or physical metric algorithms.
- Do not infer missing sector values, repair masks, interpolate profiles, or
  promote orientation evidence.
- Do not alter temperature/static behavior, publication roles, AI rescue, or
  GUI logic.
- Do not modify concurrent memory, NMR, Joint, or generated files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_strain.py`: malformed sector input and the
  existing strain orientation consumer.
- `tests/test_saxs_strain_sector_fail_closed.py`: direct helper and full-series
  regressions.

## Acceptance criteria

- [x] Malformed nested sector mappings do not raise from
  `herman_from_sector_data()`.
- [x] The malformed frame gets a strict JSON-safe Unusable orientation
  evidence record containing `strain_sector_data_invalid`.
- [x] The surrounding strain series retains the frame and all existing 1D
  analysis results; only the affected orientation evidence is downgraded.
- [x] Valid sector payloads retain the existing orientation behavior.
- [x] Focused consumer tests, structured verifier, and diff check pass; the
  exact full SAXS matrix is reported honestly if bounded execution times out.

## Implementation plan

1. Add RED tests for malformed nested sector input and its strain-series
   consumer path.
2. Add one existing-contract-based Unusable evidence builder for invalid
   sector payloads, validate nested mappings, and guard the series consumer.
3. Run focused 2D/strain/consumer tests, the structured verifier, diff check,
   and storage dry-run; create one explicit allowlist checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_strain_sector_red'
python -m pytest -q tests/test_saxs_strain_sector_fail_closed.py

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_strain_sector_focus'
python -m pytest -q tests/test_saxs_strain_sector_fail_closed.py tests/test_saxs_strain_axis_fail_closed.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_batch_parameters.py

python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-strain-sector-fail-closed.md --changed --types
git diff --check
python scripts/test_storage.py report --json
```

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_strain_sector_fail_closed.py`
- `docs/agent/tasks/2026-07-28-saxs-strain-sector-fail-closed.md`
- `docs/superpowers/specs/2026-07-28-saxs-strain-sector-fail-closed-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-strain-sector-fail-closed.md`

The pre-existing `docs/agent/memory/current-state.md`, concurrent files,
runtime directories, generated captures, scratch, and `.superpowers/` remain
outside the checkpoint.

## Verification evidence before checkpoint

- RED: `2 failed in 0.73s`; both direct helper and full strain consumer
  reproduced the existing `AttributeError` from `None.get()`.
- Focused 2D/strain/batch matrix: `54 passed in 0.79s`.
- Structured verifier exited `0`: task-check valid, Ruff/compile/type baseline
  passed, quality gate `287 passed`, preprocessing gate `106 passed`, and
  whitespace passed.
- Test-storage report exited `0` in dry-run mode: `476` artifacts and `92`
  eligible candidates; no data was deleted or moved.
- `git diff --check` passed. The complete SAXS matrix is not claimed for this
  task; the preceding 458-test bounded run timed out without a pytest summary.

Fresh follow-up on 2026-07-30 returned `69 passed in 1.12s`, exit code `0`, for
the focused 2D/strain/batch matrix with an external D: basetemp.

## Follow-up documentation checkpoint allowlist

- `docs/agent/tasks/2026-07-28-saxs-strain-sector-fail-closed.md`
- `docs/acceptance/2026-07-30-saxs-strain-sector-fail-closed.md`
- `docs/agent/memory/active-work.md`
