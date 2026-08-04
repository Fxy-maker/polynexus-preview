# SAXS Scientific Correctness Closure

## Goal

Close the 14 known SAXS findings across physical core, I/O/workflow, and figure/result contracts with regression evidence and fail-closed behavior.

## Non-goals

- Detector calibration inference, AI rescue, historical output regeneration, push, merge, or deployment.
- Changing unrelated techniques or GUI infrastructure outside SAXS result/figure eligibility.

## Scope and acceptance

### Physical core

- [ ] Porod invariant crystallinity is unit-invariant or explicitly unavailable.
- [ ] Cooling phase labels and acquisition order match low-temperature solid semantics.
- [ ] Full-channel metrics are independent of equatorial-sector changes.
- [ ] Signed corrected residuals survive quality/raw payload; positive-only fits mask explicitly.
- [ ] Existing q-min, Gibbs–Thomson, polarization, control-parameter, and single/batch smoothing fixes remain green.

### I/O and workflow

- [ ] Declared extensions and single-file/directory readers agree, including actionable HDF5/Nexus errors.
- [ ] Batch limits are configurable; any configured truncation is recorded in sequence QA/provenance.

### Geometry and GUI

- [ ] Incomplete geometry cannot receive complete/header confidence or main figure eligibility.
- [ ] Figure role requires explicit physical eligibility, not only `quality_flag=OK`.
- [ ] `Q_star_rel` is diagnostic/relative; `phi_void` is primary only when finite and valid.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-scientific-correctness-closure.md --changed --types
python scripts/verify.py --changed --types --full --boundary
python -m pytest -q tests/test_saxs_scientific_correctness_closure.py
git diff --check
```

## Known limitations

- Full verification may exceed the Windows command timeout; an incomplete run is not a pass.
- Historical generated figures must be regenerated after the implementation checkpoint.
- Human scientific review remains required for absolute-contrast/Porod interpretation.
