# DSC thermal_program.v1 routing

## Goal

Connect the existing canonical thermal-program segmentation to heating,
cooling, and isothermal DSC calculations in one ComputeRun.

## Non-goals

- No new vendor parser.
- No quality-gate relaxation or fabricated mass-normalized values.
- No raw-data or generated-output edits.

## Shared objects and entry points

- Producer: `polynexus/core/canonical_experiments/dsc_isothermal.py`.
- Consumer: `polynexus/core/dsc.py`, `polynexus/core/compute/service.py`.
- Workflow compatibility: `polynexus/core/agent_workflow/tpae.py`.
- Regression coverage: `tests/test_dsc_canonical_isothermal_conversion.py`,
  `tests/test_dsc_kinetics.py`, `tests/test_compute_service.py`.

## Affected boundaries

- Canonical template producer: Mettler DSC source to `thermal_program.v1`.
- Shared run consumer: `ComputeRunService` and its immutable result projection.
- Deterministic calculation consumer: `DSCEngine` role dispatch.
- GUI/CLI: unchanged direct consumers of the shared ComputeRun contract.

## Acceptance criteria

- [x] Thermal-cycle Mettler text yields role-tagged `thermal_program.v1` segments.
- [x] Unified execution calculates supported heating/cooling/isothermal segments in
  one result projection and keeps source/provenance links.
- [x] Existing isothermal compatibility tests remain green.
- [x] Missing sample mass is explicit and not replaced with a fabricated value.

## Implementation plan

1. Add failing converter and mixed-role execution regression tests.
2. Extend the existing converter and DSCEngine template boundary.
3. Route ComputeRun through the unified method while preserving compatibility.
4. Run focused and structured verification, then record acceptance evidence.

## Verification

```powershell
python -m pytest -q tests/test_dsc_canonical_isothermal_conversion.py tests/test_dsc_kinetics.py tests/test_compute_service.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-dsc-thermal-program-routing.md --changed --types
```
