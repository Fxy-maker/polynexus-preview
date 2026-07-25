# IR mapping/ROI contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a validated IR mapping/ROI payload through the shared figure lifecycle without guessing instrument semantics.

**Architecture:** Add immutable-ish dataclasses and pure validation/provider functions in the IR core. The engine only hands an optional mapping result to the existing provider; the GUI profile names the resulting Manifest IDs. Tests cover red/green contract validation and pipeline publication.

**Tech Stack:** Python, NumPy, PySide6-facing profile DTOs, shared FigureDefinition/FigurePipeline contracts, pytest.

---

### Task 1: Lock the mapping/ROI DTO behavior with failing tests

**Files:**
- Create: `tests/test_ir_mapping.py`

- [ ] **Step 1: Write failing tests** for shape validation, three figure IDs, and Manifest publication using explicit scalar-map and ROI-spectrum fixtures.
- [ ] **Step 2: Run `python -m pytest tests/test_ir_mapping.py -q`** and confirm failure because the mapping module and provider are absent.

### Task 2: Implement the pure mapping/ROI contract and provider

**Files:**
- Create: `polynexus/core/ir_engine/ir_mapping.py`

- [ ] **Step 1: Add DTOs and validation** with explicit coordinates, mask, metric label, ROI spectra, and provenance.
- [ ] **Step 2: Add Main/SI/diagnostic FigureDefinitions** using shared data sources and recipes.
- [ ] **Step 3: Run `python -m pytest tests/test_ir_mapping.py -q`** and confirm all contract tests pass.

### Task 3: Connect engine and Workbench profile

**Files:**
- Modify: `polynexus/core/ir.py`
- Modify: `polynexus/gui/results_workbench_profiles.py`
- Modify: `tests/test_ir_nmr_joint_workbench_profiles.py`
- Modify: `tests/test_ir_complete_figure_provider.py`

- [ ] **Step 1: Add optional engine handoff** and preserve existing standard/temperature outputs.
- [ ] **Step 2: Replace mapping template placeholders with the real figure IDs**, keeping diagnostic routing explicit.
- [ ] **Step 3: Run the focused IR/provider/profile matrix.**

### Task 4: Verify and checkpoint

**Files:**
- Modify: `docs/acceptance/2026-07-25-ir-mapping-roi-checkpoint.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [ ] **Step 1:** Run the task-scoped verifier and inspect `git diff --check`.
- [ ] **Step 2:** Record exact results and known reader/visual limitations.
- [ ] **Step 3:** Create one checkpoint with `scripts/auto_commit.py` using an explicit allowlist.
