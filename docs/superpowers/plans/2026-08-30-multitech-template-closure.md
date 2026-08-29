# Multi-technique Template Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing canonical public layer with validated IR temperature-series and SAXS/WAXS detector-image templates, complete NMR shared entry coverage, then simplify only duplication proven by real replay.

**Architecture:** Keep `CanonicalExperiment`, `ComputeRun`, `ComputeResult.metric_manifest`, FigureDefinition, ProjectWorkflow, and EvidencePackage as the only public contracts. Additive typed source blocks represent condition-series spectra and detector images; provider algorithms remain technique-specific. Legacy 1D templates remain readable and unchanged.

**Tech Stack:** Python dataclasses/JSON, existing converter registry, provider engines, pytest, `scripts/verify.py`, real-input evaluation fixtures.

---

### Task 1: Audit and lock canonical extension boundaries

**Files:**
- Modify: `polynexus/core/canonical_experiments/models.py`
- Modify: `polynexus/core/canonical_experiments/registry.py`
- Test: `tests/test_canonical_experiment_templates.py`
- Test: `tests/test_canonical_converter_registry.py`

- [ ] Add RED coverage proving legacy v1 templates round-trip unchanged and unknown template IDs remain blocked.
- [ ] Define the additive serialization shape for condition-series and detector-image source blocks without embedding raw pixel arrays in JSON.
- [ ] Add strict validation for dimensions, axes, units, source locators, hash linkage, and finite metadata; preserve legacy deserialization.
- [ ] Register only the new template IDs required by the next tasks; do not alter existing 1D mappings.
- [ ] Run focused canonical tests and `git diff --check`.

### Task 2: Implement `ir.temperature_series.v1`

**Files:**
- Create: `polynexus/core/canonical_experiments/ir_temperature_series.py`
- Modify: `polynexus/core/canonical_experiments/registry.py`
- Modify: `polynexus/core/project_workflow/adapters.py`
- Modify: `polynexus/core/agent_workflow/tpae.py`
- Test: `tests/test_ir_temperature_series_canonical.py`
- Test: `tests/test_project_workflow_adapters.py`

- [ ] Add RED tests for ordered multi-file spectra, explicit metadata CSV overrides, ambiguous axes, missing frames, and source/hash mismatch.
- [ ] Convert one directory/list into one sequence template containing existing 1D frame measurements plus condition-axis metadata; never infer a scientific temperature from an untrusted filename.
- [ ] Route the sequence as one `ir.temperature_2d` provider step instead of independent static steps while preserving old static/TPAE recipes.
- [ ] Verify deterministic ordering, matrix shape metadata, and replay validation.
- [ ] Run IR temperature, canonical, adapter, and agent workflow focused tests.

### Task 3: Route IR 2D through ComputeRun and evidence consumers

**Files:**
- Modify: `polynexus/core/compute/service.py`
- Modify: `polynexus/core/compute/models.py`
- Modify: `polynexus/core/project_workflow/service.py`
- Modify: `polynexus/core/project_workflow/package.py`
- Modify: `polynexus/core/ir_engine/figure_provider.py`
- Test: `tests/test_ir_temperature_2d_compute_run.py`
- Test: `tests/test_analysis_evidence.py`
- Test: `tests/test_ir_complete_figure_provider.py`

- [ ] Add RED tests for one completed sequence ComputeRun containing matrix/COS metrics, frame provenance, figures, metric manifest, and warnings.
- [ ] Execute the existing `analyze_temperature_2d_series` provider once per sequence and project its result without recomputation in GUI/CLI/evidence paths.
- [ ] Preserve `diagnostic_only`/`review_required`, strict JSON, History/Export restore, and package-relative source links.
- [ ] Replay the registered real IR temperature case and record acceptance evidence.

### Task 4: Add SAXS/WAXS detector-image templates and routes

**Files:**
- Create: `polynexus/core/canonical_experiments/detector_image.py`
- Modify: `polynexus/core/canonical_experiments/models.py`
- Modify: `polynexus/core/canonical_experiments/registry.py`
- Modify: `polynexus/core/compute/service.py`
- Modify: `polynexus/core/project_workflow/adapters.py`
- Test: `tests/test_detector_image_templates.py`
- Test: `tests/test_saxs_2d_orchestrator_compute_run.py`
- Test: `tests/test_waxs_2d_orchestrator_compute_run.py`

- [ ] Add RED tests for EDF/TIFF/CBF source locators, shape/axis metadata, geometry/mask provenance, unsupported formats, and no-pixel-array JSON serialization.
- [ ] Register `saxs.detector_image.v1` and `waxs.detector_image.v1` as distinct template IDs sharing only the typed image-source structure.
- [ ] Preserve raw detector provenance and route existing SAXS/WAXS 2D providers through ComputeRun for static, temperature, and strain frames.
- [ ] Keep geometry, mask, orientation, and publication gates unchanged; missing evidence remains `not_assessed` or `review_required`.
- [ ] Run real EDF/image replay and figure/evidence/export round-trips.

### Task 5: Complete NMR shared entry and package replay

**Files:**
- Modify: `polynexus/core/canonical_experiments/registry.py`
- Modify: `polynexus/core/compute/service.py`
- Modify: `polynexus/core/project_workflow/adapters.py`
- Modify: `polynexus/core/project_workflow/package.py`
- Test: `tests/test_nmr_shared_compute_run.py`
- Test: `tests/eval/test_nmr_vendor_real_case_registry.py`

- [ ] Add RED tests for liquid/solid ¹H/¹³C, table and opaque vendor inputs, ppm provenance, and missing-material behavior.
- [ ] Reuse `nmr.spectrum.v1`; do not add material defaults or infer phase assignments.
- [ ] Verify peak/area/FWHM/SNR/region/relaxation projections and method sensitivity through ComputeRun and evidence package.
- [ ] Replay all available vendor cases and record assignment-limited solid-¹³C status.

### Task 6: Empirical simplification and cross-technique acceptance

**Files:**
- Modify: only files identified by Tasks 2–5 as duplicated adapters
- Create: `docs/acceptance/2026-08-30-multitech-template-closure.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [ ] Compare real replay payloads and extract only fields and validators shared by at least two techniques.
- [ ] Remove duplicate conversion/serialization branches without changing public IDs or legacy readers.
- [ ] Run mixed-technique project, GUI/CLI/Codex, evidence-package, Figure, and ARS handoff matrices.
- [ ] Run `python scripts/verify.py --task docs/agent/tasks/2026-08-30-multitech-template-closure.md --changed --types` and document every remaining scientific or human-review boundary.
- [ ] Create one final allowlisted checkpoint only after all required evidence is present.
