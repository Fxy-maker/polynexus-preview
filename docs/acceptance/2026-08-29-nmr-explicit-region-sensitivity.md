# NMR explicit region-window sensitivity — 2026-08-29

## Outcome

NMR region-integral sensitivity now accepts explicit named ppm windows through
the shared configuration and `ComputeRunService` method-sensitivity entry
point. The default remains the existing nucleus/state-specific generic window
set when no explicit windows are supplied. No material name or filename is
used to infer a boundary.

## Contract

- `NMRConfig.region_windows_ppm` accepts JSON-safe lists or tuples of two
  finite, distinct bounds per non-empty label.
- Bounds are normalized to low/high order for deterministic integration.
- Invalid windows raise an explicit configuration error; candidate reruns keep
  the failure as a sensitivity warning rather than silently falling back.
- The public NMR parameter projection records the selected windows.
- `region_integration` sensitivity candidates are isolated under the existing
  `method-sensitivity/region_integration/<method>` output path and remain
  diagnostic observations.

## Verification

```text
pytest -q tests/test_nmr_engine.py tests/test_compute_service.py
83 passed, 3 skipped in 86.87s

python scripts/verify.py --task docs/agent/tasks/2026-08-29-nmr-explicit-region-sensitivity.md --changed --types
selected checks passed
quality gate: 313 passed
preprocessing gate: 157 passed
```

## Limitations

This change does not decide which region definitions are scientifically valid
for a manuscript. ARS or a human must supply and review the windows; the core
only performs the requested deterministic calculation and records provenance.
