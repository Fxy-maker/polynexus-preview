---
task_id: 2026-08-29-nmr-explicit-region-sensitivity
kind: scientific
status: completed
date: 2026-08-29
title: Add explicit NMR region-window sensitivity
---

# Add explicit NMR region-window sensitivity

## Goal

Allow NMR region-integral sensitivity reruns to use caller-supplied named ppm
windows through the shared ComputeRun method-sensitivity contract.

## Non-goals

- Do not infer windows from a material name, polymer database, or filenames.
- Do not replace the existing generic nucleus/state windows when no explicit
  windows are supplied.
- Do not change peak detection, deconvolution, assignment, or crystallinity
  algorithms beyond selecting the explicit integration windows.
- Do not promote any candidate to a publication conclusion automatically.

## Affected boundaries

- `NMRConfig.region_windows_ppm` and `NMRResult.parameters`.
- NMR deterministic region integration.
- `ComputeRunService` NMR sensitivity routing.
- NMR and ComputeRun regression tests.

## Implementation plan

1. Add validated, optional named ppm windows to `NMRConfig` and route them to
   the deterministic region-integral helper.
2. Preserve the existing generic windows when the option is absent, and expose
   explicit windows in the NMR public parameter projection.
3. Map shared `region_integration` sensitivity requests to the new config field
   and verify isolated candidate reruns through `ComputeRunService`.
4. Run focused tests and the task-scoped repository verifier, then record the
   acceptance evidence.

## Acceptance criteria

- [x] Named explicit windows accept JSON lists or tuples of two finite bounds.
- [x] Bounds are normalized to low/high order and malformed windows fail
  explicitly.
- [x] Explicit windows override generic region labels only when supplied;
  absent/empty configuration preserves existing behavior.
- [x] Window configuration is present in the public NMR parameter projection.
- [x] `region_integration` candidates route to `region_windows_ppm`, are
  re-run in isolated outputs, and remain diagnostic method candidates.
- [x] Focused and task-scoped verification is green; see
  `docs/acceptance/2026-08-29-nmr-explicit-region-sensitivity.md`.

## Verification

```powershell
pytest -q tests/test_nmr_engine.py::test_nmr_explicit_region_windows_override_generic_regions tests/test_compute_service.py::test_direct_run_replays_nmr_explicit_region_windows
python scripts/verify.py --task docs/agent/tasks/2026-08-29-nmr-explicit-region-sensitivity.md --changed --types
git diff --check
```
