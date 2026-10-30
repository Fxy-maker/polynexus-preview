---
task_id: 2026-09-05-mechanics-foundation
kind: scientific
status: completed
date: 2026-09-05
title: Add sample-neutral mechanics curve foundation
---

# Add Sample-Neutral Mechanics Curve Foundation

## Goal

Add one shared canonical and deterministic Core route for common polymer
mechanics table exports. Preserve explicit test axes and response channels,
emit traceable descriptive candidates, and keep model-dependent mechanics
interpretations unavailable until their test semantics are supplied.

## Non-goals

- Do not infer yield stress/strain, Young's or flexural modulus, toughness,
  fracture energy, fatigue life, creep parameters, or failure mechanism from a
  generic response curve.
- Do not guess tensile/compression/flexural/impact test geometry, gauge length,
  cross-section, strain rate, specimen chemistry, baseline, or endpoint rules.
- Do not create mechanics-private run, evidence, project, GUI, or persistence
  contracts.
- Do not promote the existing `mechanics.*` descriptors in this foundation.

## Shared objects and entry points

- Objects: `CanonicalExperiment`, `Measurement`, `AnalysisResult`, `ComputeRun`,
  metric manifest, project recipe, and evidence package.
- CLI/Batch/Codex/project: `mechanics` is canonical and all routes share
  `mechanics_curve_1d.v1`; no alias is introduced in this stage.
- GUI: unchanged; it discovers the registered engine and consumes public result
  objects.

## Affected boundaries

- Generic one-dimensional table conversion and converter registry.
- Generic curve capability family and AI descriptor discovery.
- New pure mechanics processing and engine modules.
- ComputeRun, CLI, Batch, and project adapter/index routing.
- Public Research Preview documentation and focused regressions.

## Implementation plan

1. Add failing mechanics processing and canonical conversion coverage for
   explicit stress/force/displacement/strain response columns.
2. Implement source-preserving mechanics processing and a registered engine;
   keep model-dependent properties unavailable without test semantics.
3. Extend the shared one-dimensional converter, capability families, and
   ComputeRun admission for `mechanics`.
4. Route mechanics through CLI, Batch, project index/adapters/service, and the
   existing result/evidence objects, then verify mixed-project behavior.
5. Update public maturity documentation and durable agent state, run the
   structured verifier, and checkpoint only the explicit allowlist.

## Acceptance criteria

- [x] Explicit time/displacement/strain/deflection/cycle axes preserve every
  unambiguous stress, force, load, strain, displacement, energy, and modulus
  signal with units, source locator, and source values.
- [x] A recorded response peak candidate and raw integral are diagnostic,
  unit-aware, source-preserving, and locally unavailable for incompatible axes.
- [x] Yield/modulus/toughness/fatigue/creep summaries remain explicitly
  unavailable with actionable reasons when required test semantics are absent.
- [x] `mechanics` CLI, Batch, direct/prevalidated ComputeRun, generic capability
  items, project adapters, and metric manifest share the same canonical/result
  objects.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_mechanics_processing.py tests/test_mechanics.py tests/test_canonical_one_dimensional.py
python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_capability_execution.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py
python scripts/verify.py --task docs/agent/tasks/2026-09-05-mechanics-foundation.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add mechanics foundation" `
  --files docs/agent/tasks/2026-09-05-mechanics-foundation.md `
          polynexus/core/canonical_experiments/one_dimensional.py `
          polynexus/core/canonical_experiments/registry.py `
          polynexus/core/canonical_experiments/capabilities.py `
          polynexus/core/ai_platform/capabilities.py `
          polynexus/core/mechanics_processing.py polynexus/core/mechanics.py `
          polynexus/core/compute/service.py polynexus/core/__init__.py `
          polynexus/core/project_workflow/index.py `
          polynexus/core/project_workflow/adapters.py `
          polynexus/core/project_workflow/service.py `
          polynexus/cli/parser.py polynexus/cli/run_single_service.py `
          polynexus/cli/batch_run_service.py `
          tests/test_mechanics_processing.py tests/test_mechanics.py `
          tests/test_project_workflow_index.py `
          tests/test_project_workflow_adapters.py `
          tests/test_ai_native_project_entrypoint.py `
          README.md docs/OPEN_SOURCE.md `
          docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes:
  - `python -m pytest -p no:cacheprovider -q tests/test_mechanics_processing.py tests/test_mechanics.py tests/test_canonical_one_dimensional.py`: 33 passed.
  - `python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_capability_execution.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py`: 118 passed, 3 skipped.
  - `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_index.py`: passed with the mechanics directory regression.
  - `python -m compileall -q` on changed Python modules: passed.
  - `git diff --check`: passed.
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-05-mechanics-foundation.md --changed --types`: task and memory checks passed; the command exits 1 on the repository's pre-existing Ruff errors in `polynexus/core/engine.py` (no new Ruff errors were reported for mechanics files).
- The mechanics engine is registered as `mechanics`, and all entry points use
  `mechanics_curve_1d.v1` with the shared ComputeRun, metric manifest, and
  evidence projections.
- Known limitations or follow-up: geometry-aware stress/strain conversion,
  formal modulus/yield/toughness/fatigue/creep models, uncertainty, independent
  replay, vendor binary readers, and capability promotion remain separate
  stages.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  manuscript plans/specs, `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/`.
