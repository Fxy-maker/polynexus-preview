---
task_id: 2026-08-04-saxs-iq2-fourier-figures
kind: scientific
status: completed
date: 2026-08-04
title: Add SAXS Iq2 and Fourier correlation figures
---

## Goal

Expose complete `I(q)q^2` curves for ordinary, temperature, and strain SAXS
alongside the existing normalized Fourier correlation `gamma(r)` figures.

## Non-goals

- Do not change `kratky_analysis`, Fourier integration, normalization, or core
  physical calculations.
- Do not rename the existing `gamma(r)` contract to `K(z)` in persisted data.
- Do not change Porod-invariant, negative-intensity, or publication eligibility
  semantics.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_common.py`
- `polynexus/core/saxs_engine/figure_static.py`
- `polynexus/core/saxs_engine/figure_temperature.py`
- `polynexus/core/saxs_engine/figure_strain.py`
- `polynexus/core/saxs_engine/saxs_output_documents.py`
- focused SAXS figure tests

## Implementation plan

1. Reuse the emitted `analysis.kratky` payload through a shared projection
   helper that filters invalid pairs and records projection quality.
2. Add selected-frame and all-frame `I(q)q^2` definitions to the modern
   temperature provider and an all-frame definition to the strain provider.
3. Preserve the static provider's existing complete curve and extend legacy
   lightweight fallbacks with an explicitly labelled display projection.
4. Verify editable figure contracts, Fourier distance-axis semantics, and
   fail-closed invalid-curve behavior with focused regression tests.

## Acceptance criteria

- [x] Ordinary/static SAXS exposes an editable complete `I(q)q^2` trace.
- [x] Temperature SAXS exposes selected-frame and all-frame `I(q)q^2` traces.
- [x] Strain SAXS exposes an all-frame `I(q)q^2` trace while retaining scalar
  method evidence.
- [x] Fourier correlation remains `gamma(r)` with x-axis `r/z (nm)`.
- [x] Invalid curves fail closed with projection-quality evidence.
- [x] Focused tests and the task-scoped verifier pass.

## Evidence

- `python -m pytest -q tests/test_saxs_iq2_fourier_figures.py`: 6 passed.
- `python -m pytest -q tests/test_saxs_temperature_figure_provider.py tests/test_cross_technique_figure_pipeline.py`: 18 passed.
- `python -m pytest -q tests/test_saxs_figure_document.py tests/test_saxs_figure_evidence_binding.py`: 59 passed, 4 font warnings.
- `python -m compileall -q polynexus/core/saxs_engine/figure_common.py polynexus/core/saxs_engine/figure_temperature.py polynexus/core/saxs_engine/figure_strain.py polynexus/core/saxs_engine/figure_provider.py`: passed.
- `git diff --check`: passed.

## Verification

```powershell
python -m pytest -q tests/test_saxs_iq2_fourier_figures.py tests/test_saxs_figure_document.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_figure_evidence_binding.py
python scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-iq2-fourier-figures.md --changed --types
python -X utf8 scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-iq2-fourier-figures.md --changed --types
git diff --check
```

## Pre-existing state

The worktree contains unrelated staged, unstaged, deleted, and untracked user
changes. They must remain untouched and must not enter the checkpoint.
