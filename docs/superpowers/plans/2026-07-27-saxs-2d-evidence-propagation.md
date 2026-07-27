# SAXS 2D Evidence Mode Propagation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Propagate existing detector and orientation evidence through all SAXS modes and persistence/export boundaries.

**Architecture:** Extend the existing shared quality-copy helper and add conservative series summary builders in the SAXS quality-contract module. Core DTOs carry evidence; `SAXSEngine` composes aligned parameter rows; Workbench, History, and Export consume the resulting payloads without scientific reinterpretation.

**Tech Stack:** Python dataclasses, NumPy, pytest, existing SAXS quality contracts, existing Workbench table model, JSON export bundle.

---

### Task 1: Lock the 2D transport contract with failing tests

**Files:**
- Create: `tests/test_saxs_2d_evidence_propagation.py`
- Reference: `polynexus/core/saxs_batch_helpers.py`
- Reference: `polynexus/core/saxs_engine/saxs_quality_contracts.py`

- [x] **Step 1: Add tests for deep-copy transport and conservative summaries.**
  Use `SimpleNamespace` objects with detector and orientation payloads. Assert
  the copied nested mappings are independent, partial frame lists retain
  `missing_frame_count`, summaries remain separate fields, and an empty input
  does not create a synthetic summary.
- [x] **Step 2: Run the new file and confirm RED.**
  Run `python -m pytest tests/test_saxs_2d_evidence_propagation.py -q`.
  Expected: failures because the shared helper and summary functions do not
  yet transport the new fields.

### Task 2: Implement shared 2D evidence transport and summaries

**Files:**
- Modify: `polynexus/core/saxs_batch_helpers.py`
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `polynexus/core/saxs_engine/__init__.py`
- Modify: `polynexus/core/saxs_export_bundle.py`

- [x] **Step 1: Add `detector_quality_report` and `orientation_evidence` to the shared copy allowlist.**
  Keep the helper non-mutating and use `deepcopy` exactly as for existing 1D
  fields.
- [x] **Step 2: Add conservative mode-summary builders.**
  Reuse the established level-count/coverage policy; preserve source reason
  codes and detector source kinds; return no payload when every frame is
  missing. Keep orientation as a separately named summary.
- [x] **Step 3: Add static-batch wrappers.**
  Build detector and orientation summaries from aligned analyses without
  creating a condition axis.
- [x] **Step 4: Make static export use the same summary helpers.**
  Keep single-frame export shape compatible and ensure strict JSON conversion.
- [x] **Step 5: Run the focused tests and confirm GREEN.**
  Run `python -m pytest tests/test_saxs_2d_evidence_propagation.py -q`.

### Task 3: Carry 2D evidence through core mode DTOs

**Files:**
- Modify: `polynexus/core/saxs_engine/core.py`
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`

- [x] **Step 1: Add optional detector and orientation fields to `SAXSResult`, `TemperaturePointResult`, `TempSeriesResult`, `StrainPointResult`, and `StrainSeriesResult`.**
  Preserve all existing fields and defaults.
- [x] **Step 2: Copy fields from successful `SAXSResult` objects into condition points.**
  A failed frame stays missing; no neighboring frame is copied.
- [x] **Step 3: Aggregate supplied point evidence into separate series fields.**
  Temperature uses source-index-aligned points; strain uses point order. Do not
  call `analyze_anisotropy` or infer raw detector metadata.
- [x] **Step 4: Run propagation tests and the existing 2D/core tests.**
  Run `python -m pytest tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_mode_evidence_propagation.py -q`.

### Task 4: Expose aligned evidence through parameters and Workbench diagnostics

**Files:**
- Modify: `polynexus/core/saxs.py`
- Modify: `tests/test_saxs_workbench_series_evidence.py`
- Modify: `tests/test_saxs_batch_parameters.py`

- [x] **Step 1: Add series-row alignment in `get_parameters()`.**
  Merge point evidence into `_batch_data`; temperature uses `source_index`
  rather than sorted row position. Preserve missing rows and deep-copy data.
- [x] **Step 2: Add static batch mode-level summaries to parameters.**
  Keep `metric_evidence_scope="static_batch"` and do not add a temperature or
  strain interpretation.
- [x] **Step 3: Add Workbench regression assertions.**
  Verify nested detector/orientation payloads appear in Diagnostics, while the
  review text does not call orientation a generic 1D trend.
- [x] **Step 4: Run the focused Workbench and parameter matrix.**
  Run `python -m pytest tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_batch_parameters.py tests/test_saxs_workbench_series_evidence.py -q`.

### Task 5: Verify persistence, export, and repository gates

**Files:**
- Modify: `tests/test_saxs_export_bundle.py`
- Modify: `tests/test_saxs_2d_evidence_propagation.py`
- Modify: `docs/agent/tasks/2026-07-27-saxs-2d-evidence-propagation.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Add History and Export assertions.**
  Confirm fields survive persistence, mode/frame export, and strict JSON
  serialization; confirm no `NaN` or `Infinity` is written.
- [x] **Step 2: Run the full SAXS file matrix.**
  Run `python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q`.
- [x] **Step 3: Run the structured verifier.**
  Set a dedicated `PYTEST_ADDOPTS` basetemp and run
  `python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-2d-evidence-propagation.md --changed --types`.
- [x] **Step 4: Review the cumulative diff and create one checkpoint.**
  Use `python scripts/auto_commit.py --message "feat(saxs): close 2d evidence propagation" --files ...` with an explicit allowlist containing only this task's files.
- [x] **Step 5: Update durable memory with evidence and limitations.**
  Record that no new 2D algorithm or AI application was enabled and that real
  detector/geometry scientific sign-off remains separate.
