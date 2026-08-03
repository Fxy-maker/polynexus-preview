---
task_id: 2026-08-03-saxs-orientation-reliability-program
kind: scientific
status: planned
date: 2026-08-03
title: Execute the SAXS orientation reliability program in five atomic tasks
---

## Goal

Provide one ordered handoff for Luna to implement the approved SAXS
orientation reliability roadmap without merging its five scientific and
cross-layer milestones into one change or checkpoint.

## Scientific boundary

The program must not force zero-strain orientation to zero, force monotonic
strain behavior, infer a tensile axis from scattering, subtract a suspected
instrument harmonic without calibration, or allow AI to change scientific
values or gates.

## Non-goals

- Do not implement product code in the planning checkpoint.
- Do not combine the five implementation checkpoints.
- Do not infer scientific thresholds, physical labels, or calibration
  equations not approved in the linked specifications.
- Do not push, merge, deploy, edit real EDFs, or overwrite parallel work.

## Affected boundaries

- Five linked design specifications under `docs/superpowers/specs/`.
- Five linked implementation plans under `docs/superpowers/plans/`.
- Five linked implementation task cards under `docs/agent/tasks/`.
- This program entry card.

## Implementation plan

1. Execute Task 1 and checkpoint q-resolved orientation reliability evidence.
2. Review real-data evidence, then execute Task 2 feature tracking.
3. Review stable DTOs, then execute Task 3 tensile-axis capture and results.
4. Execute Task 4 calibration plugin in fail-closed mode; do not claim real
   calibration validation or register a production numerical backend without
   reviewed equations and calibration EDF inputs.
5. Execute Task 5 AI advisory only after Tasks 1-4 contracts are stable.

## Ordered tasks

1. `2026-08-03-saxs-q-resolved-orientation-reliability`
2. `2026-08-03-saxs-orientation-feature-tracking`
3. `2026-08-03-saxs-tensile-axis-results-presentation`
4. `2026-08-03-saxs-calibration-correction-plugin`
5. `2026-08-03-saxs-orientation-ai-advisory`

Each task has its own task card, spec, plan, changed-file allowlist,
verification evidence, and commit. Luna must not begin the next task before
the current task passes its focused tests, complete SAXS matrix, structured
verifier, cumulative-diff review, and scientific stop gate.

Luna should use `superpowers:subagent-driven-development` for each task, update
that task card with fresh evidence, and run only the task card's explicit
`auto_commit.py` allowlist. This program card is an entry point, not an
aggregate product-code checkpoint.

## Luna Goal prompt

```text
Read AGENTS.md, then execute docs/agent/tasks/2026-08-03-saxs-orientation-reliability-program.md exactly in order. Use each linked spec and implementation plan. Complete Tasks 1 through 5 as separate TDD changes, verification runs, cumulative-diff reviews, and explicit-allowlist auto_commit checkpoints. Continue automatically when a task passes and no documented stop gate is triggered. Pause for the user only on a listed scientific/contract stop gate or repeated verification failure. Do not push, merge, deploy, edit real EDFs, activate an unreviewed calibration backend, or let AI mutate analysis.
```

## Stop gates

- Pause on any proposed new physical threshold not already approved.
- Pause on any new chain, lamellar, or void-vector assignment.
- Pause if real EDF evidence contradicts the input or support contracts.
- Pause if a task requires changing a previous task's public DTO semantics.
- Pause before activating a real calibration correction without reviewed
  calibration files and provenance.
- Pause before allowing AI output to create or apply a scientific candidate.

## Acceptance criteria

- [ ] All five tasks remain independent checkpoints in the documented order.
- [ ] Every task preserves existing fail-closed detector and publication gates.
- [ ] Task 4 distinguishes software readiness from real calibration validity.
- [ ] Task 5 remains advisory-only and cannot mutate analysis state.
- [ ] No push, merge, deploy, data edit, or task consolidation occurs.

## Verification

Each task uses the exact commands in its own task card and plan. The program is
complete only when all five task cards contain fresh evidence and the final
release/boundary verifier passes.

Planning-package verification:

```powershell
$env:PYTHONUTF8='1'
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-orientation-reliability-program.md --changed --types
git diff --check
```

## Pre-existing workspace changes

The current dirty index, parallel GUI/AI/memory changes, test artifacts, and
real datasets are outside this planning checkpoint and every implementation
task unless explicitly listed by that task's allowlist.
