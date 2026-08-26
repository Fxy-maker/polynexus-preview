---
kind: task
status: completed
date: 2026-08-27
title: Route non-DSC Agent directory workflows through ComputeRun
---

# Route non-DSC Agent directory workflows through ComputeRun

## Goal

Make default and custom Agent/Codex workflows for IR, SAXS, and WAXS directory
artifacts publish one shared `ComputeRun` with an opaque canonical envelope,
while preserving the DSC directory thermal-series compatibility route.

## Non-goals

- Do not change provider algorithms, directory frame discovery, or scientific
  quality gates.
- Do not migrate DSC directories until a directory-aware `thermal_program.v1`
  converter exists; preserve its current multi-segment behavior.
- Do not remove custom provider runners, legacy result fields, or raw files.

## Affected boundaries

- `polynexus/core/agent_workflow/service.py`: directory execution adapter and
  canonical replay.
- `polynexus/core/agent_workflow/inspection.py`: shared directory identity
  inspection for non-DSC providers.
- `polynexus/core/compute/service.py`: source-bound opaque directory envelope
  conversion for non-DSC techniques.
- `polynexus/core/project_workflow/package.py`: directory hash validation using
  the shared manifest contract.
- `tests/test_agent_directory_compute_run.py`: shared projection and DSC
  compatibility regressions.
- `docs/agent/`, `docs/superpowers/`, and `docs/acceptance/`: durable state.

## Shared objects and entry points

- Producer: `ComputeRunService` plus the existing raw-file envelope converter.
- Consumers: Agent/Codex `AnalysisRun` and project-workflow evidence/package
  readers.
- Preserved boundary: DSC directory provider path remains the existing
  multi-program adapter.

## Implementation plan

1. Add a failing test showing a custom non-DSC directory workflow currently
   returns no `compute_run`, and a test proving DSC directory compatibility is
   unchanged.
2. Wrap non-DSC directory provider execution in `ComputeRunService`, retaining
   exactly one provider call and an opaque source-bound canonical template.
3. Run Agent/project workflow and ComputeRun matrices, then structured verify,
   update acceptance/memory, and create an allowlisted checkpoint.

## Acceptance criteria

- [x] Non-DSC directory workflow steps expose a completed shared `ComputeRun`
  with `ir.spectrum.v1`, `saxs.profile.v1`, or `waxs.profile.v1` as appropriate.
- [x] Custom provider runners execute exactly once and their result remains the
  legacy result projection inside the shared run.
- [x] DSC directory workflows still use the existing provider-only path.
- [x] No raw input is copied or modified, and no duplicate persistence object
  is introduced.

## Completion evidence

- Directory inspection now accepts SAXS/WAXS alongside the existing DSC/IR
  identity boundary; NMR remains unregistered and unchanged.
- Agent/Codex non-DSC directory steps use an opaque source-bound canonical
  envelope and one shared `ComputeRun`; DSC directory steps remain on the
  multi-segment compatibility route.
- Directory content hashes in Agent inspection, ComputeRun, and evidence
  packaging use the same `directory_manifest` contract.

## Verification

```powershell
python -m pytest -q tests/test_agent_directory_compute_run.py tests/test_agent_workflow_contracts.py tests/test_project_workflow_adapters.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-agent-directory-compute-run-migration.md --changed --types
git diff --check
```

## Changed-file allowlist

- `polynexus/core/agent_workflow/service.py`
- `polynexus/core/agent_workflow/inspection.py`
- `polynexus/core/compute/service.py`
- `polynexus/core/project_workflow/package.py`
- `tests/test_agent_directory_compute_run.py`
- `docs/agent/tasks/2026-08-27-agent-directory-compute-run-migration.md`
- `docs/superpowers/specs/2026-08-27-agent-directory-compute-run-migration-design.md`
- `docs/superpowers/plans/2026-08-27-agent-directory-compute-run-migration.md`
- `docs/acceptance/2026-08-27-agent-directory-compute-run-migration.md`
- `docs/agent/memory/active-work.md`
