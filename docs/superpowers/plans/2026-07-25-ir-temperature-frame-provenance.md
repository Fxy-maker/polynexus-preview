# IR temperature-2D frame provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Preserve temperature-series frame conditions in IR FigureDefinitions.

**Architecture:** Add numeric condition columns to shared CSV snapshots and keep
  categorical/ordering metadata in the existing recipe payload. The plotted
  sequence-frame axis and publication roles remain unchanged.

**Tech Stack:** Python, NumPy, pytest, FigurePipeline.

---

### Task 1: Red regression

**Files:**

- Modify: `tests/test_ir_complete_figure_provider.py`

- [x] Assert heatmap/band source schemas, condition values, and recipe metadata.
- [x] Run the new test and observe missing metadata failure.

### Task 2: Minimal provider implementation

**Files:**

- Modify: `polynexus/core/ir_engine/figure_provider.py`

- [x] Add numeric temperature/time columns with NaN for absent values.
- [x] Add JSON-safe frame metadata and preserve stage/order semantics in recipe.
- [x] Keep renderer-compatible numeric CSV snapshots.

### Task 3: Verification checkpoint

- [x] Run 15-test IR provider/temperature matrix.
- [x] Run task verifier and create allowlisted checkpoint.
