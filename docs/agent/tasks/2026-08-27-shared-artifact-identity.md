---
task_id: 2026-08-27-shared-artifact-identity
kind: architecture
status: complete
date: 2026-08-27
title: Centralize raw artifact identity across entry points
---

# Centralize raw artifact identity across entry points

## Goal

Make Agent inspection and ComputeRun construction call one neutral raw-artifact
identity helper, preserving the existing identity fields and hashes.

## Non-goals

- No change to the serialized artifact schema or identity payload fields.
- No raw-data changes, symlink-policy changes, or scientific algorithm changes.
- No deletion of legacy result or persistence compatibility paths.

## Shared objects and entry points

- Producer: `polynexus/core/artifacts.py`.
- Consumers: Agent `InputArtifact`, Agent inspection, and Compute `RawArtifact`.
- Cross-entry callers: Agent/Codex workflow, Batch, GUI, and direct CLI runs.

## Affected boundaries

- All ready raw artifacts retain the same normalized path, technique, format,
  source hash, and observed-facts identity payload.
- Missing-artifact identity and source validation remain owned by their current
  callers; only the ready artifact hash construction is centralized.

## Implementation plan

1. Add a shared identity helper and a cross-entry regression assertion.
2. Replace Agent and Compute duplicate ready-artifact hash construction with
   the helper.
3. Run the shared producer/consumer matrix and structured verifier.

## Acceptance criteria

- [x] Agent inspection and Compute `RawArtifact.from_path` produce identical
  IDs for the same source and facts.
- [x] Existing canonical replay, Batch, GUI, and Agent behavior remains green.
- [x] `git diff --check` and task verification pass.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_shared_artifact_identity.py tests/test_agent_prevalidated_template_reuse.py tests/test_compute_models.py tests/test_agent_workflow_contracts.py tests/test_cli_batch_run_service.py tests/test_main_window_workers.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-shared-artifact-identity.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "refactor(core): centralize raw artifact identity" `
  --files polynexus/core/artifacts.py polynexus/core/agent_workflow/models.py polynexus/core/agent_workflow/inspection.py polynexus/core/compute/models.py tests/test_shared_artifact_identity.py docs/agent/tasks/2026-08-27-shared-artifact-identity.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md docs/acceptance/2026-08-27-shared-compute-run-migration.md
```

## Completion evidence

- `python -m pytest -p no:cacheprovider -q tests/test_shared_artifact_identity.py tests/test_agent_prevalidated_template_reuse.py tests/test_compute_models.py tests/test_agent_workflow_contracts.py tests/test_cli_batch_run_service.py tests/test_main_window_workers.py` — 47 passed, 1 skipped.
- `git diff --check` — passed.
- The neutral helper preserves the existing raw-artifact identity payload and
  is now used by Agent and Compute producers.
- Known limitations: missing-artifact identity remains a caller-owned
  compatibility path; legacy result/persistence producers remain pending the
  overall full-boundary and human review gates.
- Pre-existing local runtime outputs (`active_run.json`, `runs/`,
  `tests/_tmp_phase3/`) were left untouched.
