---
task_id: 2026-09-04-tga-module-foundation
kind: architecture
status: implementation_complete_review_required
date: 2026-09-04
title: Add sample-neutral TGA module foundation
---

## Goal

Add a first shared-Core TGA route that accepts common table exports from many
sample types, preserves source and axis semantics, and emits deterministic
generic curve results. TGA must not hard-code a polymer family or claim
validated mass-loss stages, DTG, or kinetics yet.

## Non-goals

- Do not infer polymer identity or interpret decomposition chemistry.
- Do not add publication-grade DTG, stage segmentation, or kinetic models.
- Do not create a TGA-private provenance/result contract.
- Do not modify raw data or existing technique algorithms.

## Shared objects and entry points

- Objects: CanonicalExperiment/Measurement, ComputeRun, metric manifest, and
  generic curve capability items.
- AI/Codex/CLI: use the shared ComputeRun and canonical converter; no private
  TGA result/provenance representation.
- GUI: unchanged; consumes the shared result shape and generic curve fallback.
- Cross-entry rule: single CLI, batch, ComputeRun, and future AI callers use
  the same canonical converter and `TGAEngine` registry entry.

## Affected boundaries

- Canonical table conversion and generic capability family registry.
- ComputeRunService canonical routing and BaseEngine technique registry.
- CLI single-file and batch technique choices; AI-tune remains limited to its
  existing provider-specific orchestrator until a TGA exploration adapter is
  designed.
- No raw data, project manifests, or existing provider algorithms are changed.

## Implementation plan

1. Extend the generic one-dimensional converter with sample-neutral TGA axis
   and mass/weight aliases and a `thermal_1d` measurement family.
2. Add a descriptive TGA BaseEngine and register it in Core and CLI/batch
   entry points.
3. Add focused conversion, engine, ComputeRun, and parser regression tests.
4. Run task-scoped tests and the structured verifier; record known scientific
   limitations and preserve pre-existing worktree changes.

## Acceptance criteria

- [x] CSV/TSV/TXT-style temperature/time versus mass/weight tables convert to a
  `thermal_1d` measurement and `thermal_curve_1d.v1` template.
- [x] Sample names and optional material metadata do not affect conversion.
- [x] Unknown units are retained with warnings and do not block calculation.
- [x] `get_engine("tga")`, direct ComputeRun, CLI parser, and batch format
  discovery recognize TGA.
- [x] A deterministic TGA engine emits point count, axis ranges, mass range, and
  a source-preserving curve without claiming stage/DTG/kinetics capabilities.

## Context and output budget

- Read first: canonical converter/models, ComputeRun routing, BaseEngine, CLI
  parser, memory current state, and the generic capability registry.
- Search scope: affected symbols and focused tests only.
- Expand only for architecture or verification failures.
- Report exact commands, changed files, limitations, and untouched changes.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_tga.py tests/test_canonical_one_dimensional.py tests/test_compute_service.py tests/test_cli_run_single_service.py tests/test_cli_output.py
python scripts/verify.py --task docs/agent/tasks/2026-09-04-tga-module-foundation.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add sample-neutral tga module foundation" `
  --files docs/agent/tasks/2026-09-04-tga-module-foundation.md `
          polynexus/core/canonical_experiments/one_dimensional.py `
          polynexus/core/canonical_experiments/registry.py `
          polynexus/core/canonical_experiments/capabilities.py `
          polynexus/core/ai_platform/capabilities.py `
          polynexus/core/compute/service.py `
          polynexus/core/engine.py `
          polynexus/core/tga.py `
          polynexus/core/__init__.py `
          polynexus/cli/parser.py `
          polynexus/cli/run_single_service.py `
          tests/test_tga.py README.md docs/OPEN_SOURCE.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes:
  - `python -m pytest -p no:cacheprovider -q tests/test_tga.py tests/test_canonical_one_dimensional.py tests/test_compute_service.py tests/test_cli_run_single_service.py tests/test_cli_output.py` — 91 passed, 3 skipped.
  - `python -m pytest -p no:cacheprovider -q tests/test_core.py tests/test_tga.py` — 13 passed.
  - Targeted Ruff on changed implementation/test files — passed.
  - `git diff --check` — passed.
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-04-tga-module-foundation.md --changed --types` — task card and memory checks passed, but the repository verifier stopped at pre-existing Ruff findings in `polynexus/core/engine.py` (E701/F541/E402/F401); no new TGA lint errors were reported by targeted Ruff.
- Known limitations or follow-up:
  - This is a sample-neutral descriptive curve foundation, not publication-
    validated TGA science. DTG, stage segmentation, residue interpretation,
    kinetics, vendor-specific binary readers, and a reviewed shared figure
    provider remain follow-up modules.
  - Architecture and scientific-semantics review remain required before
    capability promotion or paper-use claims.
- Pre-existing changes left untouched:
  - `polynexus/core/agent_workflow/service.py`, manuscript plans/specs,
    `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/` remain outside this
    checkpoint.
