---
task_id: 2026-08-13-workbench-surface-convergence
kind: architecture
status: implementation_complete_review_required
date: 2026-08-13
title: Define the converged workbench surface
---

# Workbench Surface Convergence

## Goal

Define the user-visible PolyNexus surface and a staged migration of existing
modules to one AI-controllable, independently usable research workbench.

## Non-goals

- Do not delete, hide, or rewrite any runtime module in this task.
- Do not change deterministic analysis, scientific semantics, data formats, or
  real regression datasets.
- Do not decide the final removal of RAG, Joint, Origin, or NMR before their
  replacement workflow is proven.

## Shared objects and entry points

- Objects: project, run, chart, evidence package, export. No contract changes.
- AI/Codex/CLI: unchanged; `project-workflow analyze-project` remains the
  producer of project analysis and evidence packages.
- GUI: unchanged; the design identifies how it will consume the same public
  objects in later tasks.
- Cross-entry rule: every later migration must use the existing public object
  contract and prove the affected CLI/AI and GUI consumers together.

## Affected boundaries

- `docs/superpowers/specs/2026-08-13-workbench-surface-convergence-design.md`:
  product surface, module disposition, and staged migration decision.
- `docs/agent/tasks/2026-08-13-workbench-surface-convergence.md` and
  `docs/agent/memory/active-work.md`: durable task scope and next action.

## Context and output budget

- Read first: `AGENTS.md`, current product memory, workflow contract, current
  GUI navigation, and project-workflow entrypoint.
- Search scope: `polynexus/gui/main_window*`, project workflow, CLI parser, and
  task/spec artifacts.
- Expand only for: a module classification that lacks a concrete producer,
  consumer, or replacement path.
- Report: design outcome, changed documents, exact verification result,
  migration limits, and untouched workspace changes.

## Acceptance criteria

- [x] Specify the default workbench, quick analysis, and advanced-tool
  surfaces without creating separate object models.
- [x] Classify current user-facing modules with a target surface and a
  precondition before any removal.
- [x] Specify an ordered set of atomic follow-up tasks and the first runtime
  task that changes GUI behavior.
- [x] Record that RAG is a candidate for later optionalization, not the first
  removal action.
- [x] Record human architecture review requirement before implementation.

## Implementation plan

1. Inspect the existing GUI navigation and public project-workflow entrypoint.
2. Define the converged surfaces and classify each current user-facing module.
3. Record removal preconditions, staged runtime tasks, and architecture review
   requirement without changing runtime behavior.
4. Validate the task/document contract and create an allowlisted checkpoint.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-13-workbench-surface-convergence.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "docs(product): define workbench surface convergence" `
  --files docs/agent/tasks/2026-08-13-workbench-surface-convergence.md docs/superpowers/specs/2026-08-13-workbench-surface-convergence-design.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes: `python scripts/verify.py --task
  docs/agent/tasks/2026-08-13-workbench-surface-convergence.md --changed
  --types` passed; the selected quality gates passed 303 and 157 tests.
- Known limitations or follow-up: runtime migration is blocked on human
  architecture review of the Project Workbench default surface, Quick Analysis
  expert path, and RAG deferral decision.
- Pre-existing changes left untouched: `.superpowers/` and
  `tests/_tmp_phase3/`.
