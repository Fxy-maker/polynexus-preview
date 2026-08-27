---
task_id: 2026-08-27-package-context-ars-consistency
kind: schema
status: implementation_complete_review_required
date: 2026-08-27
title: Preserve confirmed project context in ARS handoff
---

# Preserve confirmed project context in ARS handoff

## Goal

Make a packaged multi-run project self-contained for ARS by carrying the
explicit context used to group and interpret the runs.

## Non-goals

- Do not infer sample identity, batch identity, or causal claims.
- Do not change metric eligibility, provider calculations, or figure roles.
- Do not make context a substitute for raw-data provenance.

## Affected boundaries

- Package manifest: collect declared request context from persisted run manifests.
- ARS handoff: expose context with source/status labels and validate its shape.
- Consumers: existing GUI/evidence view readers remain compatible with additive
  fields; ARS receives the same packaged object.

## Acceptance criteria

- [x] Package manifest includes deduplicated confirmed context entries from run
  request parameters.
- [x] `ars-writing-input.json` exposes those entries with their confirmation
  status and does not present them as raw instrument facts.
- [x] Existing handoff validation and package tests remain green.

## Implementation plan

1. Add failing package/handoff tests for context propagation.
2. Collect context in package creation and project it into ARS input.
3. Validate JSON-safe shape, run focused tests, and checkpoint.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_ars_writing_handoff.py tests/test_project_workflow_package.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-package-context-ars-consistency.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "fix(package): preserve confirmed context in ARS handoff" `
  --files polynexus/core/project_workflow/package.py polynexus/core/project_workflow/ars_handoff.py tests/test_project_ars_writing_handoff.py tests/test_project_workflow_package.py docs/agent/tasks/2026-08-27-package-context-ars-consistency.md docs/superpowers/specs/2026-08-27-package-context-ars-consistency-design.md docs/superpowers/plans/2026-08-27-package-context-ars-consistency.md docs/acceptance/2026-08-27-package-context-ars-consistency.md
```

## Completion evidence

- `python -m pytest -p no:cacheprovider -q tests/test_project_ars_writing_handoff.py tests/test_project_workflow_package.py` -> `39 passed`.
- `python scripts/verify.py --task docs/agent/tasks/2026-08-27-package-context-ars-consistency.md --changed --types` -> covered by the current structured quality/preprocess gates (311/157 passed); the full boundary remains review-required because of historical failures listed in `docs/acceptance/2026-08-28-full-suite-release-boundary.md`.
- Known limitations: context remains user/AI supplied and must not be treated
  as instrument proof; historical package manifests without request context
  remain valid and simply expose an empty context list.
- Pre-existing changes left untouched: `active_run.json`, `runs/`, and
  `tests/_tmp_phase3/`.
