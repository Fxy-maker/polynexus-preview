# SAXS Scientific Correctness Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the remaining SAXS physical and data-contract defects with independent regression evidence and fail-closed outputs.

**Architecture:** Keep behavior in SAXS core/services. Add explicit unit, q-grid, sequence-validity, and orientation-convention helpers while preserving legacy DTO fields and adding reason metadata. The GUI consumes the result contract and does not implement scientific branching.

**Tech Stack:** Python, NumPy, SciPy, h5py, pytest, existing SAXS quality/evidence contracts, `scripts/verify.py`.

---

### Task 1: Lock the physical correction contracts

**Files:**
- Create: `tests/test_saxs_scientific_correctness_repair.py`
- Modify: `polynexus/core/saxs_engine/preprocess.py`
- Modify: `polynexus/core/saxs_engine/saxs_extrapolation_helpers.py`
- Modify: `polynexus/core/saxs_engine/saxs_physical_helpers.py`
- Modify: `polynexus/core/saxs_engine/core.py`
- Modify: `polynexus/core/saxs_engine/config.py`

- [x] **Step 1: Write the failing analytic tests.** Add tests asserting that
  `T_sample=.5, T_background=1, I_sample=7, I_background=4` yields normalized
  intensity `10`, that a finite Guinier input does not extrapolate as constant
  `q*I`, and that independent `drho=.2, phi=.35, L=10 nm` values satisfy the
  documented Q/Kp equations.
- [x] **Step 2: Run the tests and confirm RED.** Run
  `python -m pytest -q tests/test_saxs_scientific_correctness_repair.py -k "background or guinier or porod"`.
  The current implementation must fail on the expected numeric assertions.
- [x] **Step 3: Implement the smallest physical fix.** Use
  `T_sample/T_background` before normalization, add explicit background
  thickness configuration for thickness mode, replace the q=0 extrapolation
  with a finite Guinier fit or an unchanged boundary plus reason, and implement
  the documented Porod equations with a phase-factor requirement for `Sv`.
  Assign `sp.Q_invariant` before anomaly confidence checks.
- [x] **Step 4: Run the focused tests GREEN.** Run the same command and then
  `python -m pytest -q tests/test_saxs_scientific_correctness_closure.py tests/test_saxs_correctness_slice_a.py`.
- [x] **Step 5: Review the diff.** Confirm signed residual handling and positive
  masks remain unchanged outside the corrected boundary, then checkpoint the
  physical files and tests with `scripts/auto_commit.py`.

### Task 2: Enforce q units and a stable Fourier grid

**Files:**
- Modify: `polynexus/core/saxs_engine/config.py`
- Modify: `polynexus/core/saxs_engine/io.py`
- Modify: `polynexus/core/saxs_engine/core.py`
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `tests/test_saxs_scientific_correctness_repair.py`

- [x] **Step 1: Write failing unit/grid tests.** Assert an explicit
  `angstrom^-1` profile converts to the same nm results as its nm equivalent,
  a text profile without q metadata is marked unavailable for absolute metrics,
  and duplicate/non-uniform q input produces a monotonic uniform analysis view.
- [x] **Step 2: Run RED.** Run
  `python -m pytest -q tests/test_saxs_scientific_correctness_repair.py -k "unit or grid"`.
- [x] **Step 3: Implement the contract.** Add `q_unit` and provenance to the
  config/reader path, normalize recognized unit aliases, block absolute metrics
  when no unit is declared, and prepare a deduplicated uniform q view before
  correlation/extrapolation/smoothing while retaining the original profile.
- [x] **Step 4: Run GREEN and existing SAXS input tests.** Run the focused unit
  tests and `python -m pytest -q tests/test_saxs_correctness_slice_a.py`.
- [x] **Step 5: Checkpoint.** Use an explicit changed-file allowlist with
  `python scripts/auto_commit.py --message "fix(saxs): enforce units and stable q grids" ...`.

### Task 3: Make temperature kinetics and thermodynamics evidence-gated

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `polynexus/core/saxs_engine/config.py`
- Modify: `tests/test_saxs_scientific_correctness_repair.py`

- [x] **Step 1: Write failing sequence tests.** Assert a monotonic cooling Q
  sequence uses fixed complete-sequence endpoints, `times=None` returns
  `avrami.valid is False` with `time_axis_required`, and Gibbs-Thomson rejects
  points whose `melting_window_status` is outside the melting window.
- [x] **Step 2: Run RED.** Run
  `python -m pytest -q tests/test_saxs_scientific_correctness_repair.py -k "cooling or avrami or gibbs"`.
- [x] **Step 3: Implement the gates.** Calculate Xc after endpoint selection,
  never synthesize frame seconds, pass only melting-window points into the
  regression, and require an explicit `delta_Hf_Jm3` for surface energy.
- [x] **Step 4: Run GREEN.** Run the focused temperature tests and all existing
  SAXS temperature tests discovered by `rg -l "temperature|avrami|gibbs" tests`.
- [x] **Step 5: Checkpoint.** Commit only the temperature/config/test changes.

### Task 4: Isolate frame geometry and reject ambiguous containers

**Files:**
- Modify: `polynexus/core/saxs_engine/io.py`
- Modify: `polynexus/core/saxs.py`
- Modify: `tests/test_saxs_scientific_correctness_repair.py`

- [x] **Step 1: Write failing I/O tests.** Assert that two header parses do
  not share mutable geometry, and that an HDF5 file with two equally eligible
  datasets raises `UnsupportedDatasetError` instead of selecting alphabetically.
- [x] **Step 2: Run RED.** Run
  `python -m pytest -q tests/test_saxs_scientific_correctness_repair.py -k "geometry or hdf5"`.
- [x] **Step 3: Implement isolated configs and dispatch.** Copy the config
  before applying header values, persist per-frame geometry provenance, route
  HDF5/Nexus directly to the container reader before Fabio, and reject
  unresolved candidate ties.
- [x] **Step 4: Run GREEN.** Run the focused I/O tests and existing HDF5/reader
  tests.
- [x] **Step 5: Checkpoint.** Commit the isolated geometry and container changes.

### Task 5: Correct projected orientation and sector symmetry

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_anisotropy.py`
- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/gui/i18n.py`
- Modify: `polynexus/gui/result_table_templates.py`
- Modify: `tests/test_saxs_scientific_correctness_repair.py`

- [x] **Step 1: Write failing orientation tests.** Assert a uniform ring has
  the documented projected baseline, mirrored +90/-90 and 0/180 sectors give
  equal results, and the public label/convention identifies a projected 2D
  order parameter rather than an unqualified 3D Herman factor.
- [x] **Step 2: Run RED.** Run
  `python -m pytest -q tests/test_saxs_scientific_correctness_repair.py -k "orientation or sector"`.
- [x] **Step 3: Implement wrapped masks and labels.** Use angular distance modulo
  pi for meridional/equatorial masks, expose a projected metric name and reason,
  and retain `f_Herman` as a compatibility alias only.
- [x] **Step 4: Run GREEN.** Run the focused orientation tests and existing 2D
  detector/orientation matrices.
- [x] **Step 5: Checkpoint.** Commit the orientation and presentation changes.

### Task 6: Integrated verification and durable state

**Files:**
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/acceptance/2026-08-04-saxs-scientific-correctness-repair.md`

- [x] **Step 1: Run the focused and full tests.** Run the focused repair suite,
  all affected SAXS tests, `python scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-scientific-correctness-repair.md --changed --types`,
  `python scripts/verify.py --changed --types --full --boundary`, and
  `git diff --check`.
- [x] **Step 2: Review the cumulative diff.** Verify every acceptance item has
  a direct test or an explicit human-review limitation; do not claim full
  verification if a command times out or fails.
- [x] **Step 3: Write acceptance evidence.** Record exact commands/results,
  changed files, known calibration limitations, and intentionally untouched
  pre-existing workspace changes.
- [x] **Step 4: Create the final checkpoint.** Run
  `python scripts/auto_commit.py` with the complete explicit allowlist and a
  `fix(saxs): repair scientific correctness contracts` message.
