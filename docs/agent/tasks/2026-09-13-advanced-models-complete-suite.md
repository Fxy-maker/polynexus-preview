---
task_id: 2026-09-13-advanced-models-complete-suite
kind: scientific
status: active
date: 2026-09-13
title: Complete advanced polymer analysis model suite
---

# Complete advanced polymer analysis model suite

## Goal

Add explicit, sample-neutral advanced model routes for TGA multi-rate kinetics;
DMA temperature/frequency shifting and master curves; rheology thixotropy,
Cox–Merz, creep/relaxation, and TTS; and mechanics cyclic, fatigue, creep, and
fracture curves. Every result must remain available as a diagnostic candidate
through the shared CanonicalExperiment → ComputeRun → Metric Manifest →
Figure/Evidence chain.

## Non-goals

- No chemistry/material inference from sample names.
- No automatic calibration, curve selection, or publication/capability
  promotion.
- No replacement of existing fast analysis or generic exploratory routes.
- No formal metrology, standards certification, or human scientific sign-off
  in code.

## Affected boundaries

- TGA, DMA, rheology, and mechanics processing contracts and engines.
- Shared ComputeRun analysis-spec projection, metric manifest, figure/evidence
  consumers, and CLI/Agent entry points where options are exposed.
- Focused provider, canonical replay, and cross-entry tests.

## Implementation plan

1. Add explicit analysis-spec DTOs and deterministic TGA multi-rate kinetics;
   preserve individual curves and return local unavailable states.
2. Add explicit DMA temperature/frequency alignment, shift-factor fitting, and
   master-curve candidates with overlap diagnostics.
3. Add explicit rheology thixotropy loop metrics, Cox–Merz comparison,
   creep/relaxation model candidates, and TTS shifting.
4. Add explicit mechanics cycle segmentation, fatigue-life candidates,
   creep/relaxation fits, and fracture energy/propagation descriptors.
5. Wire each route through ComputeRun, metric manifest, CLI/Agent options,
   shared FigureDefinitions, and cross-entry replay tests.
6. Run module-focused verification after each atomic slice; retain all model
   outputs as diagnostic until independent replay and scientific review.

## Acceptance criteria

- [ ] Each requested family has a stable explicit analysis-spec contract.
- [ ] Missing or incompatible inputs yield local `unavailable` metrics while
  unrelated source curves still compute.
- [ ] Methods, parameters, units, source IDs, warnings, and model diagnostics
  are preserved in the shared result and manifest.
- [ ] Direct Core, CLI, Agent/Codex, and project routes share identical output
  projections for the same canonical template/spec.
- [ ] No new model is advertised as an available/promoted capability without
  independent replay, standards/negative controls, uncertainty evidence, and
  human scientific review.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_tga_advanced.py tests/test_dma_advanced.py tests/test_rheology_advanced.py tests/test_mechanics_advanced.py
python scripts/verify.py --task docs/agent/tasks/2026-09-13-advanced-models-complete-suite.md --changed --types
git diff --check
```

## Checkpoint allowlist

Each module is committed separately with its focused source/tests/task update;
the umbrella task is not considered complete until all four module checkpoints
pass and the cumulative diff is reviewed.

## Completion evidence

- Exact commands and outcomes: pending module implementation.
- Known limitations: all advanced models remain diagnostic candidates.
- Pre-existing changes left untouched: agent workflow service, superpowers
  plans/specs, literature text, and temporary phase-3 tests.
