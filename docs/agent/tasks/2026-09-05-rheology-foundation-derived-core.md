---
task_id: 2026-09-05-rheology-foundation-derived-core
kind: scientific
status: implementation_complete_review_required
date: 2026-09-05
title: Add sample-neutral rheology foundation and derived core
---

# Add Sample-Neutral Rheology Foundation and Derived Core

## Goal

Add a shared canonical and deterministic Core route for common rheometer table
exports. Preserve all unambiguous source signals, compute unit-safe steady-flow
and oscillatory identities, and expose source, method, parameter, unit, and
local-unavailable context through the existing ComputeRun and metric manifest.

## Non-goals

- Do not infer yield stress, constitutive model, linear viscoelastic region,
  gel point, plateau modulus, molecular architecture, or material identity.
- Do not apply Cox-Merz, time-temperature superposition, shift factors, master
  curves, thixotropy-area interpretation, creep/recovery fits, or relaxation
  models.
- Do not silently pair duplicate semantic signals or convert incompatible
  dimensions.
- Do not add rheology-private run, evidence, persistence, GUI, or export
  contracts, and do not promote the catalog's scientific capabilities.

## Shared objects and entry points

- Objects: `CanonicalExperiment`, `Measurement`, `AnalysisResult`, `ComputeRun`,
  capability items, and metric manifest.
- AI/Codex/CLI/Batch: consume the same `rheology_curve_1d.v1` template and
  deterministic engine output.
- GUI: unchanged; it may discover the registered engine and consumes public
  results rather than technique-private calculations.
- Cross-entry rule: direct and prevalidated-template routes call one shared
  `analyze_rheology_group` implementation and never overwrite source arrays.

## Affected boundaries

- Generic one-dimensional canonical conversion and converter registry.
- Generic finite curve capability family support.
- AI descriptor projection for generic curve work; formal rheology descriptors
  remain unsupported.
- New pure rheology processing and engine modules.
- ComputeRun, CLI single-run, batch choices, and engine discovery.
- Public Research Preview capability documentation and focused regressions.

## Implementation plan

1. Recognize material-neutral rheology axes and signals with explicit units.
2. Emit one canonical measurement per unambiguous signal column; duplicate
   semantic columns remain `needs_input`.
3. Derive apparent viscosity and shear stress only from dimensionally
   compatible stress/rate/viscosity inputs, with point masks for zero rates.
4. Derive oscillatory tan delta, complex-modulus magnitude, and complex-
   viscosity magnitude from compatible `G'`/`G''` plus explicit frequency.
5. Route the template through one registered Engine and shared ComputeRun,
   CLI, Batch, capability-item, and metric-manifest projections.

## Acceptance criteria

- [x] Steady shear-rate tables preserve stress and viscosity signals and emit
  source-preserving, unit-safe deterministic identities.
- [x] Oscillatory frequency tables preserve `G'` and `G''` and derive separate
  tan-delta, complex-modulus, and complex-viscosity series.
- [x] Pa/kPa/MPa and Pa*s/mPa*s/cP conversions are explicit; incompatible or
  unknown units stay locally unavailable.
- [x] Zero shear-rate/frequency points remain masked without failing valid
  points or mutating source arrays.
- [x] Duplicate semantic signals remain `needs_input`; unknown columns are not
  silently assigned.
- [x] Direct and prevalidated ComputeRuns, generic capability items, CLI, Batch,
  and metric manifest use the same canonical/result objects.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_rheology_processing.py tests/test_rheology.py tests/test_canonical_one_dimensional.py
python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_capability_execution.py tests/test_cli_run_single_service.py tests/test_cli_output.py
python scripts/verify.py --task docs/agent/tasks/2026-09-05-rheology-foundation-derived-core.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add rheology derived foundation" `
  --files docs/agent/tasks/2026-09-05-rheology-foundation-derived-core.md `
          polynexus/core/canonical_experiments/one_dimensional.py `
          polynexus/core/canonical_experiments/registry.py `
          polynexus/core/canonical_experiments/capabilities.py `
          polynexus/core/ai_platform/capabilities.py `
          polynexus/core/rheology_processing.py polynexus/core/rheology.py `
          polynexus/core/compute/service.py `
          polynexus/core/__init__.py polynexus/cli/parser.py `
          polynexus/cli/run_single_service.py polynexus/cli/batch_run_service.py `
          tests/test_rheology_processing.py tests/test_rheology.py `
          README.md docs/OPEN_SOURCE.md `
          docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes:
  - The initial focused test failed with the expected missing
    `polynexus.core.rheology_processing` module. Later unit-prefix, Greek-label,
    angular-frequency, batch-format, and generic-descriptor regressions failed
    at their intended boundaries before repair.
  - `python -m pytest -p no:cacheprovider -q tests/test_rheology_processing.py tests/test_rheology.py tests/test_canonical_one_dimensional.py`
    - 42 passed.
  - `python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_capability_execution.py tests/test_cli_run_single_service.py tests/test_cli_output.py tests/test_ai_capability_planner.py tests/test_canonical_nd_adapters.py`
    - 142 passed, 3 skipped.
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-05-rheology-foundation-derived-core.md --changed --types`
    - selected checks passed, including quality 313 and preprocessing 157.
  - `git diff --check` - passed through the structured verifier.
- Known limitations or follow-up: real instrument/material replay, measurement
  uncertainty, vendor binary readers, yield/thixotropy/LVE/crossover semantics,
  creep/relaxation models, TTS/master curves, group statistics, figures, and
  scientific capability promotion remain separate stages. Generic project-
  workflow indexing/adapters do not yet cover TGA, DMA, or rheology, so this
  task does not add a rheology-only project route.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  manuscript plans/specs, `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/`.
