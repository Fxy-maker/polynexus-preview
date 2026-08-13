# AI Project Candidate Groups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let AI/ARS choose one meaningful data group instead of running a mixed directory.

**Architecture:** A project-workflow helper derives immutable candidate groups from indexed artifact paths. The existing unified entrypoint either receives explicit scope, selects one question-matched group, or returns candidates without executing a provider.

**Tech Stack:** Python dataclasses, regex, existing project workflow, pytest.

---

### Task 1: Candidate group contract

**Files:**
- Modify: `polynexus/core/project_workflow/evidence.py`
- Create: `polynexus/core/project_workflow/grouping.py`
- Test: `tests/test_ai_project_candidate_groups.py`

- [x] Write a failing test for JW/SW temperature and 250 C time candidate extraction.
- [x] Add JSON-safe group contract with `inferred_from_filename` status.
- [x] Add deterministic grouping helper and run the focused test.

### Task 2: AI entrypoint selection

**Files:**
- Modify: `polynexus/core/project_workflow/service.py`
- Modify: `polynexus/core/project_workflow/evidence.py`
- Test: `tests/test_ai_project_candidate_groups.py`

- [x] Write failing tests for matching question selection and ambiguous no-run behavior.
- [x] Select only one matching group; otherwise return a bounded selection message.
- [x] Run service-focused tests.

### Task 3: Acceptance

**Files:**
- Create: `docs/acceptance/2026-08-14-ai-project-candidate-groups.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] Run project workflow and structured verification.
- [x] Record filename-inference limits and checkpoint.
