# IR Three-Mode Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explicitly close the IR Main/SI/diagnostic figure-role contract across standard, temperature-2D, and mapping/ROI modes.

**Architecture:** Reuse the existing IR providers and shared FigurePipeline. Only the provider assigns publication roles; the pipeline owns document, asset, Manifest, and sibling-failure behavior.

**Tech Stack:** Python, NumPy, pytest, FigureDefinition/Manifest contracts.

---

### Task 1: Lock the role matrix with failing tests

**Files:**
- Modify: `tests/test_ir_complete_figure_provider.py`
- Modify: `tests/test_ir_figure_provider.py`

- [ ] Add assertions for standard, temperature-2D, and mapping role matrices.
- [ ] Add a sibling-safe generation failure test using one invalid definition and one valid definition through `FigurePipeline`.
- [ ] Run the focused tests and observe the standard role assertions fail before implementation.

### Task 2: Make standard IR roles explicit

**Files:**
- Modify: `polynexus/core/ir_engine/figure_provider.py`

- [ ] Assign Main only to the first emitted spectrum and SI to subsequent spectra.
- [ ] Assign SI to peak-fit and diagnostic to computed comparison.
- [ ] Assign Main to the crystallinity overview.
- [ ] Run the focused provider tests.

### Task 3: Verify temperature/mapping roles and failure visibility

**Files:**
- Modify: `polynexus/core/ir_engine/figure_provider.py` only if the locked tests expose a missing role.
- Modify: `tests/test_ir_mapping.py` only if role coverage is absent.

- [ ] Keep heatmap Main, tracking/indices SI, correlations diagnostic, and mapping Main/SI/diagnostic unchanged and explicitly tested.
- [ ] Verify `FigurePipeline` preserves ready siblings beside a `generation_failed` entry.
- [ ] Run focused tests, task verifier, and `git diff --check`.

### Task 4: Record checkpoint evidence

**Files:**
- Create: `docs/acceptance/2026-07-25-ir-three-mode-vertical-slice.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [ ] Record exact commands and counts.
- [ ] Record external reader, real fixture, AI/fallback, export-bundle, and restarted-GUI limitations.
- [ ] Run `scripts/auto_commit.py` with the explicit changed-file allowlist.
