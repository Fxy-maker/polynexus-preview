# DSC Non-isothermal Method Curves Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make DSC non-isothermal method figures fail closed when no authoritative plot points exist.

**Architecture:** Keep all analysis and fit gates unchanged. The provider will use `_method_points()` as the sole coordinate source, downgrade a rates-only method to Diagnostics, and preserve its completed parameters and gate reason in recipe metadata.

**Tech Stack:** Python, NumPy, pytest, DSC FigureDefinition contracts, repository verifier.

---

### Task 1: Prove the fabricated-curve regression

**Files:**

- Modify: `tests/test_dsc_publication_nonisothermal_provider.py`
- Modify: `tests/eval/test_dsc_publication_real_data.py`

- [x] **Step 1: Add the RED test.** Build a valid conversion series and a Kissinger result with `rates`, `r_squared`, and `kissinger_Ea_kJmol` but no x/y arrays. Assert the Kissinger definition is `diagnostic`, has no objects, and its recipe records `missing_method_plot_data` and `plot_point_count == 0`.
- [x] **Step 2: Update the ready fixture.** Add finite `x` and `y` arrays to the existing qualified Kissinger fixtures so the ready Main test represents authoritative method points rather than the old constant-y fallback.
- [x] **Step 3: Run RED.** The selected test failed because the current provider promoted the method and created a constant curve.

### Task 2: Remove the provider fabrication

**Files:**

- Modify: `polynexus/core/dsc_engine/figure_nonisothermal.py`

- [x] **Step 1: Gate on authoritative points.** `_method_gate()` returns `(False, "missing_method_plot_data")` when fewer than two finite aligned points exist.
- [x] **Step 2: Remove constant-y fallback.** `_method_definition()` uses only `_method_points(result)` and emits empty diagnostic data plus no objects when no points exist.
- [x] **Step 3: Preserve evidence metadata.** Kissinger/Ozawa/Mo/Friedman method parameters, `plot_point_count`, and `r_squared` are retained in recipe parameters.

### Task 3: Verify the complete DSC boundary

**Files:**

- Update: task card, plan, `docs/agent/memory/active-work.md`, and `docs/agent/memory/current-state.md`.

- [x] **Step 1: Run focused GREEN.** Selected provider regressions passed `2`; the complete provider file passed.
- [x] **Step 2: Run DSC lifecycle/eval matrix.** The cutover/lifecycle/eval matrix passed `13`; the complete DSC plus real publication matrix passed `70`.
- [x] **Step 3: Run structured verification and diff check.** The structured verifier exited `0` with quality `283`, preprocessing `106`, Ruff, compile, type baseline, memory/task, and whitespace checks passing; `git diff --check` passed.
- [x] **Step 4: Create one allowlist checkpoint.** Use `scripts/auto_commit.py` with exactly the changed-file allowlist after the verifier passes.

## Self-review

- No requirement relies on a fabricated curve or an inferred y value.
- A ready path requires explicit finite x/y points and remains compatible with
  the existing role/order contract.
- A missing-point path remains visible through Diagnostics and recipe metadata.
- No shared GUI, renderer, analysis algorithm, or unrelated scratch file is in
  the allowlist.
