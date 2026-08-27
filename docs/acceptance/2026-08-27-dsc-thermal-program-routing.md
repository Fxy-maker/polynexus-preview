# DSC thermal_program.v1 routing acceptance

## Result

The existing `thermal_program.v1` container now routes supported heating,
cooling, and isothermal segment roles through one deterministic DSCEngine call.
The legacy `run_isothermal_template` name delegates to the unified method.

## Evidence

- Focused tests: `66 passed, 3 skipped`.
- Read-only smoke on
  `D:\PolyNexus-six-sample-replay-20260827-v004\raw\dsc\thermal-cycle\PA6.txt`:
  `ComputeRun(status=completed)`, template `thermal_program.v1`, one retained
  heating segment, sample mass `5.5 mg`.
- No raw data, generated output, or provider algorithms were modified.

## Limitations

- The supplied PA6 thermal-cycle files each contain one monotonic heating scan;
  no cooling segment is present in those files, so no cooling result can be
  inferred from them.
- Non-isothermal kinetics require at least three retained cooling curves, as
  enforced by the existing engine.
- Scientific publication eligibility remains subject to the existing evidence
  and human-review boundaries.

## Verification

```powershell
python -m pytest -q tests/test_dsc_canonical_isothermal_conversion.py tests/test_dsc_kinetics.py tests/test_compute_service.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-dsc-thermal-program-routing.md --changed --types
```
