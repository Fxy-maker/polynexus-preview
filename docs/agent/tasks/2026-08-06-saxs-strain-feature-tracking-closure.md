# SAXS Strain Feature Tracking Closure

## Goal

Close the strain-series feature-tracking data flow so long period,
feature-local orientation, directional diagnostics, figures, and GUI rows use
one authoritative tracked lamellar feature.

## Non-goals

- No inferred tensile axis or structural-axis conversion.
- No forced monotonic strain response.
- No publication, push, merge, deployment, or raw-data mutation.
- No unrelated SAXS threshold tuning or GUI redesign.

## Affected boundaries

- SAXS single-frame peak evidence and strain-series orchestration.
- Feature-local anisotropy target selection.
- Detector-coordinate sector diagnostics.
- SAXS analyzer batch-row and figure inputs.
- Strain result-table and figure parameter naming.

## Implementation plan

1. Add failing regressions for peak continuity, orientation q reuse, one core
   result per frame, canonical invariant output, and detector display scaling.
2. Make the series tracker authoritative, fail closed after loss or core
   exceptions, and transport the accepted q to orientation and sector metrics.
3. Reuse the series-owned core results in GUI rows and normalize legacy
   invariant aliases at history, stability, evidence, and batch read boundaries.
4. Replay the external EDF 8 sequence read-only, run focused and structured
   verification, document evidence, and create an explicit-file checkpoint.

## Acceptance criteria

- [x] The strain series owns one core analysis result per frame, including an
      explicit failed result when core analysis raises.
- [x] Long-period values are continuous-feature results or explicit,
      irreversible tracking loss.
- [x] Orientation uses the exact tracked total-profile q target.
- [x] Normal GUI runs supply deterministic frame source indices.
- [x] Meridional/equatorial q and L diagnostics are emitted explicitly.
- [x] Scattering invariant fields use invariant names in new strain output;
      legacy aliases remain read-only compatibility inputs.
- [x] EDF 8 results no longer contain the identified 5% q-feature switch or
      200%/400% core-versus-GUI L disagreement.
- [x] Focused regressions and structured verification pass.

## Focused evidence

- Core/GUI/tracking/table matrix: `131 passed in 14.43s`.
- Figure/orientation matrix: `245 passed, 2 skipped, 4 warnings in 40.95s`;
  warnings are existing missing Arial CJK glyphs.
- Evidence/history/stability matrix: `307 passed in 11.05s`.
- Read-only external EDF 8 replay: `1 passed in 9.11s`.
- Structured verifier passed task/memory checks, Ruff, compile, quality
  `297 passed`, preprocessing `107 passed`, and whitespace checks.
- Local explicit-file checkpoint remains pending.

## Verification

```powershell
python -m pytest -q tests/test_saxs_strain_feature_tracking_closure.py tests/test_saxs_orientation_tracking_transport.py tests/test_saxs_batch_parameters.py tests/test_saxs_results_table_service.py
python scripts/verify.py --task docs/agent/tasks/2026-08-06-saxs-strain-feature-tracking-closure.md --changed --types
git diff --check
```

## Review gate

This changes scientific strain-series semantics and requires human review
before merge. It does not require a separate approval to create the local
checkpoint after verification.
