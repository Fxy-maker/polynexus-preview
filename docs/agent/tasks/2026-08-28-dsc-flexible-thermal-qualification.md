---
task_id: 2026-08-28-dsc-flexible-thermal-qualification
kind: scientific
status: implementation_complete_review_required
date: 2026-08-28
title: Remove material-specific DSC qualification blockers
---

# Remove material-specific DSC qualification blockers

## Goal

Allow all structurally calculable DSC thermal holds to reach deterministic
analysis, recording temperature quality issues as warnings rather than blocking.

## Non-goals

- Do not alter raw data or Avrami equations.
- Do not auto-promote warned results to manuscript evidence.
- Do not remove hard structural validation.

## Shared objects and entry points

- Objects: canonical `thermal_program.v1`, `ComputeRun`, DSC result/evidence.
- Producers: DSC canonical converter and `DSCEngine`.
- Consumers: ComputeRun, project workflow, evidence package, ARS writing input,
  GUI/CLI/Batch/Agent routes consume the same result and warning fields.

## Acceptance criteria

- [x] No fixed melt-temperature prerequisite remains in generic DSC conversion.
- [x] PA11 isothermal reaches analysis with warning metadata instead of provider failure.
- [x] PA12-50 isothermal converts its calculable holds instead of format blocking.
- [x] Hard malformed/insufficient inputs still fail closed.
- [x] Focused tests and structured verification pass.

## Verification

```powershell
python -m pytest -q tests/test_dsc_canonical_isothermal_conversion.py tests/test_dsc_kinetics.py tests/test_compute_service.py
python scripts/verify.py --task docs/agent/tasks/2026-08-28-dsc-flexible-thermal-qualification.md --changed --types
git diff --check
```

## Pre-existing changes left untouched

`active_run.json`, `runs/`, `tests/_tmp_phase3/`, and historical test artifacts.

## Completion evidence

- DSC conversion and kinetics matrix: `25 passed, 2 warnings`.
- Shared `ComputeRunService` replay: PA11 `completed` with two isothermal
  holds; PA12-50 `completed` with five isothermal holds.
- The holds carry temperature-quality warnings in the canonical segment and
  Avrami quality flags; publication eligibility remains a separate review.
