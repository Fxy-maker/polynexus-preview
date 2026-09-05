---
task_id: 2026-09-05-generic-project-table-techniques
kind: architecture
status: implementation_complete_review_required
date: 2026-09-05
title: Route generic table techniques through the shared project workflow
---

# Route Generic Table Techniques Through the Shared Project Workflow

## Goal

Make the existing TGA, DMA, and rheology table foundations available to the
AI-native project workflow through the same index, canonical adapters,
ComputeRun, result-table, evidence-package, and ARS-facing contracts already
used by other techniques.

## Non-goals

- Do not add technique-private project, run, evidence, figure, or persistence
  objects.
- Do not add TGA, DMA, or rheology algorithms or promote scientific
  capabilities.
- Do not infer DMA versus rheology from an ambiguous modulus-only table.
- Do not silently confirm filename-derived experiment groups or add new group
  statistics.
- Do not change GUI controls, raw artifacts, or existing provider results.

## Shared objects and entry points

- Objects: `ProjectArtifact`, `ResearchGraph`, `AnalysisRequest`,
  `AnalysisRecipe`, `CanonicalExperiment`, `ComputeRun`, `EvidenceItem`, and
  `ResearchEvidencePackage`.
- Codex/project CLI: `ProjectWorkflowService.analyze_project`, `plan`, and
  `run` use the existing single, series, and mixed adapters.
- Quick CLI/Batch/GUI: unchanged; the project route consumes the same
  canonical templates and provider results already exposed by those entries.

## Affected boundaries

- Project-local technique indexing and explicit directory aliases.
- Shared single-input, same-technique series, and mixed-technique adapters.
- AI-native project admission whitelist and scope hints.
- Focused index, adapter, project execution, package, and provenance tests.

## Implementation plan

1. Add failing coverage for TGA, DMA, and rheology adapter registration and
   canonical template binding.
2. Add explicit project index aliases while retaining `unknown` for ambiguous
   modulus-only data outside a declared technique context.
3. Admit the three techniques through the existing project planner and
   single/series/mixed adapters.
4. Verify that a mixed project emits completed shared ComputeRun projections
   and one evidence package without private technique result shapes.

## Acceptance criteria

- [x] Explicit TGA, DMA, and rheology project paths index to the correct
  technique; ambiguous modulus-only input is not guessed as DMA or rheology.
- [x] Each technique produces a valid single-input recipe bound to its existing
  canonical template and registered deterministic engine.
- [x] Multiple same-technique files use `TechniqueSeriesAdapter` with stable
  ordering and one canonical-bound step per source.
- [x] One mixed project request executes all three through shared ComputeRuns
  and packages their evidence under the existing project contracts.
- [x] Existing DSC/IR/SAXS/WAXS/NMR project behavior remains green.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_workflow_index.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py
python -m pytest -p no:cacheprovider -q tests/test_project_workflow_service.py tests/test_project_workflow_package.py tests/test_project_workflow_cli.py
python scripts/verify.py --task docs/agent/tasks/2026-09-05-generic-project-table-techniques.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(project): route generic table techniques" `
  --files docs/agent/tasks/2026-09-05-generic-project-table-techniques.md `
          polynexus/core/project_workflow/index.py `
          polynexus/core/project_workflow/adapters.py `
          polynexus/core/project_workflow/service.py `
          tests/test_project_workflow_index.py `
          tests/test_project_workflow_adapters.py `
          tests/test_ai_native_project_entrypoint.py `
          tests/test_project_workflow_service.py `
          docs/agent/memory/active-work.md `
          docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes:
  - The focused red run produced 8 expected failures and 1 passing ambiguity
    guard before the three techniques were registered with project indexing,
    adapters, and admission.
  - `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_index.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py`
    - 59 passed, 1 skipped.
  - `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_service.py tests/test_project_workflow_package.py tests/test_project_workflow_cli.py`
    - 55 passed.
  - `python -m pytest -p no:cacheprovider -q tests/test_tga.py tests/test_dma.py tests/test_rheology.py`
    - 25 passed.
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-05-generic-project-table-techniques.md --changed --types`
    - selected checks passed, including quality 313 and preprocessing 157.
  - `git diff --check` - passed through the structured verifier.
- Known limitations or follow-up: technique confirmation for ambiguous
  unlabelled inputs, scientific grouping confirmation, group statistics,
  figures, independent replay, uncertainty, and capability promotion remain
  separate work.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  manuscript plans/specs, `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/`.
