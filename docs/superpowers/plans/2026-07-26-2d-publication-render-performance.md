# 2D Publication Render Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bound WAXS strain publication image-grid snapshots so complete real directories can reach the shared Gallery/Editor/export lifecycle without changing scientific inputs or results.

**Architecture:** Keep raw detector arrays on the loaded scans for analysis. Downsample only the editable publication snapshot at the WAXS figure-definition boundary, using vectorized NumPy construction and the existing `image_grid` contract. The renderer, editor, manifest, and export contracts remain unchanged.

**Tech Stack:** Python, NumPy, Pytest, PolyNexus FigureDefinition/image-grid pipeline.

---

### Task 1: Bound WAXS strain image-grid publication data

**Files:**
- Modify: `polynexus/core/waxs_engine/figure_strain.py`
- Test: `tests/test_waxs_publication_strain_provider.py`
- Create: `docs/agent/tasks/2026-07-26-2d-publication-render-performance.md`

- [x] **Step 1: Write the failing regression** asserting each image-grid frame is at most 256×256 while preserving the image-grid columns and selected frame count.
- [x] **Step 2: Run the focused regression and verify it fails because the provider currently serializes the full detector image.**
- [x] **Step 3: Implement vectorized bounded sampling at the figure-definition boundary.**
- [x] **Step 4: Run the focused provider/document/renderer matrix and verify it passes.**
- [x] **Step 5: Run the real WAXS strain pipeline and measure analysis versus publication time.**
- [x] **Step 6: Run the structured verifier and create one allowlist checkpoint commit.**

### Task 2: Bound IR temperature-2D publication snapshots

**Files:**
- Modify: `polynexus/core/ir_engine/figure_provider.py`
- Test: `tests/test_ir_complete_figure_provider.py`
- Update: `tests/test_real_published_run_walkthrough.py` and the real-run acceptance ledger.

- [x] **Step 1: Measure IR analysis and publication separately on the complete fixture.**
- [x] **Step 2: Add failing regressions for duplicate per-frame publication and unbounded correlation rows.**
- [x] **Step 3: Skip duplicate generic frame figures for the temperature-2D publication and cap correlation snapshots at 420×420.**
- [x] **Step 4: Re-run the complete IR temperature-2D Gallery/Editor/export/History walkthrough.**

## Verification commands

```powershell
python -m pytest --basetemp=C:\Temp\PolyNexus_waxs_2d_perf tests/test_waxs_publication_strain_provider.py tests/test_waxs_figure_document.py tests/test_figure_image_grid.py tests/test_v2_adapter_image_grid.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-26-2d-publication-render-performance.md --changed --types
```

## Non-goals

- Do not change WAXS raw detector data, strain analysis, scientific thresholds, or publication-role eligibility.
- Do not promote diagnostic-only or validation-error data to Main.
- Do not change IR mapping/ROI semantics or Joint inputs.
