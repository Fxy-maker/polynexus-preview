# NMR JEOL Axis Provenance

## Goal

Make real JEOL JDF axis metadata and fallback calibration status visible in
the NMR analysis evidence without inventing chemical-shift units or promoting
solid-state conclusions.

## Non-goals

- No vendor-specific unit conversion when the JDF metadata does not identify
  the unit as ppm.
- No change to peak detection, deconvolution, assignment, Xc, Joint, or review
  promotion thresholds.
- No edits to the real files under `测试数据/`.

## Affected boundaries

- JEOL reader: locate the observed 64-byte records and retain raw X-axis
  metadata values.
- NMR run/evidence: expose `ppm_axis_source`, `ppm_axis_reason`, units, and
  calibration state as JSON-safe evidence.
- Tests/docs: use the checked-in solid 13C JDF files as read-only regression
  inputs and preserve the existing lifecycle gate.

## Acceptance criteria

- [x] The checked-in solid 13C JDF record layout yields non-empty raw values
  for `SCANS`, `X_OFFSET`, and `X_SWEEP`.
- [x] The reader keeps the solid 13C axis on the safe default ppm range when
  the raw JEOL fields are not explicitly ppm-calibrated.
- [x] Evidence states whether the axis is vendor-derived or default-derived,
  why, and whether calibration is confirmed.
- [x] Existing real NMR lifecycle and focused engine tests remain green.

## Implementation plan

1. Add a regression against a checked-in solid 13C JEOL file and reproduce the
   missing raw axis metadata in RED.
2. Support the observed JEOL record alignment while preserving raw values and
   keeping unit interpretation fail-closed.
3. Publish axis source, reason, units, calibration state, and range through
   the NMR run projection and analysis evidence.
4. Run focused, real lifecycle, cross-module, and structured verification,
   then create one explicit allowlist checkpoint.

## Results

- The real JEOL records are located at the observed 64-byte boundaries and
  expose non-empty `SCANS`, `X_OFFSET`, and `X_SWEEP` raw values.
- The real solid 13C file retains the default `240.0..-20.0` ppm display axis
  because the vendor values are not explicitly ppm-calibrated.
- `AnalysisEvidence.feature_evidence.axis_evidence` now carries source,
  reason, units, calibration boolean, and range.
- No Xc, assignment, Joint, or scientific-review promotion rule changed.

## Verification results

- Focused RED: `1 failed`, caused by `SCANS` being `None`.
- Focused GREEN: `2 passed, 17 deselected`.
- NMR engine suite: `19 passed in 82.06s`.
- Real four-partition lifecycle: `4 passed in 235.59s`.
- Cross-module NMR/Workbench matrix: `43 passed in 352.00s`.
- Structured verifier: all selected checks passed, including quality `290` and
  preprocessing `106`.

## Verification

```powershell
python -m pytest tests/test_nmr_engine.py -q
python -m pytest tests/test_nmr_lifecycle_closure.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-30-nmr-jeol-axis-provenance.md --changed --types
```

## Explicit changed-file allowlist

- `polynexus/core/nmr_engine/io.py`
- `polynexus/core/nmr_engine/core.py`
- `polynexus/core/analysis_evidence_nmr.py`
- `tests/test_nmr_engine.py`
- `docs/agent/tasks/2026-07-30-nmr-jeol-axis-provenance.md`
- `docs/superpowers/specs/2026-07-30-nmr-jeol-axis-provenance-design.md`
- `docs/superpowers/plans/2026-07-30-nmr-jeol-axis-provenance.md`
- `docs/acceptance/2026-07-30-nmr-jeol-axis-provenance.md`
- `docs/agent/memory/active-work.md`
