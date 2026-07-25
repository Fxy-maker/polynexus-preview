# PolyNexus full software development Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 PolyNexus 全技术、全结果工作台、全图包生命周期和发布验收闭环。

**Architecture:** 先稳定共享 contracts 和 Workbench shell/profile，再以技术模式为单位执行完整 vertical slice。分析层提供结果和 evidence，GUI 只消费 presentation，图包生命周期由共享 Figure/Manifest/Gallery/Editor/Export 基础设施承载。

**Tech Stack:** Python、PySide6、pytest、Ruff、Pyright/type baseline、FigureDocument v2、RunFigureManifest、CSV/TSV/XLSX/报告/Origin export、AI preprocessing gates。

---

### Phase 0: Baseline and contract inventory

**Files:**
- Read: `AGENTS.md`, `README.md`, `docs/agent/memory/README.md`, `docs/agent/memory/current-state.md`, `docs/agent/memory/active-work.md`
- Inspect: `polynexus/core/analysis_evidence*.py`
- Inspect: `polynexus/core/figures/`
- Inspect: `polynexus/gui/results_table_service.py`, `polynexus/gui/result_table_templates.py`, `polynexus/gui/widgets/results_table_panel.py`
- Create: `docs/acceptance/2026-07-25-full-software-baseline.md`

- [ ] Inventory every technique/mode, current provider, result template, workbench consumer, figure lifecycle, export path, focused tests and real/Golden fixture.
- [ ] Record stale/active/merged status from memory without treating historical entries as current truth.
- [ ] Run `python scripts/verify.py --changed --types` with external basetemp if required and record the baseline.
- [ ] Define per-phase changed-file allowlists before implementation.

### Phase 1: Shared contracts and Results Workbench platform

**Files:**
- Inspect/modify: `polynexus/gui/results_table_service.py`
- Inspect/modify: `polynexus/gui/result_table_templates.py`
- Inspect/modify: `polynexus/gui/widgets/results_table_panel.py`
- Inspect/modify: `polynexus/gui/main_window_output_mixin.py`
- Test: `tests/test_results_table_service.py`, `tests/test_result_table_templates.py`, `tests/test_main_window_output_mixin.py`
- Create: `tests/test_results_workbench_profiles.py`

- [x] Define a typed Workbench Profile contract for title, heroes, primary/detail/diagnostics, review action, figure links and empty/error states.
- [x] Implement the shared shell without embedding technique-specific calculations.
- [x] Add profiles for SAXS static/temperature/strain first, then generic profile registration for DSC/WAXS/IR/NMR/Joint.
- [x] Make tab labels, empty states, evidence status and action routing profile-driven.
- [x] Add Qt-independent presentation tests plus focused offscreen Qt tests.
- [x] Verify mode switching, retranslation, no-result, low-confidence and diagnostic-only states.
- [ ] Checkpoint only after focused tests, Ruff, compile, `git diff --check`, and `python scripts/verify.py --changed --types` pass.

### Phase 2: SAXS complete vertical slice

**Files:**
- Inspect/modify: `polynexus/core/saxs_engine/figure_static.py`
- Inspect/modify: `polynexus/core/saxs_engine/figure_temperature.py`
- Inspect/modify: `polynexus/core/saxs_engine/figure_strain.py`
- Modify: `polynexus/gui/result_table_templates.py`, Workbench profile registry and mode adapters from Phase 1
- Test: existing SAXS provider, evidence, result table and figure lifecycle tests
- Create: `docs/acceptance/2026-07-25-saxs-full-vertical-slice.md`

- [x] Static: comparison/sample Main, structure support, correlation/IDF support and per-frame diagnostics.
- [x] Temperature: evolution Main, transition/Avrami support, condition review and selected evidence.
- [x] Strain: evolution Main, morphology/orientation/phase support, full sequence and low-q/excluded diagnostics.
- [x] Connect each mode to its Workbench Profile, Manifest, Gallery, Editor, data export and publication export.
- [ ] Cover normal, fallback, missing condition, low-confidence, invalid evidence and AI-off paths.
- [ ] Run real/Golden SAXS fixtures and restarted-GUI visual inspection; checkpoint the complete slice.

### Phase 3: DSC complete vertical slice

**Files:**
- Inspect/modify: `polynexus/core/dsc_engine/`
- Inspect/modify: `polynexus/gui/analysis_result_table_templates.py`
- Inspect/modify: shared Workbench profile registry
- Test: `tests/test_dsc_*`, figure pipeline and results-workbench tests
- Create: `docs/acceptance/2026-07-25-dsc-full-vertical-slice.md`

- [x] Standard: thermal curve, Tg/Tm/Tc/Xc and integration/baseline diagnostics.
- [x] Isothermal: crystallization evolution, Avrami fit and fit-range diagnostics.
- [x] Non-isothermal: conversion and Kissinger/Ozawa/Mo/Friedman support with method-disagreement diagnostics.
- [x] Connect FigureDocument/Manifest/Gallery/Editor/export and real-data visual acceptance.

### Phase 4: WAXS complete vertical slice

**Files:**
- Inspect/modify: `polynexus/core/waxs_engine/`
- Inspect/modify: `polynexus/gui/analysis_result_table_templates.py`
- Test: `tests/test_waxs_*`, image-grid, publication and lifecycle tests
- Create: `docs/acceptance/2026-07-25-waxs-full-vertical-slice.md`

- [x] Static: pattern/phase/Scherrer/orientation Main and diagnostics.
- [x] Temperature/time: transition and trend support.
- [x] Strain: orientation/phase/size and azimuthal evidence.
- [x] 2D detector/image-grid editing, preview, publication and fallback.

### Phase 5: IR complete vertical slice

**Files:**
- Inspect/modify: `polynexus/core/ir_engine/`
- Inspect/modify: `polynexus/gui/analysis_result_table_templates.py`
- Test: `tests/test_ir_*`, result review, mapping and lifecycle tests
- Create: `docs/acceptance/2026-07-25-ir-full-vertical-slice.md`

- [ ] Standard spectrum/band assignment/baseline quality.
- [ ] Temperature-2D spectral evolution, transition bands and sequence validity.
- [ ] Mapping/ROI map, spectra and invalid-pixel diagnostics.
- [ ] Connect Workbench, Figure Pack, Manifest/Gallery/Editor/export and visual fixtures.

Current checkpoint (2026-07-25): IR standard already has a shared provider;
temperature-2D now has Manifest-backed FigureDefinitions for its heatmap, band
tracking, band indices, and 2D-COS diagnostics. Mapping/ROI and the complete
IR acceptance chain remain open; see
`docs/acceptance/2026-07-25-ir-temperature-2d-workbench-checkpoint.md`.

### Phase 6: NMR complete vertical slice

**Files:**
- Inspect/modify: `polynexus/core/nmr_engine/`
- Inspect/modify: `polynexus/gui/analysis_result_table_templates.py`
- Test: `tests/test_nmr_*`, evidence, workbench and lifecycle tests
- Create: `docs/acceptance/2026-07-25-nmr-full-vertical-slice.md`

- [ ] Liquid H/C peak and assignment workbench.
- [ ] Solid H/C phase, crystallinity and assignment-coverage workbench.
- [ ] SNR, overlap, broad-line, solvent and weak-assignment diagnostics.
- [ ] Ensure unsupported Xc/phase claims remain provisional or diagnostic.

### Phase 7: Joint cross-technique vertical slice

**Files:**
- Inspect/modify: `polynexus/core/joint/`
- Inspect/modify: `polynexus/core/analysis_evidence_constraints*.py`
- Inspect/modify: Joint Workbench/result review/export adapters
- Test: `tests/test_joint_*`, cross-technique evidence and export tests
- Create: `docs/acceptance/2026-07-25-joint-full-vertical-slice.md`

- [ ] Add consistency checks for DSC/WAXS/SAXS crystallinity, Tm/L/lc, SAXS/WAXS multiscale, and IR/NMR assignment/calibration.
- [ ] Present conflicts as review evidence with provenance, never as silent correction.
- [ ] Add Joint report, Workbench, figure/export context and history linkage.

Current checkpoint (2026-07-25): the existing Joint hub rows now have a shared
FigureDefinition provider and Coordinator publication entrypoint for
`joint.series.crystallinity`, `joint.series.multiscale`, and
`joint.series.coverage`. The legacy `joint.compare` GUI report still needs to
consume that entrypoint; see
`docs/acceptance/2026-07-25-joint-figure-provider-checkpoint.md`.

### Phase 8: AI, release and full acceptance

**Files:**
- Inspect/modify: `polynexus/core/preprocess_optimization/`
- Inspect/modify: orchestrator, audit, calibration, export and release scripts
- Test: preprocessing Golden, AI-off, fault-injection, quality, boundary and full-suite tests
- Create: `docs/acceptance/2026-07-25-full-software-release.md`

- [ ] Verify deterministic output is valid without AI.
- [ ] Verify AI suggestions are scoped, auditable, hash-checked, reversible and never silently applied.
- [ ] Run `python scripts/verify.py --changed --types --full --boundary`.
- [ ] Run full relevant pytest matrix with an external basetemp.
- [ ] Perform restarted-GUI visual walkthrough for every Workbench mode, Gallery card, Editor entry and export bundle.
- [ ] Record human scientific review, known limitations and release decision.

### Checkpoint protocol for every phase

- [ ] Write failing tests before production behavior changes.
- [ ] Run focused red/green tests and inspect cumulative diff.
- [ ] Keep changed-file allowlist explicit; never include pre-existing scratch.
- [ ] Run the prescribed verifier and report exact output.
- [ ] Use `scripts/auto_commit.py` for one atomic phase checkpoint.
- [ ] Update `active-work.md`, `current-state.md`, task card and acceptance evidence.
