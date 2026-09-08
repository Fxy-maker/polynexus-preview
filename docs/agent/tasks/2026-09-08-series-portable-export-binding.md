---
task_id: 2026-09-08-series-portable-export-binding
kind: architecture
status: complete
date: 2026-09-08
title: Bind portable exports for multi-file and sequence runs
---

# Bind portable exports for multi-file and sequence runs

## Goal

Extend source-bound portable exports from one raw file to a strictly matched
set of raw files and exported tables across GUI batch runs and project/Agent
series recipes.

## Non-goals

- Do not treat a whole directory as one unverified export.
- Do not infer scientific grouping, calibration, units, or sample identity.
- Do not change native directory workflows for SAXS/WAXS/NMR/IR temperature
  runs in this task.
- Do not decode private vendor bytes or create a second provenance store.

## Shared objects and entry points

- Objects: per-file `PortableExportBinding`, `CanonicalExperiment`, and
  `ComputeRun` projections.
- GUI: creates a portable-export-directory declaration and passes it to the
  existing `BatchWorker`.
- Project/Agent: accepts ordered `portable_exports` declarations on the
  existing series recipe; Agent replay selects the declaration for the
  matching artifact index.
- Cross-entry rule: every file uses the same canonical converter and shared
  ComputeRun; raw artifacts remain provenance anchors.

## Affected boundaries

- Core/project recipes: `TechniqueSeriesAdapter` admits one explicit portable
  declaration per raw artifact and persists independent canonical templates.
- Agent/Codex replay: `AgentWorkflowService` selects the declared export for
  the matching artifact index before shared ComputeRun execution.
- GUI batch: `ImportSuggestionDialog`, `MainWindowRunMixin`, and `BatchWorker`
  pass a portable-export directory only through one-to-one preflight mapping.
- Unchanged boundaries: single-file portable export, CLI portable export, and
  native grouped SAXS/WAXS/NMR/IR directory workflows retain their existing
  routes; the latter reject this directory declaration explicitly.

## Implementation plan

1. Add ordered portable-export declarations to series adapter proposals and
   recipe validation.
2. Make Agent admission select the portable declaration for each artifact
   instead of reusing the first same-technique step.
3. Add strict GUI batch mapping from raw file stems to export files and route
   every pair through the existing portable binding and ComputeRun service.
4. Add focused adapter, Agent, GUI dialog, and BatchWorker regressions.
5. Run focused tests, the structured verifier, and create an allowlisted local
   checkpoint.

## Acceptance criteria

- [x] Every raw file in a series/batch has exactly one export or the run fails
  before provider execution.
- [x] Raw/export hashes and per-file canonical templates remain independent.
- [x] Agent replay uses the matching export for each artifact index.
- [x] Ordinary and native directory workflows remain unchanged.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_workflow_adapters.py tests/test_agent_portable_export_replay.py tests/test_import_suggestions.py tests/test_main_window_workers.py
python scripts/verify.py --task docs/agent/tasks/2026-09-08-series-portable-export-binding.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(workflow): bind portable exports for series runs" `
  --files path/to/changed/source.py path/to/focused_test.py docs/agent/tasks/2026-09-08-series-portable-export-binding.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

## Completion evidence

- `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_portable_export.py tests/test_agent_portable_export_replay.py tests/test_project_workflow_adapters.py tests/test_import_suggestions.py tests/test_main_window_workers.py` — 79 passed.
- `python -m ruff check polynexus/core/project_workflow/adapters.py polynexus/core/agent_workflow/service.py polynexus/gui/main_window.py polynexus/gui/main_window_run_mixin.py polynexus/gui/main_window_workers.py polynexus/gui/i18n.py tests/test_project_workflow_portable_export.py tests/test_agent_portable_export_replay.py tests/test_main_window_workers.py` — passed.
- `python -m py_compile polynexus/core/project_workflow/adapters.py polynexus/core/agent_workflow/service.py polynexus/gui/main_window.py polynexus/gui/main_window_run_mixin.py polynexus/gui/main_window_workers.py polynexus/gui/i18n.py tests/test_project_workflow_portable_export.py tests/test_agent_portable_export_replay.py tests/test_main_window_workers.py` — passed.
- `python scripts/verify.py --task docs/agent/tasks/2026-09-08-series-portable-export-binding.md --changed --types` — passed (task card, memory, Ruff, compile, quality 313, preprocessing 157, whitespace).
- `git diff --check` — passed.
- Known limitations or follow-up: native grouped directory workflows and
  arbitrary-name export maps remain follow-up; GUI visual review remains open.
- Pre-existing changes left untouched: user-owned `service.py` edits and
  unrelated plans, reference files, and temporary test artifacts.
