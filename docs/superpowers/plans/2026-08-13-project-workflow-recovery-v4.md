# Project Workflow Recovery V4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make persisted project runs recoverable and context corrections auditable.

**Architecture:** Keep recovery at the project service boundary. Reuse request/plan hash validation and existing provider execution; add only explicit correction metadata.

**Tech Stack:** Python, JSON-safe project contracts, pytest.

---

### Task 1: Recovery contracts

**Files:** `polynexus/core/project_workflow/service.py`, `tests/test_project_workflow_recovery.py`

- [ ] Write failing resume and correction tests.
- [ ] Implement manifest-backed resume and approved correction request creation.
- [ ] Run focused tests.

### Task 2: Provenance and acceptance

**Files:** `polynexus/core/project_workflow/package.py`, acceptance/memory files

- [ ] Include correction metadata in writing-input provenance.
- [ ] Record limitations and verification.
- [ ] Checkpoint the atomic task.
