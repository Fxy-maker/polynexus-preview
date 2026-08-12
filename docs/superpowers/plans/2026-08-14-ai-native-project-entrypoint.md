# AI-Native Project Entrypoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one simple project-directory call produce bounded analysis evidence for AI/ARS.

**Architecture:** Add a thin service facade over the existing inspect/plan/run/package contracts and a CLI operation that serializes its summary. Keep raw provider state and fail-closed reasons available in the response.

**Tech Stack:** Python dataclasses, existing project workflow service, argparse, pytest.

---

### Task 1: Summary contract and service facade

**Files:**
- Modify: `polynexus/core/project_workflow/service.py`
- Modify: `polynexus/core/project_workflow/__init__.py`
- Test: `tests/test_ai_native_project_entrypoint.py`

- [ ] Write failing tests for auto-discovery, package output, and three status fields.
- [ ] Implement JSON-safe summary and orchestration over existing routes.
- [ ] Run the focused service tests.

### Task 2: CLI entrypoint

**Files:**
- Modify: `polynexus/cli/parser.py`
- Modify: `polynexus/cli/run_project_workflow_service.py`
- Test: `tests/test_ai_native_project_entrypoint.py`, `tests/test_project_workflow_cli.py`

- [ ] Add `project-workflow analyze-project` with only project root/question/package id options.
- [ ] Emit exactly one machine-readable envelope with user-facing status projection.
- [ ] Run CLI focused tests.

### Task 3: Acceptance checkpoint

**Files:**
- Create: `docs/acceptance/2026-08-14-ai-native-project-entrypoint.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Run structured verification and diff checks.
- [ ] Record known scientific review limitations and commit the task.
