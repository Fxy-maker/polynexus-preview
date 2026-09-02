---
task_id: 2026-09-01-first-ai-research-loop
kind: architecture
status: implementation_complete_review_required
date: 2026-09-01
title: Complete the first AI-native mixed-technique research loop
---

# Complete the First AI-Native Mixed-Technique Research Loop

## Goal

Given one project directory and an explicit AI/Codex file-group request,
produce a shared, reproducible path from template conversion through
deterministic multi-technique computation, figures, evidence package, ARS
writing input, and an evidence-grounded manuscript draft.

## Non-goals

- Do not redesign the GUI or remove quick analysis, Batch, Origin, or RAG.
- Do not add every vendor format or future technique in this task.
- Do not require accounts, plugins, or a regulated approval workflow.
- Do not modify real source data or commit personal manuscript/runtime output.
- Do not claim publication-ready scientific conclusions automatically.

## Shared objects and entry points

- Objects: project, analysis plan, canonical experiment, ComputeRun, metric
  manifest, GroupResultTable, FigurePlan, evidence package, ARS writing input,
  manuscript/preflight.
- AI/Codex/CLI: creates the selected project request, invokes the shared
  project workflow, reads serialized runs/evidence, and requests ARS actions.
- GUI: consumes the same run, result-table, figure, and evidence DTOs; it does
  not implement technique-specific computation.
- Batch: uses the same template and ComputeRun route for selected groups.
- Cross-entry rule: the project workflow is the producer; CLI, Codex, ARS, and
  GUI adapters are consumers of the same serialized objects.

## Affected boundaries

- `polynexus/core/project_workflow`: compose the existing project analysis,
  evidence package, result-table, and manuscript projections.
- `polynexus/core/compute`: keep the shared `ComputeResult.metric_manifest`
  truthful for optional `None` metrics; no provider algorithm changes.
- `polynexus/core/ai_platform` and `core/agent_workflow`: preserve strict
  `ProviderResultInput` validation while accepting explicit unavailable rows.
- `polynexus/cli`: expose the same close-loop summary to Codex/ARS callers.
- `polynexus/suite`: consume package evidence for writing input and manuscript
  preflight without reparsing raw data.
- GUI and Batch remain DTO consumers and are not redesigned in this task.

## Implementation plan

1. Add and verify a regression test for empty optional metric projection.
2. Fix `ComputeResult.metric_manifest()` to emit `unavailable` for scalar
   `None` leaves without weakening `ProviderResultInput` validation.
3. Run the public fixture and a read-only mixed PA6 replay through
   `project-workflow close-loop`.
4. Verify evidence, figure, result-table, ARS writing, manuscript, and
   preflight bindings, then record durable acceptance and limitations.
5. Run task-scoped and release-boundary verification and create an allowlisted
   local checkpoint; defer open-source preparation to a separate task.

## Acceptance criteria

- [x] Public mixed-technique fixture completes through evidence package and
      manuscript draft from a documented entry point.
- [x] Real external project replay is read-only and produces an acceptance
      record without copying raw files into the repository.
- [x] All applicable metrics are present in ComputeRun, JSON, CSV, result
      tables, and evidence projections, including warnings and unavailable or
      failed reasons.
- [x] Figures are generated from FigurePlan and bind source runs and plotted
      data; no duplicate private figure representation is introduced.
- [x] ARS writing input is package-relative and the manuscript path consumes
      existing metrics without recomputation or fabricated numbers.
- [x] Source/mapping changes create new revisions and do not overwrite prior
      runs or evidence.
- [x] Ordinary quality warnings do not block finite deterministic results;
      structural data/provenance failures still fail closed.

## Verification

```powershell
# Focused fixture/project/evidence/ARS matrix
python -m pytest -p no:cacheprovider -q `
  tests/test_ai_native_project_entrypoint.py `
  tests/test_ai_project_candidate_groups.py `
  tests/test_ai_platform_cross_entry.py `
  tests/test_all_data_manuscript_builder.py

# Structured task verification
python scripts/verify.py --task docs/agent/tasks/2026-09-01-first-ai-research-loop.md --changed --types

# Release-boundary verification before handoff
python scripts/verify.py --changed --types --full --boundary
git diff --check
```

## Checkpoint allowlist

After verification, run `scripts/auto_commit.py` with message
`feat(research-loop): complete first mixed-technique AI path` and an explicit
allowlist containing the task card plus only the source and test files changed
for this task. Derive and review that allowlist at completion; never include
real datasets, generated manuscripts, or local runtime directories.

## Completion evidence

- Exact commands and outcomes: see `docs/acceptance/2026-09-01-first-ai-research-loop.md`.
- Public fixture output path: pytest-managed temporary project; no generated
  output is committed.
- External real-project replay path and read-only verification:
  `D:\PolyNexus-pa6-loop-20260902-clean`; source hashes are unchanged.
- Known limitations or follow-up: package remains `review_required`; NMR is
  absent from the selected project; open-source preparation is separate.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  `active_run.json`, `runs/`, `tests/_tmp_phase3/`, historical plans/specs,
  and personal literature/manuscript files.
