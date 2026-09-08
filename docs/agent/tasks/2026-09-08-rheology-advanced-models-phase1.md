---
task_id: 2026-09-08-rheology-advanced-models-phase1
kind: scientific
status: implementation_complete_review_required
date: 2026-09-08
title: Add explicit rheology yield-stress and LVE/gel-point candidates
---

# Rheology advanced models phase 1

## Goal

Extend the existing sample-neutral rheology Core with explicit, reproducible
yield-stress fitting and LVE/gel-point candidate calculations while keeping
all source signals and the shared `CanonicalExperiment → ComputeRun` route.

## Non-goals

- Do not infer a material model, sample identity, geometry, calibration, or
  publication conclusion from a table.
- Do not auto-select a fit model or silently reinterpret ambiguous signals.
- Do not promote these diagnostic candidates to formal capabilities; independent
  replay, uncertainty/metrology, standards, and human scientific review remain
  required.
- Do not implement thixotropy, Cox–Merz, creep/relaxation, TTS, or new vendor
  readers in this phase.

## Shared objects and entry points

- Core: immutable explicit rheology analysis spec carried by the canonical
  template payload; deterministic metrics and metric-manifest provenance.
- ComputeRun: prevalidated canonical rheology templates execute through the
  existing `RheologyEngine` and retain method/parameter/source metadata.
- CLI/AI/GUI: existing routes remain compatible; the generic Core option can
  carry the explicit spec without creating a private result representation.
- Cross-entry rule: direct Core/CLI and prevalidated Agent/GUI routes consume
  the same canonical payload and output metric paths.

## Affected boundaries

- `polynexus/core/rheology_processing.py`: immutable analysis specs and
  deterministic yield/LVE candidate calculations.
- `polynexus/core/rheology.py` and `polynexus/core/compute/service.py`:
  canonical-template propagation and shared ComputeRun execution.
- `polynexus/core/agent_workflow/service.py`: replay the validated rheology
  spec after source conversion without changing raw provenance.
- `polynexus/cli/parser.py` and `polynexus/cli/run_single_service.py`: explicit
  CLI spec input routed to the shared ComputeRun service.
- Focused processing, ComputeRun, Agent replay, and CLI regression tests.

## Implementation plan

1. Define immutable yield-stress and LVE analysis specs with explicit models,
   source measurement IDs, units, windows, thresholds, and JSON projection.
2. Compute Bingham/Herschel–Bulkley and strain-sweep plateau/crossover
   candidates while preserving source signals and local unavailable reasons.
3. Carry the spec through canonical templates and shared ComputeRun; reapply it
   during Agent replay so replay hashes and results remain identical.
4. Expose the same request through CLI JSON input and verify direct, replay,
   Agent, and CLI metric-manifest projections.
5. Keep results diagnostic and document independent replay, uncertainty, and
   human scientific-review requirements before capability promotion.

## Acceptance criteria

- [x] Explicit spec validates model, measurement IDs, units, windows, and LVE
  thresholds; malformed or incomplete semantics leave only affected metrics
  unavailable.
- [x] Bingham and Herschel–Bulkley fits (or an explicitly documented subset)
  return deterministic yield-stress diagnostics with fit quality and source
  provenance; nonpositive/insufficient/ambiguous input fails locally.
- [x] LVE plateau and gel-point crossover candidates are deterministic,
  unit-normalized, preserve all source arrays, and record boundary/multiple-
  candidate warnings without blocking descriptive outputs.
- [x] Canonical prevalidated ComputeRun, direct CLI/Core, and Agent/GUI-facing
  adapters expose identical metric paths, method labels, and parameters.
- [x] Existing rheology identity tests remain green and descriptor status stays
  non-promoted until validation evidence and human review exist.

## Follow-up

Independent instrument/material replay, standard samples and negative controls,
formal uncertainty/metrology, and human scientific review remain required before
these diagnostic candidates can be promoted to a formal capability. Thixotropy,
Cox–Merz, creep/relaxation, TTS/master curves, and vendor-specific readers are
outside this phase.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_rheology_processing.py tests/test_rheology.py tests/test_compute_run_projection.py tests/test_agent_workflow_contracts.py
python scripts/verify.py --task docs/agent/tasks/2026-09-08-rheology-advanced-models-phase1.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(rheology): add explicit yield and LVE candidates" `
  --files path/to/source.py tests/test_rheology_processing.py tests/test_rheology.py docs/agent/tasks/2026-09-08-rheology-advanced-models-phase1.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes: focused rheology/ComputeRun/Agent/CLI matrix
  passed (`78 passed`); `python scripts/verify.py --task
  docs/agent/tasks/2026-09-08-rheology-advanced-models-phase1.md --changed
  --types` passed task-check, Ruff, compile, quality (`313`), preprocessing
  (`157`), and whitespace checks.
- Known limitations or follow-up: validation/replay, uncertainty, scientific
  review, and later rheology models remain open.
- Pre-existing changes left untouched: user-owned
  `polynexus/core/agent_workflow/service.py` edits and unrelated untracked
  plans/reference files/test artifacts.
