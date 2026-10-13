---
task_id: 2026-09-08-gui-portable-export-import
kind: architecture
status: complete
date: 2026-09-08
title: Bind portable exports from the GUI import dialog
---

# Bind portable exports from the GUI import dialog

## Goal

Allow the GUI import flow to associate an opaque vendor file with a user-
selected portable table export and execute it through the existing canonical
conversion and ComputeRun contracts.

## Non-goals

- Do not decode private vendor bytes in the GUI or add a second result store.
- Do not infer exporter calibration, units, sample grouping, or scientific
  meaning beyond the existing canonical converter.
- Do not change directory/batch import semantics in this task.
- Do not auto-copy, move, or delete user files.

## Shared objects and entry points

- Objects: `ImportSuggestion`, `AnalysisWorker`, `ComputeRun`, and the existing
  raw/export provenance binding.
- AI/Codex/CLI: unchanged; they continue to use the existing portable-export
  and recipe contracts.
- GUI: reads and creates only the shared import declaration, then delegates
  conversion/execution to the existing worker/Core boundary.
- Cross-entry rule: the GUI uses the same canonical converter and
  `ComputeRunService` as CLI and AgentWorkflow; it does not persist a GUI-only
  result or provenance representation.

## Affected boundaries

- `polynexus/gui/main_window_import_mixin.py` and `main_window.py`: dialog
  selection and shared GUI import state.
- `polynexus/gui/main_window_run_mixin.py` and `main_window_workers.py`: pass
  the declared export through the existing ComputeRun worker.
- `polynexus/gui/import_suggestions.py`: public import suggestion DTO.
- Focused GUI import/worker tests and durable agent memory.

## Implementation plan

1. Extend the public GUI import suggestion with an optional portable-export
   declaration and add dialog controls for the export path and exporter label.
2. Carry the declaration through GUI import state without changing ordinary or
   directory imports.
3. Resolve the export through the shared canonical converter in the existing
   analysis worker and execute it via `ComputeRunService` with raw provenance.
4. Add focused dialog and worker regressions for successful binding and shared
   execution.
5. Run the focused matrix, task verifier, and an allowlisted local checkpoint.

## Acceptance criteria

- [x] The import dialog can optionally select a supported portable export and
  record its exporter label without changing ordinary imports.
- [x] A selected portable export is validated and reaches the existing shared
  ComputeRun with the raw file as source provenance.
- [x] The GUI provider path consumes the export table, not opaque raw bytes.
- [x] Missing/invalid export declarations fail before provider execution.
- [x] Existing GUI import and worker tests remain green.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_import_suggestions.py tests/test_agent_portable_export_replay.py
python scripts/verify.py --task docs/agent/tasks/2026-09-08-gui-portable-export-import.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(gui): bind portable exports from import dialog" `
  --files polynexus/gui/i18n.py polynexus/gui/import_suggestions.py polynexus/gui/main_window.py polynexus/gui/main_window_import_mixin.py polynexus/gui/main_window_run_mixin.py polynexus/gui/main_window_workers.py tests/test_import_suggestions.py tests/test_main_window_workers.py docs/agent/tasks/2026-09-08-gui-portable-export-import.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes: focused GUI/worker/Agent matrix `41 passed`;
  `scripts/verify.py --task ... --changed --types` passed Ruff, compile,
  quality `313`, preprocessing `157`, and whitespace checks.
- Known limitations or follow-up: GUI visual review, architecture review,
  scientific review, and private vendor decoding remain open.
- Pre-existing changes left untouched: the user-owned uncommitted
  `agent_workflow/service.py` changes and unrelated plans, reference files,
  and temporary test artifacts.
