# Project Technique Series V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute one same-technique multi-file project sequence and package its bounded evidence.

**Architecture:** A registered series adapter creates one indexed provider step per artifact. Agent workflow execution resolves steps by `artifact_index`; project packaging adds explicit run/request relations.

**Tech Stack:** Python dataclasses, existing workflow contracts, pytest.

---

### Task 1: Series recipe adapter

**Files:** `polynexus/core/project_workflow/adapters.py`, `tests/test_project_workflow_adapters.py`

- [ ] Add failing tests for deterministic ordering, mixed/one-file blocking, and recipe validation.
- [ ] Implement `project.technique.series.v1` for IR/WAXS/SAXS.
- [ ] Run the adapter tests.

### Task 2: Project plan and execution binding

**Files:** `polynexus/core/project_workflow/service.py`, `polynexus/core/agent_workflow/service.py`, `tests/test_project_workflow_service.py`

- [ ] Select the series adapter for same-technique scopes with multiple artifacts.
- [ ] Persist ordered paths and source hashes in the plan.
- [ ] Bind each provider step to its indexed artifact and fail closed on stale sources.
- [ ] Run the project workflow matrix.

### Task 3: ARS relations and acceptance

**Files:** `polynexus/core/project_workflow/package.py`, `tests/test_project_workflow_package.py`, acceptance/memory files

- [ ] Emit conservative same-request relations when packaging multiple runs.
- [ ] Add focused package tests and PA6 read-only smoke evidence.
- [ ] Run structured verification and checkpoint the atomic task.
