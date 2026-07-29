---
task_id: 2026-07-29-saxs-strain-figure-v2-binding
kind: scientific
status: completed
date: 2026-07-29
title: Bind strain SAXS Figures to the existing V2 route
---

# Strain SAXS Figure V2 binding

## Goal

Make every Figure emitted by the existing SAXS strain provider explicitly
available to the already-approved `saxs_strain` V2 capability route, including
Manifest sidecars and the reactive Figure session/export consumers.

## Non-goals

- Do not change SAXS algorithms, numeric cleaning, quality levels, physical
  gates, evidence values, AI/rescue behavior, or publication roles.
- Do not infer detector data, interpolate, fabricate pixels/frames, or alter
  source provenance.
- Do not change V2 fallback policy, GUI drafts, real datasets, or test-storage
  retention/cleanup behavior.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_strain.py`: final recipe normalization for
  every emitted strain `FigureDefinition`.
- `tests/test_saxs_figure_evidence_binding.py`: provider-wide capability and
  representative Manifest-sidecar regressions.

## Acceptance criteria

- [x] Every currently emitted strain Figure declares `saxs_strain`.
- [x] Every emitted strain Figure resolves through the existing capability
  layer as `v2_runtime: ready` for supported inputs.
- [x] A representative strain FigurePipeline run writes a V2 sidecar while
  retaining existing evidence, role, and legacy-artifact behavior.
- [x] Unsupported V2 objects still fail closed through the existing adapter
  capability path.
- [x] Focused tests, structured verification, complete SAXS matrix, storage
  dry-run, hygiene checks, and an explicit allowlist checkpoint are recorded.

## Implementation plan

1. Add RED provider and Pipeline assertions that expose the missing strain V2
   adapter declaration and resulting `not_configured` capability.
2. Add the existing `saxs_strain` adapter as a non-overriding default at the
   provider's final recipe normalization boundary.
3. Run GREEN, adjacent Figure/provider consumers, structured verification, the
   complete SAXS matrix, non-destructive storage audit, and diff hygiene.
4. Record actual evidence and create one local explicit-allowlist checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k "strain_v2"
python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_saxs_detector_figure_modes.py tests/test_saxs_figure_document.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-strain-figure-v2-binding.md --changed --types
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName })
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
```

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-29-saxs-strain-figure-v2-binding.md`
- `docs/superpowers/specs/2026-07-29-saxs-strain-figure-v2-binding-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-strain-figure-v2-binding.md`
- `polynexus/core/saxs_engine/figure_strain.py`
- `tests/test_saxs_figure_evidence_binding.py`

## Pre-existing workspace changes

Keep `docs/agent/memory/current-state.md`, GUI/editor/release work,
`.superpowers/`, historical test-storage directories, the running GUI, and all
other untracked or parallel files outside this task checkpoint.

## Verification evidence

- TDD RED: `python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k
  "strain_v2"` returned `2 failed, 27 deselected`.  The provider assertion
  raised `KeyError: 'v2_adapter'`; the Pipeline assertion observed
  `v2_runtime == 'not_configured'`, exactly identifying the missing binding.
- TDD GREEN: the same command returned `2 passed, 27 deselected in 1.95s` and
  found the V2 sidecar written by `FigurePipeline`.
- Figure/provider consumer matrix: `56 passed, 4 warnings in 15.42s`.  The
  warnings are existing Arial CJK glyph notices from temperature documents.
- Structured verifier without the shared changed-file set passed: task/memory,
  Pyright `0 errors`, quality `287 passed`, preprocessing `106 passed`, and
  whitespace all returned exit code 0.  The prescribed `--changed --types`
  variant is accurately recorded as blocked by eight Ruff F401 findings in
  pre-existing parallel `polynexus/core/__init__.py` scientific-review work;
  none of those files is in this task's allowlist.
- Fresh complete SAXS matrix: `572 passed, 6 warnings in 376.46s`, exit code
  0.  Warnings are existing Arial glyph and missing detector-header geometry
  notices.
- Targeted `ruff check` and `compileall` for the strain provider/test passed;
  `git diff --check` passed.
- Storage `report --json` and `clean --older-than-hours 24` remained dry-runs:
  22 artifacts, `0` eligible bytes, and `0` removed.  No `--apply` was run.
- The checkpoint contains only the explicit five-file allowlist in this card;
  shared memory, scientific-review, GUI, release, storage, and scratch files
  remain outside it.
