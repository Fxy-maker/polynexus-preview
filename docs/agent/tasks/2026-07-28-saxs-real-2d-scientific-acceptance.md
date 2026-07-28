---
kind: task
status: completed
date: 2026-07-28
title: Make real SAXS 2D scientific acceptance boundaries explicit
---

# SAXS real 2D scientific acceptance audit

## Goal

Expose a read-only, existing-gates-only audit for real 2D SAXS runs so that
software validation success cannot be mistaken for scientific or publication
acceptance.

## Evidence baseline

Fresh PAD8 strain evidence on the current checkout:

- real SAXS static/temperature/strain walkthrough: `3 passed`;
- actual PAD8 strain pipeline: `validation_passed=True`,
  `paper_figure_candidate=False`, and `paper_conclusion_ready=False`;
- five raw detector reports: all `raw_detector`, all `Diagnostic`, header-backed
  geometry, configured mask provenance, `validity=not_assessed`, and coverage
  decreasing from about `0.690` to `0.416`;
- strain reliability: `diagnostic_only`, with existing reasons for low-q void
  dominance, lost lamellar anchor, low axis confidence, and phase ambiguity.

## Non-goals

- Do not add or tune scientific thresholds.
- Do not change existing physical metrics, quality levels, rescue/AI behavior,
  publication roles, or Figure/Manifest/Export decisions.
- Do not claim geometry or mask validity from provenance alone.
- Do not edit real data, generated outputs, `current-state.md`, or parallel
  scratch files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`: pure audit builder
  and existing-gate reason extraction;
- `polynexus/core/saxs_engine/__init__.py`: public SAXS engine export;
- `polynexus/core/saxs.py`: strain-series parameter attachment only;
- `tests/test_saxs_real_2d_scientific_acceptance.py`: contract and real PAD8
  acceptance regression;
- `docs/acceptance/` and task/spec/plan/memory records: durable evidence only.

## Acceptance criteria

- [x] `build_saxs_scientific_acceptance_audit()` returns strict JSON-safe,
  detached evidence using only existing fields.
- [x] Audit status is `diagnostic_only` for the current PAD8 result while the
  original `validation_passed=True` and publication flags remain unchanged.
- [x] Missing evidence is `not_assessed`; an apparently unblocked payload is
  only `review_required`, never automatically accepted.
- [x] Existing levels, reason codes, provenance validity, reliability status,
  and publication flags are retained without numeric reclassification.
- [x] The SAXS strain-series parameters contain the detached audit while all
  existing result and frame fields remain backward-compatible.
- [x] TDD RED/GREEN, exact SAXS matrix, structured verifier, diff check, real
  PAD8 run, and explicit allowlist checkpoint are recorded.

## Implementation plan

1. Add focused RED tests for missing evidence, diagnostic PAD8-like evidence,
   review-required evidence, strict JSON, and input immutability.
2. Implement the pure audit builder in `saxs_quality_contracts.py` and export
   it through the existing SAXS engine public boundary.
3. Add the audit to the strain-series parameter payload only, preserving the
   existing fields and source-indexed frame records.
4. Run the focused suite, real PAD8 test, exact SAXS matrix, structured
   verifier, and `git diff --check` with external test storage if needed.
5. Record the real evidence and create one explicit allowlist checkpoint.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_real_2d_scientific_acceptance.py -vv --basetemp C:\Temp\PolyNexus_saxs_real_2d_acceptance_redgreen
python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName) --basetemp C:\Temp\PolyNexus_saxs_real_2d_acceptance_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-real-2d-scientific-acceptance.md --changed --types
git diff --check
```

The real PAD8 source is `D:\PolyNexus\测试数据\saxs\PAD8原位拉伸` and must be
read-only; pytest output must use managed/external basetemp storage.

## Verification

The required structured check is:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-real-2d-scientific-acceptance.md --changed --types
```

The exact SAXS matrix must report a readable pytest summary. A timeout,
collection-only result, or an unrelated older process is not counted as a pass.

## Verification evidence

- TDD RED: collection failed with the expected missing
  `build_saxs_scientific_acceptance_audit` import.
- First implementation run: `3 passed, 1 failed`; the failure identified the
  need for separate raw geometry/mask provenance reason codes.
- Final focused GREEN: `4 passed in 14.90s`, including the real PAD8 strain
  pipeline.
- Fresh real walkthrough: `3 passed, 12 deselected in 45.12s` for SAXS
  static/temperature/strain; the real eval runner also returned `2 passed`.
- Exact SAXS matrix: `435 passed, 6 warnings in 45.04s`. Warnings were the
  existing Arial CJK glyph warnings and existing EDF geometry warnings.
- Structured verifier exited `0` with quality `287 passed`, preprocessing `106
  passed`, Ruff/compile/type baseline/memory/task/whitespace all passing.
- `git diff --check` passed through the verifier. Real direct audit output was
  written outside the repository under
  `C:\Temp\PolyNexus_saxs_real_2d_direct_audit_current4`.

The real PAD8 result kept `validation_passed=True` but returned
`scientific_acceptance_audit.status=diagnostic_only`, with existing publication
flags false, raw-detector and sector-map evidence separated, and geometry/mask
validity remaining `not_assessed`.

## Known limitations

This task makes the existing boundary explicit. It does not approve detector
geometry, mask validity, beam-center meaning, orientation interpretation,
temperature/strain scientific meaning, or final publication/release.

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, running Python/pytest
processes, historical test directories, `.superpowers/`, GUI/editor drafts,
and `tests/_tmp_phase3/` remain outside this task.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/__init__.py`
- `polynexus/core/saxs.py`
- `tests/test_saxs_real_2d_scientific_acceptance.py`
- this task card
- `docs/superpowers/specs/2026-07-28-saxs-real-2d-scientific-acceptance-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-real-2d-scientific-acceptance.md`
- `docs/acceptance/2026-07-28-saxs-real-2d-scientific-acceptance.md`
- `docs/agent/memory/active-work.md`

## Checkpoint

The explicit allowlist checkpoint is created after this verification record is
finalized. No push, merge, or publication approval is performed.
