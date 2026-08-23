---
task_id: 2026-08-23-core-simplification-architecture
kind: architecture
status: complete
date: 2026-08-23
title: Define the AI-first compute-core simplification
---

# Define the AI-first Compute-Core Simplification

## Goal

Record the approved target architecture and migration boundaries that reduce
PolyNexus from a paper-review-oriented core to an AI-first deterministic data
conversion, analysis, and figure system.

## Non-goals

- Do not delete, move, or change runtime code in this documentation task.
- Do not change a scientific method, promote manuscript claims, or claim that
  direct-AI output is a numerical reference.
- Do not redesign the GUI visual layout in this task.

## Affected boundaries

- Analysis engine: target ownership of conversion, deterministic providers,
  generic figures, and numerical validation.
- Result/schema contract: future `RawArtifact`, `CanonicalDataset`,
  `AnalysisPlan`, `AnalysisResult`, and `AnalysisRun` replace overlapping
  workflow/review payloads.
- GUI/CLI/AI: all will consume one direct run/result path; this task changes no
  current behavior.
- Persistence/export: retain source/hash/plan/result/figure reproducibility;
  remove evidence-package and manuscript-specific persistence in later tasks.
- Documentation/tooling: this architecture task and the approved design record.

## Shared objects and entry points

- Objects: raw artifact, canonical dataset, analysis plan, analysis run,
  analysis result, chart, and lightweight project catalog.
- AI/Codex/CLI: future shared compute consumer; no behavior changes in this
  task.
- GUI: future shared compute consumer; no behavior changes in this task.
- Cross-entry rule: the migration must make Quick Analysis and AI tools invoke
  the same compute contracts; neither receives a private analysis or
  provenance representation.

## Implementation plan

1. Inventory current Core responsibilities and existing workflow consumers.
2. Record the agreed compute-core boundary, status semantics, and module
   retain/replace/remove classification.
3. Define dependency-safe migration batches and accuracy acceptance criteria.
4. Validate the task-card/documentation contracts and checkpoint the approved
   design; implementation remains a later, separately planned task.

## Context and output budget

- Read first: agent memory, current public workflow contracts, the existing
  agent-native core design, and scoped Core module inventory.
- Search scope: `polynexus/core`, current CLI/GUI consumers, and focused
  workflow tests.
- Expand only for: dependency mapping required by a deletion batch or a
  scientific-method migration.
- Report: design outcome, changed documents, verification, limitations, and
  untouched runtime changes.

## Acceptance criteria

- [x] The design separates computation, conversion, application entry points,
  and optional research/paper workflows.
- [x] It names the small shared contracts and their status semantics.
- [x] It classifies current Core subsystems as retain, replace, or remove.
- [x] It provides deletion batches that do not strand the GUI or AI/CLI on
  private contracts.
- [x] It records numerical-validation and scientific-boundary requirements.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-23-core-simplification-architecture.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "docs(architecture): define AI-first core simplification" `
  --files docs/agent/tasks/2026-08-23-core-simplification-architecture.md docs/superpowers/specs/2026-08-23-ai-first-core-simplification-design.md
```

## Completion evidence

- Exact commands and outcomes: task verification and whitespace verification
  are recorded after the final documentation check.
- Known limitations or follow-up: implementation requires a separate approved
  plan and atomic migration tasks.
- Pre-existing changes left untouched: `.superpowers/`, the FTIR review-loop
  task/plan/test, `ftir_group_overlay_review.png`, and `tests/_tmp_phase3/`.
