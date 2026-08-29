---
task_id: 2026-08-30-multitech-template-closure
kind: architecture
status: in_progress
date: 2026-08-30
title: Close IR 2D, SAXS/WAXS 2D, and NMR canonical template routes
---

# Multi-technique canonical template closure

## Goal

Use the existing canonical/ComputeRun/evidence public layer to add validated
conversion templates for IR temperature/time 2D-COS, SAXS/WAXS detector images,
and the four existing NMR 1D modes; then replay real inputs and simplify only
the duplication proven by those runs.

## Non-goals

- Do not create a second public analysis or provenance model.
- Do not implement spatial IR mapping or 2D NMR in this task.
- Do not relax scientific review, geometry, assignment, or publication gates.
- Do not infer missing temperatures, detector geometry, masks, assignments, or
  material composition from filenames.
- Do not edit raw datasets or generated evidence packages in place.

## Current baseline

- Existing public contracts: `CanonicalExperiment`, `Measurement`,
  `ConversionRecord/Outcome`, `CanonicalConverterRegistry`, `ComputeRun`,
  `ComputeResult.metric_manifest`, FigureDefinition, ProjectWorkflow, and
  EvidencePackage.
- Existing template coverage: generic 1D IR/SAXS/WAXS conversion and
  `nmr.spectrum.v1`; dedicated SAXS/WAXS detector-image templates are now
  registered while legacy 1D IDs remain unchanged.
- IR temperature-2D provider/evidence/figures already exist, but the generic
  project series route splits files into independent steps instead of one
  sequence computation.
- SAXS/WAXS providers already contain partial 2D image processing, but their
  canonical conversion and shared ComputeRun routes are incomplete.
- NMR provider and vendor cases exist; project/evidence replay now accepts an
  explicit `nmr.liquid_h`, `nmr.liquid_c`, `nmr.solid_h`, or `nmr.solid_c`
  submodule and carries it through single and mixed project recipes.

## Affected boundaries

- `polynexus/core/canonical_experiments`: additive template and locator
  contracts plus registry entries; preserve v1 compatibility.
- `polynexus/core/compute`: route sequence/image templates through the existing
  ComputeRun and capability/metric-manifest projection.
- `polynexus/core/project_workflow` and `core/agent_workflow`: preserve grouped
  sequence/image steps instead of silently treating them as static 1D inputs.
- Technique providers and figure/evidence packages: consume the same template
  and retain existing scientific roles and warnings.
- CLI/GUI/ARS: DTO consumers only; no technique-specific calculations.

## Milestones

1. Audit and document template gaps without changing algorithms.
2. Add `ir.temperature_series.v1` and prove one sequence ComputeRun.
3. Add SAXS/WAXS detector-image templates and prove static/series replay.
4. Complete NMR four-mode shared entry and package replay.
5. Extract only empirically shared fields, remove duplicate adapters, and run
   cross-technique evidence/figure/paper handoff acceptance.

## Progress (2026-08-30)

- [x] Added the first additive `ir.temperature_series.v1` converter. It reuses
      existing 1-D `Measurement` frames, records temperature/time/order metadata,
      and rejects unresolved temperature axes.
- [x] Registered IR temperature-series directory conversion without changing
      legacy static template mappings.
- [x] Routed IR temperature-series directories as one project/Agent/ComputeRun
      step and validated mixed-recipe delegation.
- [x] Added `saxs.detector_image.v1` and `waxs.detector_image.v1` conversion
      envelopes with source hash, shape, pixel axes, and explicit geometry
      provenance; raw pixels and default calibration are excluded.
- [x] Added explicit NMR four-mode project routing and mixed-technique package
      coverage using the existing `nmr.spectrum.v1` template.
- [x] Real IR/SAXS/WAXS image and NMR vendor replays reached ComputeRun,
      metric/evidence projections, package, and evidence-only export where
      applicable; provider-specific scientific gates remain unchanged.
- [x] Empirical payload comparison confirmed the existing canonical outer
      contract and adapters are the minimal safe shared layer. IR condition
      axes and detector geometry remain intentionally technique-specific.
- [ ] Final GUI/CLI/ARS product acceptance matrix remains a follow-up outside
      this code checkpoint.

## Acceptance boundary

Each milestone must provide focused RED/GREEN tests, strict JSON round-trip,
source/hash linkage, ComputeRun persistence, figure/evidence/export consumers,
real-input replay where available, and:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-30-multitech-template-closure.md --changed --types
```

The final milestone additionally requires cross-entry replay and explicit
documentation of any `diagnostic_only`, `review_required`, or human scientific
review limitations.

## Acceptance criteria

- [ ] Each requested technique has a registered, hash-linked canonical template
      and a replayable ComputeRun/evidence path.
- [ ] No raw detector pixels, guessed geometry, NMR assignments, or material
      defaults are introduced into public JSON.
- [ ] CLI/GUI/AI consumers read the existing run, figure, and evidence DTOs.

## Implementation plan

1. Audit existing canonical, ComputeRun, provider, and evidence boundaries.
2. Add dedicated IR temperature-series, detector-image, and explicit NMR routes.
3. Replay available real inputs and verify package/export consumers.
4. Extract only fields proven common by at least two replayed techniques.

## Verification

- Focused pytest suites for each converter and project adapter.
- `python scripts/verify.py --task docs/agent/tasks/2026-08-30-multitech-template-closure.md --changed --types`

## Known limitations

The current worktree contains pre-existing untracked `active_run.json`,
`runs/`, and `tests/_tmp_phase3/`; they remain outside all checkpoints.
