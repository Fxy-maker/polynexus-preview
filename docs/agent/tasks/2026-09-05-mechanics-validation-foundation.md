---
task_id: 2026-09-05-mechanics-validation-foundation
kind: scientific
status: implementation_complete_review_required
date: 2026-09-05
title: Add mechanics replay and diagnostic uncertainty foundation
---

# Add Mechanics Replay and Diagnostic Uncertainty Foundation

## Goal

Make contract-bound mechanics outputs independently replayable and expose an
explicit, first-order diagnostic uncertainty projection without promoting any
mechanics capability.

## Non-goals

- Do not invent instrument uncertainty, standard-sample values, or material
  repeatability from a curve alone.
- Do not claim metrological uncertainty, publication validation, or capability
  promotion from the first-order estimate.
- Do not implement fatigue, fracture, creep, relaxation, or new UI/account
  workflows.
- Do not add a second run, evidence, or persistence representation.

## Shared objects and entry points

- Objects: `MechanicsAnalysisSpec`, `AnalysisResult`/`ComputeResult` uncertainty
  projection, canonical payload, and a validation-only replay report.
- Core/ComputeRun/CLI/Batch/Codex: explicit `stress_std`/`strain_std` values
  flow through the existing mechanics processor and shared `uncertainty`
  projection. Replay reports consume serialized canonical-style input and do
  not replace ComputeRun.
- GUI: unchanged; it reads the existing result/manifest DTOs.
- Cross-entry rule: no entry point calculates uncertainty or replay values
  outside the shared mechanics validation helpers.

## Affected boundaries

- Mechanics processing/spec validation and the shared `MechanicsEngine` result
  metadata projection.
- New validation-only replay DTOs and deterministic case runner.
- Mechanics focused tests, documentation, and durable agent memory.

## Implementation plan

1. Add failing tests for uncertainty propagation, canonical result projection,
   and replay round-trip/mismatch behavior.
2. Extend `MechanicsAnalysisSpec` with optional explicit stress/strain standard
   deviations and calculate first-order diagnostic intervals for computed
   modulus, offset yield, and toughness.
3. Add immutable serialized replay case/report contracts that compare computed
   scalar outputs against independently supplied expected values and retain a
   replay hash.
4. Route uncertainty through `MechanicsEngine` and `ComputeRun`; verify the
   existing mechanics and shared consumer matrix without changing capability
   statuses.

## Acceptance criteria

- [x] No uncertainty inputs means existing outputs and empty shared uncertainty
  remain unchanged.
- [x] Explicit finite stress/strain standard deviations produce uncertainty
  records with units, method, source metric, and diagnostic status; invalid
  inputs remain locally unavailable.
- [x] A serialized replay case can be round-tripped and produces a deterministic
  pass/fail report with expected-value mismatches and a stable hash.
- [x] Replay failure or uncertainty availability never blocks descriptive or
  independently computable mechanics metrics.
- [x] Formal capability descriptors remain unsupported and all standard-sample,
  metrology, independent instrument, and human scientific review gates remain
  open.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_mechanics_processing.py tests/test_mechanics.py tests/test_mechanics_validation.py
python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_capability_execution.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py
python scripts/verify.py --task docs/agent/tasks/2026-09-05-mechanics-validation-foundation.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(mechanics): add replay and uncertainty foundation" `
  --files docs/agent/tasks/2026-09-05-mechanics-validation-foundation.md `
          polynexus/core/mechanics_processing.py polynexus/core/mechanics.py `
          polynexus/core/mechanics_validation.py `
          tests/test_mechanics_processing.py tests/test_mechanics.py `
          tests/test_mechanics_validation.py README.md docs/OPEN_SOURCE.md `
          docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes:
  - `python -m pytest -p no:cacheprovider -q tests/test_mechanics_processing.py tests/test_mechanics.py tests/test_mechanics_validation.py`: 15 passed.
  - `python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_capability_execution.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py`: 118 passed, 3 skipped.
  - `python -m ruff check` on changed mechanics/validation/test files,
    `compileall`, and `git diff --check`: passed.
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-05-mechanics-validation-foundation.md --changed --types`: selected checks passed; quality gate 313 and preprocessing 157 passed.
- Known limitations or follow-up: uncertainty is first-order diagnostic only;
  replay references are externally supplied fixtures, not standard-sample or
  inter-laboratory evidence. Formal capability promotion remains blocked on
  independent replay, standards, negative controls, uncertainty review, and
  human scientific approval.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  manuscript plans/specs, `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/`.
