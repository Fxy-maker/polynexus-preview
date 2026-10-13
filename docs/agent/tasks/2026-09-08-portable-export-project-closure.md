---
task_id: 2026-09-08-portable-export-project-closure
kind: architecture
status: complete
date: 2026-09-08
title: Close portable-export project manifest and cross-entry chain
---

# Close portable-export project manifest and cross-entry chain

## Goal

Make the portable-export route complete for project-workbench batch manifests
and prove that GUI Batch, project CLI, and Agent/Codex series execution share
the same raw-bound canonical and ComputeRun contracts.

## Non-goals

- Do not decode private vendor bytes or infer calibration, grouping, or sample
  identity.
- Do not create a GUI-only result/provenance store or replace native grouped
  SAXS/WAXS/NMR/IR directory semantics.
- Do not promote portable-export results to scientific capabilities or claims.

## Shared objects and entry points

- Core/project: immutable `PortableExportBatchManifest` and entries embedded in
  existing `AnalysisRequest`/`ProjectPlan` contracts.
- CLI: `project-workflow plan/run` accepts the manifest through the existing
  request path and emits the normal project run envelope.
- GUI: existing `BatchWorker` continues to produce per-file shared
  `ComputeRun` objects from the directory declaration.
- Agent/Codex: existing series recipe and replay consume the same per-file
  declarations; no private representation is added.

## Affected boundaries

- Manifest parsing, hashing, one-to-one source/export validation, and project
  plan/run propagation.
- Project series/single adapters and Agent replay declarations.
- CLI request loading and GUI/CLI/Agent cross-entry regression coverage.
- Unchanged: native grouped directory workflows and private binary readers.

## Implementation plan

1. Add a hash-verified batch portable-export manifest DTO and request/plan
   helpers.
2. Route project planning and execution through declarations for each selected
   raw artifact, including opaque raw inputs.
3. Expose the manifest on the project-workflow CLI without duplicating result
   storage or bypassing Core validation.
4. Add an end-to-end regression comparing GUI Batch, project CLI, and Agent
   canonical/ComputeRun provenance for the same raw/export set.
5. Run focused and structured verification, update memory, and create one
   allowlisted local checkpoint.

## Acceptance criteria

- [x] A formal project batch manifest requires complete, unique raw/export
  bindings and is content-hash verified before planning or execution.
- [x] Project plan/run persists and replays each declaration through the
  existing adapter, Agent, CanonicalExperiment, and ComputeRun chain.
- [x] GUI, CLI, and Agent tests prove equivalent raw/export hashes, canonical
  template identity, and per-file result provenance for one shared fixture.
- [x] Existing single-file and native grouped workflows remain unchanged.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_workflow_portable_export.py tests/test_agent_portable_export_replay.py tests/test_main_window_workers.py tests/test_portable_export_cross_entry.py
python scripts/verify.py --task docs/agent/tasks/2026-09-08-portable-export-project-closure.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(workflow): close portable export project chain" `
  --files path/to/source.py tests/test_portable_export_cross_entry.py docs/agent/tasks/2026-09-08-portable-export-project-closure.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

## Completion evidence

- `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_portable_export.py tests/test_agent_portable_export_replay.py tests/test_project_workflow_adapters.py tests/test_project_workflow_cli.py tests/test_project_workflow_models.py tests/test_import_suggestions.py tests/test_main_window_workers.py tests/test_portable_export_cross_entry.py` → 99 passed.
- `python -m ruff check` on all changed source/tests → passed; `python -m py_compile` on the same files → passed; `git diff --check` → passed.
- `python scripts/verify.py --task docs/agent/tasks/2026-09-08-portable-export-project-closure.md --changed --types` → selected checks passed (quality 313, preprocessing 157, whitespace).
- Cross-entry regression compares GUI BatchWorker, project CLI/resume, and Agent series replay for canonical template hash, raw/export hashes, exporter, and per-file binding.
- Known limitations or follow-up: native grouped portable sequences,
  arbitrary-name GUI export maps, and architecture/scientific review remain
  follow-up boundaries.
- Pre-existing changes left untouched: user-owned `service.py` edits and
  unrelated plans, reference files, and temporary test artifacts.
