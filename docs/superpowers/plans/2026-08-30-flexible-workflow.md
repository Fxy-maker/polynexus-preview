# Flexible Workflow and Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove unnecessary routing rigidity while preserving canonical scientific validation and shared provenance.

**Architecture:** Keep `CanonicalExperiment`, `AnalysisRecipe`, `ComputeRun`, and evidence objects as the only public contracts. Let canonical conversion and artifact inspection decide input validity; project adapters only select the appropriate recipe shape. Extract only small helpers used by at least two adapters.

**Tech Stack:** Python dataclasses, existing project workflow adapters, canonical converter registry, pytest, repository verifier.

---

### Task 1: Lock flexible routing behavior with regression tests

**Files:**
- Modify: `tests/test_project_workflow_adapters.py`
- Modify: `tests/test_mixed_technique_project_run.py`

- [ ] Add a test that creates two valid IR table files beneath a directory whose path contains `saxs`, submits them to `TechniqueSeriesAdapter` with `technique="ir"`, and asserts a ready two-step recipe.
- [ ] Add a test that sends an IR temperature directory through `MixedTechniqueAdapter` without relying on a pre-count branch and asserts the canonical template remains `ir.temperature_series.v1`.
- [ ] Run the focused tests and confirm the new path-name case fails before implementation.

### Task 2: Remove path-name and duplicate preflight gates

**Files:**
- Modify: `polynexus/core/project_workflow/adapters.py`

- [ ] Delete the `technique_markers` path-token checks from `TechniqueSeriesAdapter.propose_recipe`; keep artifact inspection and converter outcomes as the authority.
- [ ] Replace the mixed IR branch's `sum(... ) >= 2` condition with a directory-shape dispatch based only on `technique == "ir"`, one path, and `Path.is_dir()`; let `IRTemperatureSeriesAdapter`/canonical conversion return `needs_input` for insufficient frames.
- [ ] Keep NMR explicit submodule validation and all recipe shape checks unchanged.
- [ ] Run Task 1 tests and confirm GREEN.

### Task 3: Extract only proven shared adapter helpers

**Files:**
- Modify: `polynexus/core/project_workflow/adapters.py`
- Modify: `tests/test_project_workflow_adapters.py`

- [ ] Add one private helper that loads a manifest and one private helper that converts an inspected artifact through the default registry, returning the existing `ConversionOutcome` unchanged.
- [ ] Replace duplicated calls in single, series, and IR temperature adapters with those helpers without changing reason codes or status mapping.
- [ ] Add a round-trip regression assertion for canonical source artifact IDs and conversion IDs across single and series recipes.
- [ ] Run focused adapter and ComputeRun tests and confirm GREEN.

### Task 4: Cross-entry verification and documentation

**Files:**
- Modify: `docs/agent/tasks/2026-08-30-multitech-template-closure.md`
- Modify: `docs/acceptance/2026-08-30-multitech-template-closure.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Record the exact gates removed, the gates intentionally retained, and the affected CLI/GUI/AI shared consumers.
- [ ] Run focused project, detector, NMR, and mixed-technique tests.
- [ ] Run `python scripts/verify.py --changed --types` and the task verifier.
- [ ] Review `git diff --check`, preserve pre-existing untracked runtime files, and create one allowlisted checkpoint with `scripts/auto_commit.py`.
