# SAXS Temperature Guinier Sequence Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make existing temperature Guinier sequence evidence source-traceable and visible through the established SAXS transport and review boundaries.

**Architecture:** Keep `build_guinier_sequence_evidence()` as the sole observational sequence summarizer. Add an optional source-index mapping at the quality-contract boundary, pass it from `TempSeriesResult`, and expose the immutable JSON-safe payload through existing parameter, Workbench, DataFrame, History, and Export consumers.

**Tech Stack:** Python, NumPy, PySide6-facing Results DTOs, pytest, Ruff, PolyNexus structured verifier.

---

### Task 1: Lock the sequence source mapping contract

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Test: `tests/test_saxs_guinier_sequence_evidence.py`

- [x] Add a failing test for source indices surviving JSON round-trip and for a mismatched source-index list remaining diagnostic.
- [x] Run the focused contract tests and verify the new assertions fail for the missing field/API.
- [x] Add the optional `frame_source_indices` contract field and builder input with no repair or interpolation.
- [x] Run the focused contract tests and verify they pass.

### Task 2: Propagate source identity from the temperature engine

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Test: `tests/test_saxs_temperature_guinier_evidence.py`

- [x] Add a failing regression using unsorted input temperatures and assert sequence order plus original `source_index` mapping.
- [x] Run the regression and verify it fails because the builder currently has no source mapping.
- [x] Pass the existing `TemperaturePointResult.source_index` values into the builder and add `source_index` to `to_dataframe()`.
- [x] Run the temperature/DataFrame matrix and verify it passes without changing frame values or order.

### Task 3: Expose the detailed sequence evidence to consumers

**Files:**
- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/core/saxs_batch_helpers.py`
- Modify: `polynexus/gui/saxs_results_table_service.py`
- Test: `tests/test_saxs_batch_parameters.py`
- Test: `tests/test_saxs_workbench_series_evidence.py`
- Test: `tests/test_saxs_export_bundle.py`

- [x] Add failing assertions for temperature parameters and Workbench diagnostics/review text.
- [x] Run the consumer tests and verify the assertions fail without transport/display changes.
- [x] Copy the existing JSON-safe sequence payload through the temperature branch and render only its level, counts, source-index context, and reasons.
- [x] Verify Export and History retain the same payload and no strain/static path gains temperature sequence state.

### Task 4: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-27-saxs-temperature-guinier-sequence-transport.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] Run the focused SAXS matrix with an isolated basetemp.
- [x] Run `python scripts/verify.py --task ... --changed --types` with an isolated basetemp and record exact output.
- [x] Run the relevant full/boundary verification when practical and record any environmental limitation without hiding it.
- [ ] Run `git diff --check`, review the cumulative diff, and create one explicit-allowlist checkpoint with `scripts/auto_commit.py`.
