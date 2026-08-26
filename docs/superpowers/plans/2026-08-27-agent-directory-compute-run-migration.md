# Agent directory ComputeRun migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route non-DSC Agent/Codex directory workflows through the shared ComputeRun producer.

**Architecture:** Keep DSC directory handling as a compatibility boundary. For other techniques, adapt either the default engine or custom provider runner to `ComputeRunService`, which attaches an opaque source-bound canonical envelope and preserves the provider result.

**Tech Stack:** Python, pytest, AgentWorkflowService, ComputeRunService, canonical converter registry.

---

### Task 1: Regression contract

**Files:**
- Create: `tests/test_agent_directory_compute_run.py`

- [x] **Step 1: Write failing tests for non-DSC shared projection and DSC fallback.**
- [x] **Step 2: Run `python -m pytest -q tests/test_agent_directory_compute_run.py`; the non-DSC projection assertion initially failed because `compute_run` was `None`.**

### Task 2: Shared directory adapter

**Files:**
- Modify: `polynexus/core/agent_workflow/service.py`

- [x] **Step 1: Route non-DSC directory artifacts through a one-call provider adapter and `ComputeRunService`.**
- [x] **Step 2: Leave DSC directories on the existing provider-only path.**
- [x] **Step 3: Run the focused tests and verify custom provider invocation count is one.**

### Task 3: Verification and checkpoint

**Files:**
- Modify: task card, memory
- Create: acceptance record

- [x] **Step 1: Run the Agent/project/ComputeRun matrix.**
- [x] **Step 2: Run the task-scoped structured verifier and `git diff --check`.**
- [ ] **Step 3: Create the explicit allowlisted checkpoint with `scripts/auto_commit.py`.**
