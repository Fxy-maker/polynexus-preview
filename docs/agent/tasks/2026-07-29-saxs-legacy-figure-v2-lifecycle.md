---
task_id: 2026-07-29-saxs-legacy-figure-v2-lifecycle
kind: scientific
status: completed
date: 2026-07-29
title: Lock legacy SAXS Figure V2 lifecycle evidence
---

# Legacy SAXS Figure V2 lifecycle acceptance

## Goal

Record an executable regression proving that lightweight legacy SAXS Figure
providers for static, strain, and temperature modes retain their approved V2
adapter, resolve to a ready capability, and write a Manifest sidecar.

## Non-goals

- No production-code, analysis, quality, physical-gate, role, AI/rescue, GUI,
  or export behavior changes.
- No migration of legacy data, interpolation, frame fabrication, or source
  rewriting.
- No promotion of a legacy static asset or unsupported V2 definition; existing
  capability fallback behavior remains authoritative.

## Affected boundaries

- `tests/test_saxs_temperature_figure_provider.py`: legacy provider lifecycle
  acceptance regression.
- Existing `FigurePipeline` and `build_v2_definition_artifact` contracts are
  exercised as consumers, not modified.

## Acceptance criteria

- [x] Legacy static, strain, and temperature definitions declare the existing
  mode-specific V2 adapter.
- [x] Every definition in those representative legacy packs resolves to
  `v2_runtime: ready`.
- [x] One representative definition per mode produces a ready Manifest entry
  and a real V2 sidecar.
- [x] Existing roles, data sources, and legacy provider outputs remain intact.
- [x] Focused, structured, SAXS, storage dry-run, hygiene, and allowlist
  evidence are recorded.

## Implementation plan

1. Add one acceptance regression over the existing lightweight provider
   fixtures; record that this is an audit test if the current behavior is
   already green.
2. Run the focused legacy provider and FigurePipeline matrix, then the
   structured verifier and complete SAXS matrix.
3. Run storage report/clean without `--apply`, inspect the exact diff, update
   evidence, and create one explicit allowlist checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k legacy_v2
python -m pytest -q tests/test_saxs_temperature_figure_provider.py tests/test_saxs_publication_pack_upgrade.py tests/test_saxs_figure_evidence_binding.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-legacy-figure-v2-lifecycle.md --changed --types
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName })
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
```

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-29-saxs-legacy-figure-v2-lifecycle.md`
- `docs/superpowers/specs/2026-07-29-saxs-legacy-figure-v2-lifecycle-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-legacy-figure-v2-lifecycle.md`
- `tests/test_saxs_temperature_figure_provider.py`

## Pre-existing workspace changes

Keep `docs/agent/memory/current-state.md`, GUI/editor/release work,
`.superpowers/`, historical test-storage directories, the running GUI, and all
other untracked or parallel files outside this task checkpoint.

## Verification evidence

- Runtime audit before the regression covered legacy static `3` definitions,
  legacy strain `3`, legacy temperature `5`, modern static `2`, modern
  temperature `1`, and modern strain `3`; every definition had its expected
  adapter and `v2_runtime: ready`.
- This was an acceptance-only slice: no production RED was applicable because
  the existing runtime already satisfied the contract. The initial focused
  selector was corrected after `-k legacy_v2` returned `10 deselected`; the
  corrected test then returned `1 passed, 9 deselected in 3.47s`.
- Focused provider/publication/evidence matrix: `43 passed in 12.48s`.
- Structured verifier: exit code 0; task/memory, Ruff, compile, type baseline,
  quality `287 passed`, preprocessing `106 passed`, and whitespace all passed.
- Fresh complete SAXS matrix: `573 passed, 6 warnings in 383.68s`, exit code 0.
  Warnings are existing Arial glyph and missing EDF detector-header geometry
  notices.
- Targeted Ruff and compile checks passed; `git diff --check` passed.
- Storage report and clean were dry-runs: `28` artifacts, `0` eligible bytes,
  `0` removed. Five zero-byte legacy D-drive entries were eligible by rule;
  seven paths were protected by running-process references and the remainder
  by retention. No `--apply` was executed.
- The checkpoint contains exactly the four files in this card's allowlist; no
  production code, GUI, memory, real data, or scratch file is included.
