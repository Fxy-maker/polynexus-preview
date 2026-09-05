---
task_id: 2026-09-05-mechanics-advanced-models
kind: scientific
status: implementation_complete_review_required
date: 2026-09-05
title: Add contract-bound mechanics modulus, yield, and toughness models
---

# Add Contract-Bound Mechanics Advanced Models

## Goal

Extend the shared mechanics processing route with deterministic, explicitly
configured tensile/compression/flexural modulus, offset-yield candidate, and
stress-strain toughness calculations while preserving local unavailable states
when test semantics are incomplete.

## Non-goals

- Do not infer specimen geometry, test mode, strain convention, endpoint, or
  fitting window from material names, filenames, or curve shape.
- Do not implement fatigue, fracture, creep, relaxation, TTS, or capability
  promotion in this task.
- Do not reinterpret a vendor-provided modulus as a Core-fitted modulus.
- Do not create mechanics-private project, run, evidence, GUI, or persistence
  objects.

## Shared objects and entry points

- Objects: `CanonicalExperiment` payload, `Measurement`, `AnalysisResult`,
  `ComputeRun` metric manifest, and evidence-facing result projection.
- Core/ComputeRun/CLI/Batch/Codex: continue to use the shared canonical
  mechanics template and result object. A canonical payload may carry the
  user/AI-proposed `mechanics_analysis` DTO; absent semantics remain local
  `unavailable`.
- GUI: unchanged; it consumes the public summary and metric manifest.
- Cross-entry rule: no route may calculate these properties outside
  `analyze_mechanics_group` and the existing `MechanicsEngine` projection.

## Affected boundaries

- Mechanics processing and its metric-manifest projection.
- Canonical one-dimensional strain-unit recognition and canonical payload
  reuse.
- Shared `MechanicsEngine` and `ComputeRun` prevalidated-template execution.
- Focused mechanics/Core regression tests and Research Preview documentation.

## Implementation plan

1. Add failing processor and ComputeRun regressions for explicit mechanics
   semantics and local unavailable behavior.
2. Implement the immutable semantics DTO, unit normalization, modulus, yield,
   and endpoint-controlled toughness calculations in the mechanics processor.
3. Pass the canonical payload spec through `MechanicsEngine` while preserving
   the existing shared result and metric-manifest contracts.
4. Verify the mechanics, canonical, ComputeRun, capability, project, and AI
   consumers, then record the diagnostic/review boundary.

## Input contract

`MechanicsAnalysisSpec` is immutable and serializable. It binds:

- test mode (`tensile`, `compression`, or `flexural`);
- explicit stress and strain measurement IDs, or an explicit strain axis;
- specimen geometry metadata (at minimum one positive geometry field);
- stress/strain unit declarations and a positive modulus fitting window;
- optional offset-yield method and offset;
- optional toughness endpoint rule (`last_valid` only in this slice).

The processor accepts a mapping only through this DTO parser and records the
serialized spec in method parameters. It never guesses missing semantic fields.

## Acceptance criteria

- [x] Without a valid spec, existing descriptive metrics still compute and each
  advanced property is locally `unavailable` with an actionable reason.
- [x] Valid explicit stress-strain data produce a unit-normalized modulus with
  fit window, source measurement IDs, method, and provenance in the metric
  manifest.
- [x] A valid offset-yield request produces a candidate only when the offset
  line has a deterministic crossing; otherwise only yield is unavailable.
- [x] A valid `last_valid` endpoint produces stress-strain toughness in Pa; no
  endpoint is inferred when the rule is absent.
- [x] Vendor modulus remains source-preserved and is not used as a fitted
  modulus input.
- [x] Canonical/ComputeRun routes retain the same result projection and source
  arrays remain unchanged.
- [x] Fatigue, fracture, creep, uncertainty, independent replay, and formal
  capability promotion remain explicitly out of scope and review-required.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_mechanics_processing.py tests/test_mechanics.py
python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_capability_execution.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py
python scripts/verify.py --task docs/agent/tasks/2026-09-05-mechanics-advanced-models.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(mechanics): add contract-bound advanced models" `
  --files docs/agent/tasks/2026-09-05-mechanics-advanced-models.md `
          polynexus/core/canonical_experiments/one_dimensional.py `
          polynexus/core/mechanics_processing.py polynexus/core/mechanics.py `
          tests/test_mechanics_processing.py tests/test_mechanics.py `
          README.md docs/OPEN_SOURCE.md docs/agent/memory/active-work.md `
          docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes:
  - `python -m pytest -p no:cacheprovider -q tests/test_mechanics_processing.py tests/test_mechanics.py`: 12 passed.
  - `python -m pytest -p no:cacheprovider -q tests/test_canonical_one_dimensional.py tests/test_compute_service.py tests/test_capability_execution.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py`: 143 passed, 3 skipped.
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-05-mechanics-advanced-models.md --changed --types`: selected checks passed; quality gate 313 and preprocessing 157 passed.
  - `python -m ruff check` on changed mechanics/canonical/test files, `compileall`, and `git diff --check`: passed.
- Known limitations or follow-up: capability descriptors remain unsupported;
  fatigue, fracture, creep, uncertainty, independent replay, standard-sample
  validation, and scientific capability promotion remain review-required.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  manuscript plans/specs, `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/`.
