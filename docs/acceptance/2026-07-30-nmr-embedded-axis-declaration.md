# NMR embedded axis declaration acceptance

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-30-nmr-embedded-axis-declaration.md`

## Scope

The checked-in JEOL/Delta JDF/JDFF payloads contain an explicit `acquisition`
text block. This slice exposes that source declaration in NMR provenance and
Results review. It does not apply the declaration to the plotted ppm array.

## Data contract

- Solid 13C: vendor dimension `x` / dimension 1, domain `Carbon13`,
  `x_offset=100 ppm`, `x_sweep=300 ppm`, `x_points=1024`.
- Solid 1H: vendor dimension `x` / dimension 1, domain `Proton`,
  `x_offset=0 ppm`, `x_sweep=200 ppm`, `x_points=2048`.
- Source: `jeol_delta_acquisition_text`.
- Status: `declared_not_applied`.
- Existing `ppm_axis_source`, `ppm_axis_reason`, `ppm_axis_calibrated`,
  assignment readiness, and Xc promotion remain unchanged.

## Verification

Fresh command results:

```text
Focused NMR engine: 22 passed in 95.19s
Focused evidence: 14 passed, 129 deselected in 0.58s
Focused Results review: 3 passed, 30 deselected in 0.23s
Real NMR lifecycle: 4 passed in 243.02s
Native solid-C route: 1 passed, 16 deselected in 19.06s
Structured verifier: selected checks passed; quality 296, preprocessing 106
Diff check: exit code 0
Storage report: 79 artifacts, eligible_bytes=0, emergency=false, removed=0
Checkpoint: final `HEAD`, explicit 12-file allowlist, no push
```

## Limitation

The text proves the vendor-declared fields and units, but does not by itself
prove whether `x_offset` is the displayed-axis origin or a reference/center
offset, nor prove processed-spectrum orientation. Scientific assignment and Xc
promotion therefore remain fail-closed.
