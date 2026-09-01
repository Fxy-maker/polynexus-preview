---
task_id: 2026-09-01-first-ai-research-loop
kind: architecture
status: proposed
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

## Acceptance criteria

- [ ] Public mixed-technique fixture completes through evidence package and
      manuscript draft from a documented entry point.
- [ ] Real external project replay is read-only and produces an acceptance
      record without copying raw files into the repository.
- [ ] All applicable metrics are present in ComputeRun, JSON, CSV, result
      tables, and evidence projections, including warnings and unavailable or
      failed reasons.
- [ ] Figures are generated from FigurePlan and bind source runs and plotted
      data; no duplicate private figure representation is introduced.
- [ ] ARS writing input is package-relative and the manuscript path consumes
      existing metrics without recomputation or fabricated numbers.
- [ ] Source/mapping changes create new revisions and do not overwrite prior
      runs or evidence.
- [ ] Ordinary quality warnings do not block finite deterministic results;
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

- Exact commands and outcomes:
- Public fixture output path:
- External real-project replay path and read-only verification:
- Known limitations or follow-up:
- Pre-existing changes left untouched:
