# SAXS strain other panels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 锁定拉伸 SAXS 的主图/SI/diagnostic order，并让已有拉伸 review summary 在结果页提示区复用统一消费边界。

**Architecture:** provider 继续是唯一 figure order/role 来源；GUI 只把已有 `saxs_strain_summary_text`、risk 和 next-step 结果传给共享 review hint。不会新增科学计算或跨层接口。

**Tech Stack:** Python、pytest、PySide6 test doubles、Ruff、`scripts/verify.py`、`scripts/auto_commit.py`。

---

### Task 1: Lock strain publication panel order

**Files:**
- Modify: `tests/test_saxs_publication_pack_upgrade.py`
- Inspect: `polynexus/core/saxs_engine/figure_strain.py`

- [x] **Step 1: Reuse the existing 1D strain fixture**

  Use `_static_engine(3)` from the existing test module, set both
  `_condition_type` and `cfg.experiment_type` to `strain`, and attach the existing
  three-point `_strain_result` fixture shape.

- [x] **Step 2: Add the order/role regression**

  Assert the emitted IDs start with `saxs.strain.evolution.1d`,
  `saxs.strain.sequence.1d`, and `saxs.strain.invariant`; assert display orders
  are `[10, 100, 105, 110, 220]` for the fixture; assert roles are `main`, then
  `si` for sequence/invariant/correlation, and `diagnostic` for low-q.

- [x] **Step 3: Run the focused strain test**

  Run `python -m pytest tests/test_saxs_publication_pack_upgrade.py::test_strain_pack_orders_main_support_and_diagnostic_panels -q`.
  The current provider satisfies the contract, so this regression passes without
  a provider change.

### Task 2: Extend review-hint consumption through TDD

**Files:**
- Modify: `tests/test_main_window_output_mixin.py`
- Modify: `polynexus/gui/main_window_output_mixin.py`

- [x] **Step 1: Add the failing strain consumer test**

  Call `_update_results_review_hint` with a `_ResultsHintWindow("saxs", "saxs.strain")`
  and assert the recorder receives the exact summary/risk/next-step, status
  `review`, a localized action label, and a callable action.

- [x] **Step 2: Run the test and observe the expected failure**

  Run `python -m pytest tests/test_main_window_output_mixin.py::test_saxs_strain_summary_updates_results_review_hint_recorder -q`.
  Before the implementation, the existing temperature-only guard clears the hint
  and the assertion fails.

- [x] **Step 3: Implement the smallest guard extension**

  In `_update_results_review_hint`, accept `submodule_id == "saxs.strain"` in the
  same allowed set as `temperature` and `saxs.temperature`. Leave action routing,
  localized title/action, status, and non-SAXS clearing behavior unchanged.

- [x] **Step 4: Run the focused GUI tests**

  Run `python -m pytest tests/test_main_window_output_mixin.py -q`; expected result
  is all tests passing.

### Task 3: Verify and checkpoint the strain slice

**Files:**
- Include: `docs/superpowers/specs/2026-07-25-saxs-strain-other-panels-design.md`
- Include: `docs/superpowers/plans/2026-07-25-saxs-strain-other-panels.md`
- Include: `tests/test_saxs_publication_pack_upgrade.py`
- Include: `tests/test_main_window_output_mixin.py`
- Include: `polynexus/gui/main_window_output_mixin.py`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [x] **Step 1: Run focused verification**

  Run `python -m pytest tests/test_saxs_publication_pack_upgrade.py tests/test_main_window_output_mixin.py -q`.

- [x] **Step 2: Run lint, compile, and whitespace checks**

  Run `python -m ruff check polynexus/gui/main_window_output_mixin.py tests/test_saxs_publication_pack_upgrade.py tests/test_main_window_output_mixin.py`, `python -m compileall -q polynexus/gui/main_window_output_mixin.py tests/test_saxs_publication_pack_upgrade.py tests/test_main_window_output_mixin.py`, and `git diff --check`.

- [x] **Step 3: Run the repository verifier with the external pytest basetemp**

  Run `$env:PYTEST_ADDOPTS='--basetemp=C:\PolyNexus_saxs_verify_20260725_strain'; python scripts/verify.py --changed --types` and record the exact result. The strain slice uses the same verifier evidence as the temperature checkpoint: quality gate `282 passed`, preprocessing gate `103 passed`, exit code 0.

- [ ] **Step 4: Create the strain checkpoint**

  Run `python scripts/auto_commit.py --message "feat(saxs): route strain panel review hints" --files docs/superpowers/specs/2026-07-25-saxs-strain-other-panels-design.md docs/superpowers/plans/2026-07-25-saxs-strain-other-panels.md tests/test_saxs_publication_pack_upgrade.py tests/test_main_window_output_mixin.py polynexus/gui/main_window_output_mixin.py docs/agent/memory/active-work.md docs/agent/memory/current-state.md`.

- [ ] **Step 5: Record the checkpoint and next project**

  Update durable memory with the checkpoint hash and exact verification evidence;
  the next independent project is the static SAXS comparison/structure/
  correlation/diagnostic chain.
