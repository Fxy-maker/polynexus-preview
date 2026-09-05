---
task_id: 2026-09-05-sec-gpc-foundation
kind: scientific
status: implementation_complete_review_required
date: 2026-09-05
title: Add sample-neutral SEC/GPC chromatogram foundation
---

# Add Sample-Neutral SEC/GPC Chromatogram Foundation

## Goal

Add one shared canonical and deterministic Core route for common SEC/GPC table
exports. Preserve unambiguous elution coordinates and detector/distribution
signals, emit traceable raw-response descriptors, and expose explicit
unavailable molecular-weight results until calibration and distribution
semantics are sufficient.

## Non-goals

- Do not infer `Mn`, `Mw`, `Mz`, dispersity, absolute molar mass, branching, or
  Mark-Houwink parameters from an ordinary detector response.
- Do not guess universal calibration, `dn/dc`, detector constants, baseline,
  peak boundaries, column exclusion limits, or sample chemistry.
- Do not merge duplicate detector channels or create SEC-private run,
  evidence, project, GUI, or persistence contracts.
- Do not promote `sec.molecular_weight.v1` or `sec.distribution.v1`.

## Shared objects and entry points

- Objects: `CanonicalExperiment`, `Measurement`, `AnalysisResult`,
  `ComputeRun`, metric manifest, project recipe, and evidence package.
- CLI/Batch/Codex/project: `sec` is canonical; `gpc` is an input alias. All
  routes consume `sec_chromatogram_1d.v1` and the same engine result.
- GUI: unchanged; it may discover the registered engine and consumes public
  result objects.

## Affected boundaries

- Generic one-dimensional table conversion and converter registry.
- Generic curve capability family and AI descriptor discovery.
- New pure SEC processing and engine modules.
- ComputeRun, CLI, Batch, and project adapter/index routing.
- Public Research Preview documentation and focused regressions.

## Implementation plan

1. Add failing SEC processing and canonical conversion coverage for one or more
   explicitly labelled detector, vendor molar-mass, and distribution columns.
2. Implement source-preserving SEC processing and a registered `sec` engine;
   keep molecular-weight moments unavailable without calibration semantics.
3. Extend the shared one-dimensional converter, capability families, and
   ComputeRun admission so `sec` is canonical and `gpc` is only an alias.
4. Route SEC/GPC through CLI, Batch, project index/adapters/service, and the
   existing result/evidence objects, then verify mixed-project behavior.
5. Update public maturity documentation and durable agent state, run the
   structured verifier, and checkpoint only the explicit allowlist.

## Acceptance criteria

- [x] Elution time/volume tables preserve every unambiguous recognized signal
  with detector/distribution kind, unit, source locator, and source values.
- [x] RI, UV, light-scattering, viscometer/pressure, concentration, and
  vendor-provided molar-mass/distribution columns remain distinct.
- [x] Response peak coordinate and baseline-uncorrected trapezoid integral are
  diagnostic, unit-aware, and locally unavailable for incompatible axes.
- [x] Molecular-weight summary remains explicitly unavailable without a
  reviewed calibration and distribution contract.
- [x] `sec` and `gpc` CLI aliases, Batch, direct/prevalidated ComputeRun,
  generic capability items, project adapters, and metric manifest share the
  same canonical/result objects.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_sec_processing.py tests/test_sec.py tests/test_canonical_one_dimensional.py
python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_capability_execution.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py
python scripts/verify.py --task docs/agent/tasks/2026-09-05-sec-gpc-foundation.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add sec gpc foundation" `
  --files docs/agent/tasks/2026-09-05-sec-gpc-foundation.md `
          polynexus/core/canonical_experiments/one_dimensional.py `
          polynexus/core/canonical_experiments/registry.py `
          polynexus/core/canonical_experiments/capabilities.py `
          polynexus/core/ai_platform/capabilities.py `
          polynexus/core/sec_processing.py polynexus/core/sec.py `
          polynexus/core/compute/service.py polynexus/core/__init__.py `
          polynexus/core/project_workflow/index.py `
          polynexus/core/project_workflow/adapters.py `
          polynexus/core/project_workflow/service.py `
          polynexus/cli/parser.py polynexus/cli/run_single_service.py `
          polynexus/cli/batch_run_service.py `
          tests/test_sec_processing.py tests/test_sec.py `
          tests/test_project_workflow_index.py `
          tests/test_project_workflow_adapters.py `
          tests/test_ai_native_project_entrypoint.py `
          README.md docs/OPEN_SOURCE.md `
          docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes:
  - `python -m pytest -p no:cacheprovider -q tests/test_sec_processing.py tests/test_sec.py tests/test_canonical_one_dimensional.py` - 34 passed.
  - `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_index.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py tests/test_compute_service.py tests/test_capability_execution.py` - 134 passed, 4 skipped.
  - `python -m compileall -q` over all changed Python modules - passed.
  - Focused `ruff check` over all changed SEC/canonical/project/CLI modules and tests - passed.
  - `git diff --check` - passed.
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-05-sec-gpc-foundation.md --changed --types` - task card and memory checks passed; repository baseline Ruff errors in pre-existing `polynexus/core/engine.py` remain when that file is included by the changed-file scan.
- Known limitations or follow-up: vendor binary readers, baseline/peak method
  families, calibration DTOs, concentration/detector response factors,
  molecular-weight distribution moments, uncertainty, independent replay, and
  capability promotion remain separate stages.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  manuscript plans/specs, `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/`.
