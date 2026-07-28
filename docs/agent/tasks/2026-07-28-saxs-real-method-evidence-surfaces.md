---
kind: task
status: completed
date: 2026-07-28
title: Verify real SAXS method evidence across parameter, figure, and export surfaces
---

# Real SAXS method-evidence surfaces

## Goal

Replay the real Static, Temperature, and Strain SAXS fixtures and verify that
the existing Porod, Kratky, invariant, lamellar, and (when emitted) Guinier
`metric_evidence` reaches the final parameter summary, Figure provenance, and
`quality_evidence.json` without changing its scientific meaning. Where the
Figure frame view previously selected a stale per-frame analysis record, bind
only the already-emitted Temperature/Strain series-point evidence to the
corresponding frame.

## Non-goals

- Do not change 1D algorithms, q windows, physical thresholds, quality levels,
  publication roles, rescue, AI, or frame ordering.
- Do not require the compact Figure projection to duplicate series aggregate
  counts; it must preserve every field it does project and remain lossless for
  the authoritative summary.
- Do not edit real datasets, generated repository outputs, `current-state.md`,
  or parallel scratch files.

## Affected boundaries

- Real Static, Temperature, and Strain replay through `SAXSEngine`;
- existing `metric_evidence` parameter, Figure/Manifest, and Export contracts;
- focused real acceptance regression and durable task/spec/plan/acceptance
  records.

## Implementation plan

1. Resolve the existing real fixtures and define an external-output replay for
   all three SAXS modes.
2. Assert strict-JSON final method evidence, exact Export summary equality, and
   lossless Figure projection for the fields retained by the existing compact
   provenance contract.
3. Use the existing Temperature `source_index` and Strain frame order to make
   Figure frame-level method evidence consume the series-point record already
   emitted by the analysis pipeline; keep the old frame fallback for modes or
   points without a series record.
4. Run the focused regression, structured verifier, SAXS matrix as a bounded
   diagnostic, diff check, and test-storage report; record timeouts as
   incomplete rather than passing.
5. Create one explicit allowlist checkpoint containing only this regression,
   the minimal Figure evidence fix, and
   its durable task/spec/plan/acceptance records.

## Acceptance criteria

- [x] Real Static, Temperature, and Strain fixtures replay when available and
  expose strict-JSON `metric_evidence` in final parameters.
- [x] Export `quality_evidence.json` contains a method-evidence mapping exactly
  equal to the final parameter summary for the corresponding mode.
- [x] Every Figure/Manifest method-evidence mapping is a detached, strict-JSON
  field-preserving subset of the authoritative summary; static frame records
  retain the emitted method evidence.
- [x] Existing conservative levels/reason codes and Temperature validation
  failure remain unchanged; no rendered figure promotes evidence.
- [x] Focused test, task verifier, diff check, storage report, and checkpoint
  evidence are recorded with exact outcomes.

## Verification

```powershell
python -m pytest -q tests/test_saxs_real_method_evidence_surfaces.py -vv --basetemp D:\PolyNexus_saxs_real_method_evidence_surfaces_green_current
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-real-method-evidence-surfaces.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python -m pytest -q tests/test_saxs_*.py --basetemp D:\PolyNexus_saxs_real_method_evidence_matrix_current
```

The broad SAXS matrix is a separate bounded diagnostic for this acceptance
slice. It must have a real pytest summary before being reported as a pass.

## Verification evidence

- Focused RED: `1 passed, 2 failed in 44.48s` (the intended stale Figure
  evidence mismatch).
- Focused GREEN: `3 passed in 41.92s`.
- Task verifier: exit `0`; quality gate `287 passed`, preprocessing gate
  `106 passed`, Ruff/compile/type-baseline/memory/task/whitespace checks
  passed.
- Exact SAXS file matrix: `455 passed, 6 warnings in 240.01s`.
- `git diff --check`: passed.
- `python scripts/test_storage.py report --json`: exit `0`, dry-run; active
  and retained test directories were protected and no files were removed.
- A separately started full/boundary verifier (`PID 22808`, command
  `python scripts/verify.py --changed --types --full --boundary`) was still
  running when this task checkpoint was prepared. Its result is intentionally
  not counted as evidence for this task; no pytest summary was observed.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_evidence.py`
- `tests/test_saxs_real_method_evidence_surfaces.py`
- this task card
- `docs/superpowers/specs/2026-07-28-saxs-real-method-evidence-surfaces-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-real-method-evidence-surfaces.md`
- `docs/acceptance/2026-07-28-saxs-real-method-evidence-surfaces.md`
- `docs/agent/memory/active-work.md`

Do not include `polynexus/core/*`, real datasets, generated outputs,
`current-state.md`, or parallel scratch files unless a focused RED test proves
that a production behavior change is required.
