---
task_id: 2026-07-29-saxs-advanced-figure-v2-binding
kind: scientific
status: completed
date: 2026-07-29
title: Bind advanced static and temperature SAXS Figures to V2
---

# Advanced static/temperature SAXS Figure V2 binding

## Goal

Make every Figure emitted by the current static and temperature SAXS Figure
providers capability-gated and available to the existing V2 sidecar,
Workbench session, and publication export flow.

## Non-goals

- No changes to SAXS algorithms, cleaning, quality levels, physical gates,
  evidence values, AI/rescue behavior, or publication roles.
- No changes to the legacy `figure_provider.py` route or strain Figure
  provider.
- No default-route promotion beyond the existing reviewed adapter policy.
- No edits to real data, generated outputs, GUI drafts, or parallel memory
  changes.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_static.py`: existing static recipe helper.
- `polynexus/core/saxs_engine/figure_temperature.py`: existing advanced
  temperature recipes.
- `tests/test_saxs_figure_evidence_binding.py`: provider-wide V2 capability
  and sidecar regressions.

## Acceptance criteria

- [x] Every emitted static Figure declares `saxs_static` and resolves to
  `v2_runtime: ready`.
- [x] Every emitted temperature Figure declares `temperature_saxs` and
  resolves to `v2_runtime: ready`.
- [x] Pipeline-generated Manifest entries write V2 sidecars while retaining
  existing evidence, roles, and legacy assets.
- [x] Unsupported/invalid definitions still fail closed through the existing
  adapter capability path.
- [x] Focused, structured, complete SAXS, storage dry-run, hygiene, and
  explicit allowlist evidence are recorded.

## Implementation plan

1. Add RED assertions over the existing static and temperature provider
   fixtures for adapter declaration, V2 readiness, and sidecar capability.
2. Give the static recipe helper its existing `saxs_static` adapter default
   and add `temperature_saxs` to each advanced temperature recipe.
3. Run focused provider/capability regressions and the related FigurePipeline
   matrix.
4. Run the task verifier, complete SAXS matrix, storage dry-run, diff audit,
   and create the explicit allowlist checkpoint.

## Verification

    python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k "advanced_v2"
    python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_saxs_temperature_figure_panels.py tests/test_saxs_static_publication_gate.py
    python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-advanced-figure-v2-binding.md --changed --types
    python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName })
    python scripts/test_storage.py report --json
    python scripts/test_storage.py clean --older-than-hours 24
    git diff --check

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-29-saxs-advanced-figure-v2-binding.md`
- `docs/superpowers/specs/2026-07-29-saxs-advanced-figure-v2-binding-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-advanced-figure-v2-binding.md`
- `polynexus/core/saxs_engine/figure_static.py`
- `polynexus/core/saxs_engine/figure_temperature.py`
- `tests/test_saxs_figure_evidence_binding.py`

## Pre-existing workspace changes

Keep `docs/agent/memory/active-work.md`,
`docs/agent/memory/current-state.md`, release-packet files, `.superpowers/`,
the running GUI, historical pytest/storage directories, and all other
untracked or parallel files outside this task checkpoint.

## Verification evidence

- TDD RED: `python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k
  advanced_v2` returned `2 failed, 24 deselected`; both expected failures were
  missing `v2_adapter` keys.  An initial selector typo returned only
  deselections and was corrected before this RED run.
- TDD GREEN plus Manifest sidecar regression: `3 passed, 24 deselected`.
- Provider/Figure/publication matrix: `39 passed in 5.03s`; the V2 fallback
  and affected matrix then returned `48 passed in 5.60s`.
- Structured verifier passed task/memory checks, Ruff, compile, quality
  `287 passed`, preprocessing `106 passed`, and whitespace.
- Fresh complete SAXS matrix: `570 passed, 6 warnings in 358.19s`, exit code
  0.  Warnings are existing Arial glyph and missing detector-header geometry
  notices.
- Storage report and clean were dry-runs: 20 artifacts and 0 eligible bytes;
  no item was removed and no `--apply` was run.  Existing external artifacts
  were protected by active-process or retention rules.
- `git diff --check` exited 0.  The checkpoint is limited to this card, its
  spec/plan, the two providers, and the focused test file; shared memory and
  release documents remain excluded.
