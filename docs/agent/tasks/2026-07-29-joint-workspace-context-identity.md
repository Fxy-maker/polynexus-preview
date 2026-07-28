---
task_id: 2026-07-29-joint-workspace-context-identity
kind: gui-contract
status: completed
---

# Joint workspace context identity

## Goal

Make the compact Joint workspace context line use the existing report identity
when the active report is populated, so the header does not pair `PA6-A` with
`No data loaded`.

## Non-goals

- Do not change Joint metrics, conflict checks, severity, scientific meaning,
  publication decisions, or report payloads.
- Do not change persisted project identity or source-run provenance.
- Do not infer vendor semantics or close human scientific/release review.

## Affected boundaries

- `MainWindowWorkspaceMixin._workspace_context_summary_text()`.
- Existing Joint identity resolver.
- Workspace/Joint regression and native Joint route acceptance.

## Implementation plan

1. Add a failing regression for a populated Joint workspace context.
2. Reuse the existing display-only identity resolver at the context-text
   boundary.
3. Run the focused matrix, structured verifier, diff check, and native Joint
   route with external D: output.
4. Record exact evidence and create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] A populated single-sample Joint report renders its sample identity in the
  workspace context line.
- [x] Empty and multi-sample report behavior remains delegated to the existing
  identity resolver.
- [x] TDD RED and GREEN evidence are recorded.
- [x] Focused matrix, structured verifier, native route, and allowlist
  checkpoint pass.

## Verification evidence

- RED: `1 failed`; the summary rendered the translated no-data placeholder.
- GREEN focused regression: `1 passed in 0.63s`.
- Focused matrix: `42 passed, 177 deselected in 38.36s`, exit code `0`.
- Native Windows Qt Joint route: `1 passed, 16 deselected in 9.20s`, exit code
  `0`; the fresh Results capture shows `PA6-A` in both the task-card source
  and compact workspace context line.

The structured verifier exited `0`; quality gate `287 passed`, preprocessing
gate `106 passed`, Ruff, compile, type baseline, memory/task, and whitespace
checks passed. `git diff --check` passed.

## Verification

```powershell
python -m pytest -q tests/test_main_window_workspace_mixin.py tests/test_joint_history_project_identity.py tests/test_context_suggestion_service.py tests/test_joint_hub_dataset.py tests/test_main_window_persistence.py -k "workspace or workflow_task or joint or history_project_identity or persistence_keeps_raw_project_identity"
python scripts/verify.py --task docs/agent/tasks/2026-07-29-joint-workspace-context-identity.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/gui/main_window_workspace_mixin.py`
- `tests/test_main_window_workspace_mixin.py`
- `docs/superpowers/specs/2026-07-29-joint-workspace-context-identity-design.md`
- `docs/superpowers/plans/2026-07-29-joint-workspace-context-identity.md`
- `docs/agent/tasks/2026-07-29-joint-workspace-context-identity.md`
- `docs/acceptance/2026-07-29-joint-workspace-context-identity.md`
- `docs/agent/memory/active-work.md`

Do not include `docs/agent/memory/current-state.md`, generated outputs, real
datasets, or pre-existing scratch files.
