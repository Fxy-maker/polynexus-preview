---
task_id: 2026-08-27-optional-project-context-no-material-defaults
kind: architecture
status: active
date: 2026-08-27
title: Optional project context and removal of implicit material defaults
---

# Optional project context and removal of implicit material defaults

## Goal

Make deterministic analysis material-agnostic by default while allowing Codex/ARS to provide a small, optional, project-local context that is validated, hashed, and used only by calculations that explicitly need it.

## Non-goals

- No material database, material editor, or GUI form.
- No automatic scientific material identification from filenames.
- No rewrite of FTIR/SAXS/WAXS algorithms in this task.
- No relaxation of provider quality gates or automatic promotion to manuscript claims.

## Shared objects and entry points

- Objects: `AnalysisPlan`, `ComputeRun`, DSC provider result.
- AI/Codex/CLI: may pass or discover optional context; all use `ComputeRunService`.
- GUI: unchanged user flow; optional context is never required.
- Cross-entry rule: context is represented once in the shared compute plan/run provenance.

## Affected boundaries

- Core: `ProjectContext`, `AnalysisPlan`, `ComputeRunService`, and DSC configuration/result projection.
- Consumers: existing CLI, Batch, GUI worker, and Agent/Codex routes continue using the same optional API.
- Not affected: evidence-package publication classification, figure rendering, RAG, and raw datasets.

## Implementation plan

1. Add and validate the optional project-context contract.
2. Persist the context snapshot and hash on the shared analysis plan.
3. Remove implicit material reference defaults from DSC and consume only explicit context values.
4. Verify unchanged no-context entry points and checkpoint the atomic change.

## Acceptance criteria

- [x] Missing context never injects a material-specific reference enthalpy; DSC still computes material-independent metrics and marks Xc unavailable when its reference is absent.
- [x] A valid context can provide an explicit DSC reference enthalpy and source, and that value is used deterministically.
- [x] Invalid context fails closed with a `project_context_invalid` reason and never reaches a provider.
- [x] `AnalysisPlan`/`ComputeRun` retain a JSON-safe context snapshot and SHA-256 hash for replay provenance.
- [x] Existing GUI/CLI/Batch calls remain valid without new required arguments.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_context.py tests/test_compute_service.py tests/test_dsc_engine.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-optional-project-context-no-material-defaults.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add optional project context without material defaults" `
  --files polynexus/core/project_context.py polynexus/core/compute/models.py polynexus/core/compute/service.py polynexus/core/dsc.py polynexus/core/dsc_engine/config.py polynexus/core/dsc_engine/core.py tests/test_project_context.py tests/test_compute_service.py tests/test_dsc_engine.py docs/agent/tasks/2026-08-27-optional-project-context-no-material-defaults.md docs/superpowers/specs/2026-08-27-optional-project-context-design.md docs/superpowers/plans/2026-08-27-optional-project-context.md
```

## Completion evidence

- Exact commands and outcomes: pending implementation.
- Known limitations or follow-up: migrate other technique-specific hard-coded material assumptions in a separate task.
- Pre-existing changes left untouched: `active_run.json`, `runs/`, `tests/_tmp_phase3/`.
