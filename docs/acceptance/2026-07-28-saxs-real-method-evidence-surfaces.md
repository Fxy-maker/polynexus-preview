# SAXS real method-evidence surfaces acceptance

## Scope

This acceptance slice checks the existing Static, Temperature, and Strain
fixtures across final parameters, Figure provenance, and Export
`quality_evidence.json`. It preserves existing metric values, quality levels,
reason codes, validation gates, source indices, and publication roles.

## Evidence

- Fresh RED: `1 passed, 2 failed in 44.48s`; Temperature failed on
  `lamellar.fit_evidence.L_nm`, and Strain failed on `invariant.value`.
- Root cause: Figure frame provenance selected the preliminary
  `_batch_results` evidence instead of the already-emitted series-point
  evidence consumed by final parameters and Export.
- Fresh GREEN: `python -m pytest -q tests/test_saxs_real_method_evidence_surfaces.py -vv --basetemp D:\PolyNexus_saxs_real_method_evidence_surfaces_green_current`
  returned `3 passed in 41.92s`.

## Acceptance boundary

Temperature frame evidence is bound by the existing `source_index`; Strain
frame evidence is bound by the existing point order. The Figure projection
remains compact and detached. No interpolation, new threshold, rescue, AI
decision, physical gate, or scientific validity promotion is introduced.

## Verification closure

- Task verifier exited `0`; quality gate was `287 passed`, preprocessing gate
  was `106 passed`, and Ruff/compile/type-baseline/memory/task/whitespace
  checks passed.
- Exact SAXS file matrix: `455 passed, 6 warnings in 240.01s`.
- `git diff --check` passed.
- Test-storage report exited `0` in dry-run mode; no artifacts were removed.
- The explicit allowlist checkpoint is the only commit action for this slice.

A separately started full/boundary verifier was still running at checkpoint
time and had no pytest summary. It is not counted as a pass for this slice;
its eventual result must be classified independently.
