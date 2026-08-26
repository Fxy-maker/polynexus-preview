---
task_id: 2026-08-27-dsc-thermal-program-migration
kind: scientific
status: complete
date: 2026-08-27
title: Route DSC multi-program exports through thermal_program.v1
---

# Route DSC multi-program exports through thermal_program.v1

## Goal

Keep the existing multi-segment Avrami calculation while making
`thermal_program.v1` the registry and shared-ComputeRun identity for DSC
program exports.

## Non-goals

- No changes to Avrami equations, qualification thresholds, or scientific
  publication decisions.
- No raw-data edits and no removal of the `dsc.isothermal.v1` compatibility
  reader.

## Affected boundaries

- `polynexus/core/canonical_experiments/dsc_isothermal.py`
- `polynexus/core/canonical_experiments/registry.py`
- `polynexus/core/compute/service.py`
- `polynexus/core/dsc.py`
- `polynexus/core/agent_workflow/tpae.py`
- focused DSC, compute, and TPAE tests

## Implementation plan

1. Allow the existing deterministic Mettler converter to emit either the old
   compatibility ID or `thermal_program.v1`, with registry/TPAE choosing the
   new ID.
2. Accept both IDs at the DSCEngine canonical execution boundary while
   preserving all existing segment qualification and Avrami logic.
3. Let `ComputeRunService` attach DSC templates and execute a supplied
   canonical template through the existing provider adapter.
4. Add replay and compatibility tests, then run the structured verifier.

## Acceptance criteria

- [x] Registry-driven DSC conversion emits `thermal_program.v1`.
- [x] ComputeRun exposes that template and retains all accepted segments.
- [x] DSCEngine executes both new and legacy template IDs identically.
- [x] Existing invalid/legacy DSC paths remain compatible.
- [x] Focused DSC and structured verification pass.

## Completion evidence

- The deterministic converter keeps `dsc.isothermal.v1` as an explicit
  compatibility option, while registry and TPAE proposals use
  `thermal_program.v1`.
- `ComputeRunService` now attaches valid DSC templates and invokes the
  existing template execution boundary without changing Avrami logic.
- TPAE and direct-run steps expose the shared template/result projection; all
  accepted program segments remain independently represented in the template.
- Focused DSC/compute/TPAE coverage passed `76` tests with `3` skips; the
  structured verifier passed task checks, Ruff/compile, quality `310`,
  preprocessing `157`, and whitespace.
- No raw data or provider equations were changed.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_dsc_canonical_isothermal_conversion.py tests/test_dsc_kinetics.py tests/test_tpae_golden_workflow.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-dsc-thermal-program-migration.md --changed --types
git diff --check
```
