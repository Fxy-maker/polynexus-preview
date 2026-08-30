# Current evidence workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended) to implement this plan task-by-task.

**Goal:** Add append/replace working evidence state and explicit package freeze.

**Architecture:** Persist a compact source-keyed index under `.polynexus/evidence/working.json`; resolve validated run manifests only at freeze time and delegate package creation to the existing packager.

**Tech Stack:** Python dataclasses, JSON, existing project workflow and pytest.

---

### Task 1: Working index model

**Files:**
- Create: `polynexus/core/project_workflow/working_evidence.py`
- Test: `tests/test_project_evidence_workspace.py`

- [ ] Define JSON-safe `WorkingEvidenceEntry` and `WorkingEvidenceStatus` values.
- [ ] Implement source-artifact keyed upsert, removal, and deterministic status counts.
- [ ] Persist atomically through `ProjectWorkspace.write_json`.

### Task 2: Service integration and freeze

**Files:**
- Modify: `polynexus/core/project_workflow/service.py`
- Modify: `polynexus/core/project_workflow/__init__.py`
- Test: `tests/test_project_evidence_workspace.py`

- [ ] Add service methods to upsert a validated run, read status, and freeze current entries.
- [ ] Load each referenced run manifest into `ProjectWorkflowRun`, validate it via existing packager checks, and call `package()` once.
- [ ] Keep old package APIs unchanged.

### Task 3: Verification

- [ ] Run focused tests, task verifier, and diff check.
- [ ] Confirm existing package view still loads.
