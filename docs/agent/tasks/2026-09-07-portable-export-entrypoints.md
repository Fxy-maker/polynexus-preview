---
task_id: 2026-09-07-portable-export-entrypoints
kind: architecture
status: complete
date: 2026-09-07
title: Expose source-bound portable exports through CLI and project/Codex routes
---

# Expose source-bound portable exports through CLI and project/Codex routes

## Goal

Make the existing `PortableExportBinding`/canonical conversion route usable
from a machine-readable CLI and project/Codex manifests, without treating a
Proteus/Origin export as the original private instrument file.

## Non-goals

- Do not decode or reverse-engineer private vendor bytes.
- Do not add a second result/provenance representation.
- Do not add a GUI dialog or change GUI layout in this task.
- Do not infer exporter calibration or scientific semantics.

## Affected boundaries

- `polynexus/cli/parser.py`, `polynexus/__main__.py`, and a focused CLI
  adapter for the public `portable-export` command.
- `polynexus/core/project_workflow/adapters.py` so a project/Codex manifest
  can declare the same source-bound export request.
- Focused CLI and project adapter regression tests.

## Implementation plan

1. Add a machine-readable `portable-export` CLI adapter over the shared
   canonical converter and optional `ComputeRunService` execution.
2. Extend the project/Codex single-input manifest with a validated
   `portable_export` declaration while preserving the opaque raw artifact.
3. Persist the same canonical template and converter metadata in the project
   recipe; leave protected agent-workflow replay code untouched in this task.
4. Add focused regression tests and run the structured verifier.

## Acceptance criteria

- [x] CLI accepts raw private source, portable table, technique, and exporter;
  conversion-only JSON includes both independent hashes and the canonical
  template.
- [x] CLI can optionally execute the resulting canonical template through the
  existing `ComputeRunService` and emits the shared run projection.
- [x] Project/Codex single-input manifests can declare `portable_export` and
  persist the same canonical template/converter metadata.
- [x] Invalid/missing/mismatched portable inputs fail closed with stable reason
  codes and never invoke a provider.
- [ ] Existing direct input and project routes remain unchanged.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_portable_export_cli.py tests/test_project_workflow_adapters.py
python scripts/verify.py --task docs/agent/tasks/2026-09-07-portable-export-entrypoints.md --changed --types
git diff --check
```

## Completion evidence

- Focused entry-point/project/CLI parser coverage: `41 passed`.
- Structured verifier: Ruff, compilation, quality gate `313 passed`,
  preprocessing `157 passed`, and whitespace checks passed.
- The pre-existing `polynexus/core/agent_workflow/service.py` worktree changes
  were intentionally left untouched; opaque-source agent replay and GUI intake
  remain follow-up work.
