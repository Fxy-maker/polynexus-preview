# Shared ComputeRun Canonical Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Carry generic IR/SAXS/WAXS canonical templates and finite capability items through the shared `ComputeRunService` used by Quick Analysis and single-file CLI.

**Architecture:** The service performs source-bound generic conversion before the legacy provider. Generic-ready templates contribute immutable capability items to one `ComputeRun`; ambiguous mappings stop with `needs_input`; vendor formats remain compatibility inputs. Existing providers and consumers are otherwise unchanged.

**Tech Stack:** Python dataclasses, existing canonical registry/capability executor, pytest.

---

### Task 1: Add failing shared-contract tests

**Files:** `tests/test_compute_models.py`, `tests/test_compute_service.py`, `tests/test_cli_run_single_service.py`, `tests/test_main_window_workers.py`

- [x] Test canonical template serialization and source binding.
- [x] Test generic-ready, ambiguous, vendor fallback, and provider-failure routing.
- [x] Test CLI JSON and Quick Analysis worker expose identical fields.

### Task 2: Implement shared routing

**Files:** `polynexus/core/compute/models.py`, `polynexus/core/compute/service.py`

- [x] Add optional validated `canonical_template` to `ComputeRun`.
- [x] Convert generic table inputs before provider execution.
- [x] Attach finite capability results and preserve them on provider failure.

### Task 3: Verify and checkpoint

- [x] Run focused consumers and structured verification.
- [x] Update task/memory records and create an allowlisted local checkpoint.
