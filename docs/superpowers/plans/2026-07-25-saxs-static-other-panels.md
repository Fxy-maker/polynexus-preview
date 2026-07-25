# SAXS static other panels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 锁定静态 SAXS 的 comparison/sample、support/profile 和 per-frame diagnostic 顺序与 publication role。

**Architecture:** 复用现有 static provider 与统一 figure lifecycle；本阶段只增加 provider 回归，不修改科学算法和 GUI。

**Tech Stack:** Python、pytest、Ruff、`compileall`、`scripts/verify.py`、`scripts/auto_commit.py`。

---

### Task 1: Lock static figure order and fallback roles

**Files:**
- Modify: `tests/test_saxs_publication_pack_upgrade.py`
- Inspect: `polynexus/core/saxs_engine/figure_static.py`

- [x] **Step 1: Reuse `_static_engine` with two analyzed samples**

  Keep the existing fixture data and emitted correlation evidence; call
  `build_static_saxs_figure_definitions(_static_engine())`.

- [x] **Step 2: Add the order/role regression**

  Assert the first IDs are `saxs.static.comparison`, then
  `saxs.static.correlation.support`; assert orders are `[10, 20, 100, 104, 114]` for
  the fixture, roles are `main`, `si`, and `diagnostic` for all per-frame entries,
  and no correlation/frame diagnostic entry is `main`.

- [x] **Step 3: Run the static regression**

  Run `python -m pytest tests/test_saxs_publication_pack_upgrade.py::test_static_pack_orders_main_support_and_diagnostics -q`.

### Task 2: Verify and checkpoint the static slice

**Files:**
- Include: `docs/superpowers/specs/2026-07-25-saxs-static-other-panels-design.md`
- Include: `docs/superpowers/plans/2026-07-25-saxs-static-other-panels.md`
- Include: `tests/test_saxs_publication_pack_upgrade.py`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [x] **Step 1: Run focused static verification**

  Run `python -m pytest tests/test_saxs_publication_pack_upgrade.py -q`.

- [x] **Step 2: Run lint, compile, and whitespace checks**

  Run `python -m ruff check tests/test_saxs_publication_pack_upgrade.py`, `python -m compileall -q tests/test_saxs_publication_pack_upgrade.py`, and `git diff --check`.

- [x] **Step 3: Run the repository verifier with external pytest basetemp**

  Run `$env:PYTEST_ADDOPTS='--basetemp=C:\PolyNexus_saxs_verify_20260725_static'; python scripts/verify.py --changed --types` and record the exact result. The static slice uses quality gate `282 passed`, preprocessing gate `103 passed`, and exit code 0.

- [ ] **Step 4: Create the static checkpoint**

  Run `python scripts/auto_commit.py --message "test(saxs): lock static figure panel contracts" --files docs/superpowers/specs/2026-07-25-saxs-static-other-panels-design.md docs/superpowers/plans/2026-07-25-saxs-static-other-panels.md tests/test_saxs_publication_pack_upgrade.py docs/agent/memory/active-work.md docs/agent/memory/current-state.md`.
