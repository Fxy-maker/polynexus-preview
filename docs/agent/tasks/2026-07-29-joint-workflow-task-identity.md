---
task_id: 2026-07-29-joint-workflow-task-identity
kind: gui-contract
status: completed
---

# Joint workflow task identity

## Goal

Ensure a populated Joint report uses its existing display-only sample identity
in the Results Workbench task card, rather than showing `No data loaded`.

## Non-goals

- Do not change Joint metrics, conflict checks, severity, scientific meaning,
  or publication decisions.
- Do not mutate the report, persisted project identity, source runs, or export
  provenance.
- Do not infer vendor semantics or approve human scientific review.

## Affected boundaries

- `MainWindowWorkspaceMixin._workflow_task_context()` display projection.
- Existing Joint identity resolver and its history/persistence contracts.
- Focused Workspace/Joint regression tests and durable acceptance records.

## Implementation plan

1. Add a regression through `MainWindowWorkspaceMixin._workflow_task_context()`
   that reproduces the populated Joint report showing `No data loaded`.
2. Reuse `resolve_joint_history_project_label()` at that display boundary so a
   single report sample is shown without changing the report or persistence
   payload.
3. Run the focused Workspace/Joint/History/Persistence matrix and the
   structured repository verifier.
4. Create one allowlisted local checkpoint after `git diff --check` passes.

## Acceptance criteria

- [x] A single populated Joint report row displays its sample identity in the
  task-card source field.
- [x] Empty and multi-sample report behavior continues to use the existing
  resolver policy.
- [x] Existing persisted Joint project identity remains unchanged.
- [x] Focused regression matrix passes with an exact pytest summary.
- [x] Structured verifier and allowlist checkpoint pass.

## Verification evidence

- RED: `1 failed`; expected source was `PA6-A`, actual source was
  `No data loaded`.
- GREEN focused matrix: `41 passed, 177 deselected in 56.97s`, exit code `0`.

## Verification

```powershell
python -m pytest -q tests/test_main_window_workspace_mixin.py tests/test_joint_history_project_identity.py tests/test_context_suggestion_service.py tests/test_joint_hub_dataset.py tests/test_main_window_persistence.py -k "workspace or workflow_task or joint or history_project_identity or persistence_keeps_raw_project_identity"
python scripts/verify.py --task docs/agent/tasks/2026-07-29-joint-workflow-task-identity.md --changed --types
git diff --check
```

The structured verifier exited `0`; quality gate `287 passed`, preprocessing
gate `106 passed`, Ruff, compile, type baseline, memory/task, and whitespace
checks passed. `git diff --check` passed.

## Explicit changed-file allowlist

- `polynexus/gui/main_window_workspace_mixin.py`
- `tests/test_main_window_workspace_mixin.py`
- `docs/superpowers/specs/2026-07-29-joint-workflow-task-identity-design.md`
- `docs/superpowers/plans/2026-07-29-joint-workflow-task-identity.md`
- `docs/agent/tasks/2026-07-29-joint-workflow-task-identity.md`
- `docs/acceptance/2026-07-29-joint-workflow-task-identity.md`
- `docs/agent/memory/active-work.md`

Do not include `docs/agent/memory/current-state.md`, generated outputs, real
datasets, or pre-existing scratch files.
