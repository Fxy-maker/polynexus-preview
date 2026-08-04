# SAXS Iq2 and Fourier Figures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add editable complete `I(q)q^2` curves to ordinary, temperature, and strain SAXS figure routes while preserving the existing normalized Fourier correlation `gamma(r)` contract.

**Architecture:** Figure providers project the existing `analysis.kratky` arrays through shared finite-pair logic. Static uses its existing diagnostic trace path plus profile panels; temperature gets selected-frame Kratky evidence and a full-series overlay; strain gets a full-series Kratky overlay while keeping scalar method evidence. No core analysis or GUI event handler changes are needed.

**Tech Stack:** Python, NumPy, existing `FigureDefinition`/`FigureDataSourceDefinition` contracts, pytest.

---

### Task 1: Establish provider regressions

**Files:**
- Modify: `tests/test_saxs_figure_document.py`
- Modify: `tests/test_saxs_temperature_figure_provider.py`
- Modify: `tests/test_saxs_figure_evidence_binding.py`
- Create: `tests/test_saxs_iq2_fourier_figures.py`

- [ ] **Step 1: Write failing tests**

  Assert static definitions expose a `kratky` trace with `q_nm_inv` and
  `intensity_q2`; temperature selected evidence exposes a `kratky` panel and
  a full-series Kratky definition; strain definitions expose a complete
  sequence Kratky trace; correlation definitions retain `r_nm` and `gamma`.

- [ ] **Step 2: Run the focused tests to verify RED**

  Run:
  `python -m pytest -q tests/test_saxs_iq2_fourier_figures.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_figure_document.py`

  Expected: new provider assertions fail because temperature/strain complete
  Kratky trace definitions are absent.

### Task 2: Add shared Kratky projection helper

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_common.py`
- Test: `tests/test_saxs_iq2_fourier_figures.py`

- [ ] **Step 1: Add a provider-only helper**

  Add `kratky_curve_from_frame(frame)` that reads `frame.analysis.kratky`,
  coerces `q` and `kratky`, retains finite pairs, sorts q stably, and returns
  `(q, kratky, quality)` or `None`. It must not call `kratky_analysis`.

- [ ] **Step 2: Run helper tests**

  Run:
  `python -m pytest -q tests/test_saxs_iq2_fourier_figures.py::test_kratky_projection_filters_invalid_pairs`

  Expected: PASS.

### Task 3: Add ordinary/static Iq2 trace coverage

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_static.py`
- Modify: `polynexus/core/saxs_engine/saxs_output_documents.py` only if the
  existing static overview document needs the new source object.
- Test: `tests/test_saxs_iq2_fourier_figures.py`

- [ ] **Step 1: Implement the complete static trace projection**

  Extend the representative profile object builder to add a second source
  column `intensity_q2` from `analysis.kratky`, with `q_nm_inv` as x and
  `intensity_q2` as y. Keep the existing scalar `kratky` diagnostic unchanged.

- [ ] **Step 2: Run static tests**

  Run:
  `python -m pytest -q tests/test_saxs_iq2_fourier_figures.py -k static`

  Expected: PASS.

### Task 4: Add temperature selected and full-series Iq2 figures

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_temperature.py`
- Test: `tests/test_saxs_iq2_fourier_figures.py`
- Test: `tests/test_saxs_temperature_figure_provider.py`

- [ ] **Step 1: Add Kratky to selected-frame evidence**

  Extend `_build_selected_evidence` with a `kratky` panel sourced from
  `analysis.kratky.q` and `analysis.kratky.kratky`, using q in nm^-1 and
  intensity_q2 in a.u. nm^-2. Preserve correlation and IDF panel order.

- [ ] **Step 2: Add a full-series Kratky overlay**

  Add `_build_kratky_waterfall` parallel to `_build_waterfall`, one line per
  frame, with condition labels and a `projection_quality` recipe field. Add
  it to `build_temperature_figure_definitions` after the intensity waterfall.

- [ ] **Step 3: Run temperature tests**

  Run:
  `python -m pytest -q tests/test_saxs_iq2_fourier_figures.py -k temperature tests/test_saxs_temperature_figure_provider.py`

  Expected: PASS.

### Task 5: Add strain full-series Iq2 figure

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_strain.py`
- Test: `tests/test_saxs_iq2_fourier_figures.py`

- [ ] **Step 1: Add a strain Kratky overlay definition**

  Add `_kratky_definition` using all valid strain frames, one `plot_series`
  per frame, x `q_nm_inv`, y `intensity_q2`, and explicit source paths and
  projection quality. Include the definition in
  `build_strain_figure_definitions` without removing scalar method evidence.

- [ ] **Step 2: Run strain tests**

  Run:
  `python -m pytest -q tests/test_saxs_iq2_fourier_figures.py -k strain`

  Expected: PASS.

### Task 6: Verify labels, exports, and repository gates

**Files:**
- Modify: `tests/test_saxs_figure_document.py` if document source expectations
  need explicit `intensity_q2` coverage.
- Modify: `docs/agent/tasks/2026-08-04-saxs-iq2-fourier-figures.md`

- [ ] **Step 1: Run the complete focused matrix**

  Run:
  `python -m pytest -q tests/test_saxs_iq2_fourier_figures.py tests/test_saxs_figure_document.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_figure_evidence_binding.py`

  Expected: all selected tests pass.

- [ ] **Step 2: Run repository verification**

  Run:
  `python -X utf8 scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-iq2-fourier-figures.md --changed --types`

  Expected: task check, Ruff, compile, quality gate, preprocessing gate, and
  whitespace check pass.

- [ ] **Step 3: Review diff and checkpoint**

  Run `git diff --check`, review the explicit file allowlist, then invoke
  `scripts/auto_commit.py` with only the files listed above. Existing staged
  user changes must remain untouched and may block the checkpoint.
