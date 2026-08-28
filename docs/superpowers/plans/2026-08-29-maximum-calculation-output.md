# Maximum Calculation Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose all deterministic result fields and explicit condition-scoped group tables through shared contracts, then validate them on six real samples.

**Architecture:** Add a technique-neutral result-field inventory/projection beside existing `ComputeRun` and evidence DTOs. Provider values remain authoritative; the projection records values or explicit unavailable states with source/method/quality metadata. Group statistics are a separate view over caller-selected rows and never replace the per-file rows.

**Tech Stack:** Python dataclasses/DTOs, existing project workflow contracts, CSV/JSON exports, pytest.

---

### Task 1: Inventory and coverage contract

**Files:**
- Create: `docs/acceptance/2026-08-29-maximum-calculation-output.md`
- Create: `tests/test_result_field_inventory.py`
- Inspect: `polynexus/core/submodule_registry.py`, `polynexus/core/compute/models.py`, provider result projections

- [x] Write a failing contract test requiring each technique to expose a field inventory with field id, unit policy, source locator, and status policy.
- [x] Implement the smallest shared inventory DTO/registry without changing provider algorithms.
- [x] Add provider field mappings for current public result parameters, including fields that may be diagnostic-only.
- [x] Verify the contract and record missing/unexposed provider fields in the acceptance report.

### Task 2: Per-file and condition-scoped group table

**Files:**
- Create or modify the existing project-workflow result table service identified in Task 1
- Create: `tests/test_group_result_table.py`

- [x] Write tests for one row per source result, explicit condition keys, finite values, and unavailable reason codes.
- [x] Implement a technique-neutral table DTO and deterministic statistics (count, mean, standard deviation, CV) over explicitly selected same-condition rows.
- [x] Ensure the aggregate retains row ids/source files and refuses mixed condition keys.
- [x] Add JSON/CSV serialization through the existing shared consumer boundary.

### Task 3: Six-sample real replay

**Files:**
- Create: `docs/acceptance/2026-08-29-six-sample-maximum-output.md`
- Modify: `docs/agent/tasks/2026-08-29-maximum-calculation-output.md`

- [x] Inspect the existing six-sample persisted replay against the user-provided project data without modifying raw inputs.
- [x] Compare persisted completed, unavailable, and failed field coverage for DSC/FTIR/SAXS/WAXS; record that NMR is not present in this replay.
- [x] Record the existing failed/blocked statuses as follow-up findings; no scientific gate was relaxed during replay.

### Task 4: Verification and checkpoint

- [ ] Run focused tests, `python scripts/verify.py --task docs/agent/tasks/2026-08-29-maximum-calculation-output.md --changed --types`, and `git diff --check`.
- [ ] Update `docs/agent/memory/active-work.md` with durable coverage findings.
- [ ] Commit only the explicit task allowlist with `scripts/auto_commit.py`.
