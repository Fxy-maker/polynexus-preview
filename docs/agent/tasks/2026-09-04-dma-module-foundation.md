---
task_id: 2026-09-04-dma-module-foundation
kind: architecture
status: implementation_complete_review_required
date: 2026-09-04
title: Add sample-neutral DMA curve foundation
---

## Goal

Expose a shared, sample-neutral DMA/DMTA table route for common frequency,
temperature, or time curves and one explicitly selected viscoelastic signal.

## Non-goals

- Do not infer glass transitions, master curves, shift factors, or polymer
  identity.
- Do not silently choose among multiple modulus/tan-delta columns; ambiguous
  tables remain `needs_input` until a mapping selects one signal.
- Do not add a DMA-private result or provenance contract.

## Shared objects and entry points

- Objects: CanonicalExperiment/Measurement, ComputeRun, metric manifest, and
  generic curve capability items.
- AI/Codex/CLI: use the shared canonical converter and ComputeRun; no private
  DMA result representation.
- GUI: unchanged and consumes generic result projections.
- Cross-entry rule: single CLI, batch, ComputeRun, and future AI callers share
  the same `viscoelastic_1d` template and engine lifecycle.

## Affected boundaries

- Generic one-dimensional axis/signal mapping and capability families.
- ComputeRun and BaseEngine registration; CLI single and batch choices.
- No raw data or existing technique algorithms are changed.

## Implementation plan

1. Add DMA/DMTA axis and viscoelastic signal aliases to the generic converter.
2. Add a descriptive DMA engine that reports curve ranges and source metadata.
3. Register shared Core/CLI/batch routes and add focused regression tests.
4. Run task-scoped verification and record the ambiguity and scientific review
   boundaries.

## Acceptance criteria

- [x] Frequency/temperature/time versus modulus, tan-delta, stress, or strain
  tables convert to `viscoelastic_1d` and `dma_curve_1d.v1`.
- [x] A table with multiple candidate signals does not silently select one.
- [x] `get_engine("dma")`, direct ComputeRun, CLI parser, and batch discovery
  recognize the route.
- [x] Generic curve summaries are emitted without master-curve/Tg claims.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_dma.py tests/test_tga.py tests/test_canonical_one_dimensional.py tests/test_compute_service.py tests/test_cli_run_single_service.py tests/test_cli_output.py
python scripts/verify.py --task docs/agent/tasks/2026-09-04-dma-module-foundation.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add sample-neutral dma module foundation" `
  --files docs/agent/tasks/2026-09-04-dma-module-foundation.md `
          polynexus/core/canonical_experiments/one_dimensional.py `
          polynexus/core/canonical_experiments/registry.py `
          polynexus/core/canonical_experiments/capabilities.py `
          polynexus/core/compute/service.py `
          polynexus/core/engine.py `
          polynexus/core/dma.py `
          polynexus/core/__init__.py `
          polynexus/cli/parser.py `
          polynexus/cli/run_single_service.py `
          tests/test_dma.py README.md docs/OPEN_SOURCE.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes:
  - `python -m pytest -p no:cacheprovider -q tests/test_dma.py tests/test_tga.py tests/test_canonical_one_dimensional.py tests/test_compute_service.py tests/test_cli_run_single_service.py tests/test_cli_output.py tests/test_core.py` — 108 passed, 3 skipped.
  - Targeted Ruff on the changed DMA/canonical/CLI files — passed.
  - `git diff --check` — passed.
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-04-dma-module-foundation.md --changed --types` — task card and memory checks passed, but the repository verifier stopped at the same pre-existing Ruff findings in `polynexus/core/engine.py` (E701/F541/E402/F401).
- Known limitations or follow-up:
  - This is a sample-neutral descriptive curve foundation, not publication-
    validated DMA/DMTA science. Master curves, time-temperature superposition,
    shift factors, Tg interpretation, multi-signal transforms, and vendor
    binary readers remain follow-up modules.
  - Architecture and scientific-semantics review remain required before
    capability promotion or paper-use claims.
- Pre-existing changes left untouched:
  - `polynexus/core/agent_workflow/service.py`, manuscript plans/specs,
    `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/` remain outside this
    checkpoint.
