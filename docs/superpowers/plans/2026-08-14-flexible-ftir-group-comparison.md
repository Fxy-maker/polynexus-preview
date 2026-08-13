# Flexible FTIR Group Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render useful FTIR comparison candidates for two ARS-selected groups without blocking on imperfect condition alignment.

**Architecture:** Extend the existing FTIR group renderer with a comparison branch. Keep selection validation and provider orchestration in the workflow service, while the renderer owns spectrum alignment, optional difference/trend candidates, and warning metadata. Preserve the existing one-group path and package contracts.

**Tech Stack:** Python dataclasses, NumPy, Matplotlib, existing IR reader/preprocessor, pytest.

---

### Task 1: Lock the flexible comparison contract with failing tests

**Files:**
- Modify: `tests/test_ars_group_figure_candidates.py`

- [ ] Add tests proving two selected groups execute providers and return a comparison overlay.
- [ ] Add a test proving mismatched condition axes keep the overlay and omit only the difference candidate.
- [ ] Add a test proving mixed metric methods retain a limitation instead of suppressing the complete comparison trend.
- [ ] Run the focused tests and confirm they fail because comparison is currently blocked.

### Task 2: Implement FTIR comparison rendering

**Files:**
- Modify: `polynexus/core/project_workflow/ir_group_figures.py`

- [ ] Load usable spectra per selected group using the existing reader/preprocessing path.
- [ ] Render a two-group shared-grid overlay whenever both groups contribute at least one spectrum; use group-specific colors and condition labels.
- [ ] Match conditions by exact numeric value for an optional difference candidate; omit it with `comparison_conditions_unmatched` when alignment is incomplete.
- [ ] Render a comparison metric trend when each group has complete finite metrics, retaining method differences in limitations.
- [ ] Keep all output under the selection figure directory and write the canonical manifest.
- [ ] Run focused comparison tests and confirm they pass.

### Task 3: Remove the provider-free comparison block and preserve orchestration

**Files:**
- Modify: `polynexus/core/project_workflow/service.py`
- Modify: `docs/agent/tasks/2026-08-14-ars-selected-group-figure-candidates.md`
- Modify: `docs/acceptance/2026-08-14-ars-selected-group-figure-candidates.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Remove the `group_comparison_not_implemented` early return.
- [ ] Keep selected artifact filtering and provider execution unchanged.
- [ ] Document that comparison is best-effort and review-required.
- [ ] Run the project workflow regression matrix.

### Task 4: Verify and checkpoint

**Files:**
- Modify: `polynexus/core/project_workflow/ir_group_figures.py`
- Modify: `polynexus/core/project_workflow/service.py`
- Modify: `tests/test_ars_group_figure_candidates.py`
- Modify: `docs/agent/tasks/2026-08-14-ars-selected-group-figure-candidates.md`
- Modify: `docs/acceptance/2026-08-14-ars-selected-group-figure-candidates.md`
- Modify: `docs/agent/memory/active-work.md`
- Create: `docs/superpowers/specs/2026-08-14-flexible-ftir-group-comparison-design.md`
- Create: `docs/superpowers/plans/2026-08-14-flexible-ftir-group-comparison.md`

- [ ] Run `python scripts/verify.py --task docs/agent/tasks/2026-08-14-ars-selected-group-figure-candidates.md --changed --types`.
- [ ] Run `git diff --check`.
- [ ] Commit only the explicit allowlist with `scripts/auto_commit.py`.
