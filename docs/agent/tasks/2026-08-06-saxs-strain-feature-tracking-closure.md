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

## Acceptance criteria

- [ ] The strain series owns one core analysis result per frame.
- [ ] Long-period values are continuous-feature results or explicit tracking loss.
- [ ] Orientation uses the exact tracked total-profile q target.
- [ ] Normal GUI runs supply deterministic frame source indices.
- [ ] Meridional/equatorial q and L diagnostics are emitted explicitly.
- [ ] Scattering invariant fields use invariant names in new strain output.
- [ ] EDF 8 results no longer contain the identified 5% q-feature switch or
      200%/400% core-versus-GUI L disagreement.
- [ ] Focused regressions and structured verification pass.

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
