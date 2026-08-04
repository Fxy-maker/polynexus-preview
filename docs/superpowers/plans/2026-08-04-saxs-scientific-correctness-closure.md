# SAXS Scientific Correctness Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the 14 known SAXS findings with physically correct or fail-closed behavior.

**Architecture:** Keep technique behavior in the SAXS core/services. Introduce one explicit signed-profile/positive-mask boundary and one total-vs-sector channel contract; let I/O and GUI consume the resulting DTO/provenance instead of inferring physical validity. Preserve existing public result fields while adding reason codes and eligibility gates.

**Tech Stack:** Python, NumPy, pytest, PySide6 result templates, existing SAXS quality/evidence contracts, `scripts/verify.py`.

---

### Task 1: Lock the physical-core regressions

**Files:**
- Create: `tests/test_saxs_scientific_correctness_closure.py`
- Modify: `polynexus/core/saxs_engine/saxs_physical_helpers.py`
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `polynexus/core/saxs_engine/core.py`
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`

- [x] Write tests for unit-equivalent invariant inputs, cooling labels/order, signed residual retention, and positive-mask coverage.
- [x] Run `python -m pytest -q tests/test_saxs_scientific_correctness_closure.py`; verify each new test fails for the current behavior.
- [x] Implement a unit-explicit invariant helper. Convert q and length consistently, and return a structured unavailable reason when the dimensionless contract cannot be satisfied.
- [x] Change cooling classification so high normalized invariant is solid and low normalized invariant is melt; retain acquisition order for cooling/isothermal inputs.
- [x] Preserve signed corrected intensity and add a positive-only view/mask for log-domain consumers. Keep raw quality counts for negative residuals.
- [x] Re-run the focused file and verify it passes without changing unrelated consumers.

### Task 2: Separate total and sector channels in strain analysis

**Files:**
- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`
- Modify: `polynexus/core/saxs_engine/figure_strain.py`
- Modify: `tests/test_saxs_scientific_correctness_closure.py`

- [x] Add a regression fixture with identical full intensity and two different equatorial sectors; assert full-channel invariant/structure equality and sector-only orientation changes.
- [ ] Run the new test and verify it fails because `_run_strain_pipeline()` currently passes equatorial data to `analyze_single()`.
- [x] Add explicit total and anisotropy channel arguments to the strain service; route full profiles to invariant/structure consumers and sectors only to orientation/anisotropy consumers.
- [x] Preserve existing result DTO fields and add source-channel provenance for Q-star and structure metrics.
- [x] Run the focused strain matrix and verify all channel tests pass.

### Task 3: Make I/O and batch limits explicit

**Files:**
- Modify: `polynexus/core/saxs_engine/io.py`
- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/core/saxs_engine/config.py`
- Modify: `tests/test_saxs_scientific_correctness_closure.py`

- [x] Add tests for declared extension parity, typed HDF5/Nexus dataset errors, single-vs-directory preprocessing parity, and configured frame-limit provenance.
- [ ] Run the tests to capture RED failures for current `.cbf/.h5/.nxs` and hard-limit behavior.
- [x] Centralize extension dispatch and add HDF5/Nexus dataset selection with actionable errors; keep unsupported readers fail-closed.
- [x] Replace hard-coded 10/48 limits with config values whose default is unlimited; record every configured skip in `sequence_qa` and result metadata.
- [x] Run I/O and workflow focused matrices.

### Task 4: Tighten geometry and result/figure semantics

**Files:**
- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/core/saxs_engine/figure_eligibility.py`
- Modify: `polynexus/gui/result_table_templates.py`
- Modify: `tests/test_saxs_scientific_correctness_closure.py`

- [x] Add tests showing incomplete geometry, invalid Q-star, and all-NaN void fraction cannot become main/publication output.
- [ ] Run tests to capture current over-permissive eligibility and primary-field behavior.
- [x] Require complete physical geometry evidence and explicit Q-star/analysis gates before `main`; preserve SI/diagnostic roles with reason codes.
- [x] Keep `Q_star_rel` as a relative diagnostic field and enable `phi_void` primary display only for finite valid values.
- [x] Run focused figure/result matrices and inspect the resulting DTOs.

### Task 5: Integrated verification and review

**Files:**
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/acceptance/2026-08-04-saxs-scientific-correctness-closure.md`

- [x] Run `python scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-scientific-correctness-closure.md --changed --types`.
- [x] Run `python scripts/verify.py --changed --types --full --boundary`; record timeout or failure honestly.
- [x] Run `git diff --check` and the focused SAXS matrix.
- [x] Review the cumulative diff against the design and task card; fix critical/important findings before checkpoint.
- [ ] Create one atomic checkpoint with the explicit changed-file allowlist using `scripts/auto_commit.py` after verification.
