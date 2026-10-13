---
task_id: 2026-09-05-dma-multisignal-derived-core
kind: scientific
status: implementation_complete_review_required
date: 2026-09-05
title: Add sample-neutral DMA multi-signal derived core
---

# Add Sample-Neutral DMA Multi-Signal Derived Core

## Goal

Preserve every unambiguously labelled DMA signal in a shared canonical
experiment, derive dimensionless loss tangent from compatible storage/loss
modulus pairs, and emit material-neutral temperature-response peak candidates
with complete method, parameter, unit, and local-unavailable context.

## Non-goals

- Do not label any peak as glass-transition temperature or infer polymer
  identity, phase, relaxation mechanism, or publication meaning.
- Do not implement time-temperature superposition, shift factors, master
  curves, frequency-temperature surface fitting, or group statistics here.
- Do not silently pair incompatible tensile/shear modulus bases or
  non-convertible units.
- Do not add DMA-private run, evidence, persistence, GUI, or CLI result models.
- Do not promote the existing experimental/unsupported capability descriptors.

## Shared objects and entry points

- Objects: `CanonicalExperiment`, `Measurement`, `AnalysisResult`, `ComputeRun`,
  and metric manifest.
- AI/Codex/CLI: all consume the same multi-measurement canonical experiment and
  shared ComputeRun projection.
- GUI: unchanged; it consumes the public result rather than technique-specific
  event-handler calculations.
- Cross-entry rule: direct and prevalidated-template runs use one
  `analyze_dma_group` implementation; source channels are never overwritten.

## Affected boundaries

- DMA-specific branches of generic one-dimensional canonical conversion.
- New pure DMA processing configuration/outcome functions.
- DMA engine result construction and shared metric-manifest metadata.
- Focused canonical, engine, and ComputeRun regressions.

## Implementation plan

1. Classify explicit DMA signal headers by signal kind and modulus basis.
2. Emit one canonical measurement per unambiguous signal column sharing an
   axis, while keeping duplicate semantic signals as mapping ambiguity.
3. Add pure group processing for compatible storage/loss modulus pairs,
   traceable unit conversion, partial zero-denominator masks, and temperature
   response-peak candidates.
4. Preserve source and derived series separately and expose all metadata
   through the existing AnalysisResult/ComputeRun metric manifest.
5. Add focused regressions for explicit multi-signal tables, incompatible
   bases/units, partial unavailable points, non-temperature axes, canonical
   replay, and legacy single-signal behavior.

## Acceptance criteria

- [x] Explicit `E'`, `E''`, and `tan delta` columns all survive canonical
  conversion with stable signal kind and modulus-basis metadata.
- [x] Duplicate semantic signal columns remain `needs_input`; unknown columns
  are not silently assigned.
- [x] Compatible storage/loss pairs yield a separate dimensionless tan-delta
  series with conversion parameters and a validity mask; source arrays remain
  unchanged.
- [x] Zero denominators affect only those derived points, while incompatible
  bases/units make only the requested relationship unavailable.
- [x] Temperature-response peaks are retained as candidates and explicitly not
  identified as Tg; frequency/time curves remain calculable without thermal
  labels.
- [x] ComputeRun and metric manifest expose the same values, units, methods,
  parameters, and local statuses used by all entry points.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_dma_processing.py tests/test_dma.py tests/test_canonical_one_dimensional.py
python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_capability_execution.py
python scripts/verify.py --task docs/agent/tasks/2026-09-05-dma-multisignal-derived-core.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add dma multisignal derived core" `
  --files docs/agent/tasks/2026-09-05-dma-multisignal-derived-core.md `
          polynexus/core/canonical_experiments/one_dimensional.py `
          polynexus/core/dma_processing.py polynexus/core/dma.py `
          tests/test_dma_processing.py tests/test_dma.py `
          README.md docs/OPEN_SOURCE.md `
          docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes:
  - Initial focused red test failed with the expected missing
    `polynexus.core.dma_processing` module; later Unicode-label and proposal
    contract red tests failed at their intended boundaries before repair.
  - `python -m pytest -p no:cacheprovider -q tests/test_dma_processing.py tests/test_dma.py tests/test_canonical_one_dimensional.py`
    — 38 passed.
  - `python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_capability_execution.py`
    — 70 passed, 3 skipped.
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-05-dma-multisignal-derived-core.md --changed --types`
    — selected checks passed, including quality 313 and preprocessing 157.
  - `git diff --check` — passed.
- Known limitations or follow-up: project-level grouping/statistics, method
  sensitivity, real-data replay, uncertainty, TTS/master curves, and scientific
  promotion remain separate stages. Architecture and scientific-semantics
  review are required before merge or capability promotion.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  manuscript plans/specs, `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/`.
