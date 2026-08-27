---
task_id: 2026-08-27-architecture-scientific-repair
kind: architecture
status: active
date: 2026-08-27
title: Repair directory provenance and DSC evidence eligibility
---

# Repair directory provenance and DSC evidence eligibility

## Goal

Remove the three merge-blocking findings from the architecture/scientific
review: directory hash drift, unenforced ComputeRun provenance, and overly broad
DSC Results eligibility.

## Non-goals

- Do not modify raw data or provider algorithms.
- Do not promote FTIR, SAXS, or WAXS diagnostics.
- Do not remove legacy GUI/Batch/Codex compatibility paths.
- Do not implement package portability or confirmed-context transport in this
  atomic task.

## Shared objects and entry points

- Producer: canonical converter registry, `ComputeRunService`, Agent workflow.
- Consumers: project evidence packager, package view, citation metrics, ARS
  writing input.
- Cross-entry rule: directory hashes must be byte-identical across Agent,
  ComputeRun, converter registry, and package validation; migrated packageable
  steps must carry one matching `ComputeRun` projection.

## Affected boundaries

- Canonical conversion: directory source identity serialization.
- Project evidence packaging: recipe-step and ComputeRun provenance checks.
- ARS metric projection: DSC Avrami eligibility and duplicate suppression.
- Unchanged: raw readers, provider algorithms, GUI rendering, Batch storage,
  and FTIR/SAXS/WAXS metric rules.

## Context and output budget

- Read first: architecture/scientific review, canonical converter registry,
  ComputeRun/Agent contracts, package validator, and writing metric tests.
- Search scope: `polynexus/core/canonical_experiments`,
  `polynexus/core/project_workflow`, and the focused package/evidence tests.
- Report: changed contracts, focused verification counts, remaining P1/P2
  limitations, and untouched workspace artifacts.

## Implementation plan

1. Align directory manifest hashing with the `RawArtifact` envelope and add a
   cross-entry regression test.
2. Add package validation for step/recipe alignment and completed,
   artifact-bound ComputeRun projections; cover missing and mismatched cases.
3. Filter flagged or low-fit DSC Avrami metrics to diagnostic-only and suppress
   equivalent `best_avrami` duplicates without changing provider output.
4. Run focused producer/consumer tests, record acceptance evidence, and create
   one allowlisted local checkpoint.

## Acceptance criteria

- [x] All directory hash producers use the same `directory_manifest` envelope.
- [x] Package validation rejects a migrated step whose ComputeRun is missing or
  whose artifact/template identity does not match the recipe.
- [x] DSC metrics with quality flags or low Avrami R² are not Results
  candidates; `best_avrami` does not duplicate a segment metric.
- [x] Existing FTIR/SAXS/WAXS diagnostic boundaries remain unchanged.
- [x] Focused tests and structured verification pass.

## Verification

```powershell
python -m pytest -q tests/test_directory_manifest_hash.py tests/test_project_workflow_package.py tests/test_project_workflow_adapters.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-architecture-scientific-repair.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "fix(provenance): repair directory hashes and DSC eligibility" `
  --files polynexus/core/canonical_experiments/registry.py polynexus/core/project_workflow/package.py polynexus/core/project_workflow/writing_metrics.py tests/test_directory_manifest_hash.py tests/test_project_workflow_package.py docs/agent/tasks/2026-08-27-architecture-scientific-repair.md docs/acceptance/2026-08-27-architecture-scientific-repair.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes: recorded in
  `docs/acceptance/2026-08-27-architecture-scientific-repair.md`.
- Known limitations: package portability, GUI batch persistence, generic
  capability coverage, and confirmed cross-sample context remain follow-ups.
- Pre-existing changes left untouched: `active_run.json`, `runs/`,
  `tests/_tmp_phase3/`, and historical test artifacts.
