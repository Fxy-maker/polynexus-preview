# SAXS temperature other panels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变科学算法和既有 figure 合同的前提下，锁定并打磨温变 SAXS 的 evolution、Avrami、selected evidence 板块边界。

**Architecture:** 以 `polynexus/core/saxs_engine/figure_temperature.py` 为温变 figure 排序和证据元数据来源，`figure_provider.py` 只负责既有 fallback 投影；GUI 继续消费 manifest/result presentation。本阶段优先补 provider 回归，只有发现消费层缺口才修改 GUI。

**Tech Stack:** Python、pytest、Ruff、`compileall`、仓库 `scripts/verify.py` 与 `scripts/auto_commit.py`。

---

### Task 1: Lock the temperature figure contract

**Files:**
- Create: `tests/test_saxs_temperature_figure_panels.py`
- Inspect: `polynexus/core/saxs_engine/figure_temperature.py`
- Inspect: `polynexus/core/saxs_engine/figure_provider.py`

- [x] **Step 1: Locate the provider and existing evidence fixtures**

  The provider entry is `build_temperature_figure_definitions` in
  `polynexus/core/saxs_engine/figure_temperature.py`; existing evidence-mode
  contract fixtures live in `tests/test_saxs_mode_evidence_contract.py`. The
  new focused test uses the same `SimpleNamespace`/`SAXSFrameView` style and
  does not invoke scientific analysis.

- [x] **Step 2: Write the contract tests before production edits**

  `test_temperature_panels_keep_publication_order_and_roles` asserts the
  eligible sequence is `evolution` order 10, `avrami` order 20, `waterfall`
  order 100, and selected evidence order 200 or later. It also asserts that
  waterfall remains `si`, evolution/Avrami remain `main`, and selected evidence
  is never promoted beyond `si`/`diagnostic`.

  `test_temperature_fallback_keeps_waterfall_and_adds_only_si_summary` uses the
  existing completed-result fallback path with two frames. It asserts no
  evolution or Avrami entry is fabricated, the temperature waterfall remains
  `si`, and the legacy parameter/heatmap summaries are added at orders 110/120
  as `si`.

- [x] **Step 3: Run the focused tests**

  Run `python -m pytest tests/test_saxs_temperature_figure_panels.py -q`.
  Result: `2 passed`.

- [x] **Step 4: Decide whether production changes are necessary**

  Both contracts pass against the existing provider, so no production change
  is justified in this stage. Keep the regression tests as the durable contract
  and do not alter scientific eligibility predicates, thresholds, IDs, columns,
  or publication roles.

### Task 2: Verify GUI/result consumption boundaries

**Files:**
- Inspect: `polynexus/gui/main_window_output_mixin.py`
- Inspect: `polynexus/gui/result_table_templates.py`
- Inspect: `polynexus/gui/widgets/results_table_panel.py`
- Verify existing regressions: `tests/test_main_window_output_mixin.py`,
  `tests/test_analysis_result_table_templates.py`

- [x] **Step 1: Confirm existing temperature review-hint coverage**

  `tests/test_main_window_output_mixin.py` already verifies that the temperature
  summary/risk/next-step values are passed to the results panel and that a
  non-temperature technique clears the temperature hint. No new scientific
  branching is needed in the GUI.

- [x] **Step 2: Confirm existing temperature result-table fields**

  `tests/test_analysis_result_table_templates.py` already verifies the static,
  temperature, and isothermal table templates, including temperature condition
  and Avrami fields. Keep the existing hero/primary/detail/diagnostic tabs and
  do not add technique-specific figure computation there.

- [x] **Step 3: Run the consumer regressions**

  Run `python -m pytest tests/test_main_window_output_mixin.py tests/test_analysis_result_table_templates.py -q`.

### Task 3: Verify and checkpoint the temperature slice

**Files:**
- Include: `docs/agent/tasks/2026-07-25-saxs-other-modules-polish.md`
- Include: `docs/superpowers/specs/2026-07-25-saxs-temperature-other-panels-design.md`
- Include: `docs/superpowers/plans/2026-07-25-saxs-temperature-other-panels.md`
- Include: `tests/test_saxs_temperature_figure_panels.py`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md` only if the durable current-state summary changes

- [x] **Step 1: Run focused verification**

  Run `python -m pytest tests/test_saxs_temperature_figure_panels.py tests/test_main_window_output_mixin.py tests/test_analysis_result_table_templates.py -q`.

- [x] **Step 2: Run syntax, lint, and diff checks**

  Run `python -m ruff check tests/test_saxs_temperature_figure_panels.py`,
  `python -m compileall -q tests/test_saxs_temperature_figure_panels.py`, and
  `git diff --check`.

- [x] **Step 3: Run the repository verifier**

  Run `python scripts/verify.py --changed --types` and record the exact exit code
  and summary. The first run reproduced the pre-existing Windows lock on
  `.pytest_tmp`; the prescribed command then passed with
  `PYTEST_ADDOPTS=--basetemp=C:\PolyNexus_saxs_verify_20260725`: quality gate
  `282 passed`, preprocessing gate `103 passed`, exit code 0.

- [x] **Step 4: Review the scoped diff**

  Run `git diff --stat`, `git diff -- docs/agent/tasks/2026-07-25-saxs-other-modules-polish.md docs/superpowers/specs/2026-07-25-saxs-temperature-other-panels-design.md docs/superpowers/plans/2026-07-25-saxs-temperature-other-panels.md tests/test_saxs_temperature_figure_panels.py`, and `git status --short`. Confirm no existing Origin/editor scratch path is included.

- [x] **Step 5: Create the atomic checkpoint**

  After verification, run `python scripts/auto_commit.py --message "test(saxs): lock temperature figure panel contracts" --files docs/agent/tasks/2026-07-25-saxs-other-modules-polish.md docs/superpowers/specs/2026-07-25-saxs-temperature-other-panels-design.md docs/superpowers/plans/2026-07-25-saxs-temperature-other-panels.md tests/test_saxs_temperature_figure_panels.py docs/agent/memory/active-work.md`.

- [x] **Step 6: Update durable memory**

  Record the exact verification results and the fact that this temperature
  slice required regression coverage but no production algorithm change. The
  next independent sub-project is strain SAXS panel ordering; the checkpoint
  hash is added after the atomic commit.
