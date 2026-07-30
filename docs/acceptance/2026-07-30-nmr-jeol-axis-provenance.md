# NMR JEOL axis provenance acceptance

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-30-nmr-jeol-axis-provenance.md`

## Scope

This checkpoint uses the checked-in real JEOL solid 13C files as read-only
inputs. It makes the raw vendor record fields and the ppm calibration boundary
visible; it does not claim a vendor unit conversion that the file does not
explicitly establish.

## Implemented behavior

- JEOL records at the observed 64-byte alignment expose raw `SCANS`,
  `X_OFFSET`, `X_SWEEP`, and related fields under `metadata.params`.
- Frequency-like values are not silently interpreted as ppm.
- The solid 13C sample retains the safe default ppm axis `240.0..-20.0` and
  reports:

```json
{
  "source": "default_range",
  "reason": "jeol_metadata_units_unconfirmed",
  "units": "ppm",
  "calibrated": false,
  "range": [240.0, -20.0]
}
```

- The same axis status is carried through the NMR run-level evidence
  projection and `AnalysisEvidence.feature_evidence.axis_evidence`.
- Existing assignment-limited solid-state Xc and scientific review gates are
  unchanged.

## Verification

```text
python -m pytest tests/test_nmr_engine.py -q -k "jeol_solid_c_exposes_raw_axis_fields_without_claiming_ppm_calibration or nmr_engine_analysis_attaches_unified_evidence_for_history_persistence"
2 passed, 17 deselected

python -m pytest tests/test_nmr_engine.py -q
19 passed in 82.06s

python -m pytest tests/test_nmr_lifecycle_closure.py -q
4 passed in 235.59s
```

The lifecycle covers real liquid H/C and solid H/C input, analysis evidence,
Manifest/Gallery, Editor working and published revisions, export figure-run
provenance, and History restore. No fixture output was modified.

## Limitation

The checked-in JDF metadata exposes frequency-like values but does not provide
an explicit ppm calibration contract usable by this reader. The result is
therefore usable for diagnostic inspection and remains subject to the existing
solid-state assignment and scientific-review gates.
