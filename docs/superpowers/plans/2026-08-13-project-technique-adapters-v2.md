# Project Technique Adapters V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Route one real indexed IR, WAXS, or SAXS artifact through existing engines and emit bounded ARS evidence.

**Architecture:** Add a small registered adapter that creates one recipe step per supported technique. Keep project planning and packaging generic; reuse `AgentWorkflowService` for validation, execution, and receipts.

**Tech Stack:** Python dataclasses, existing agent-workflow contracts, existing technique engines, pytest.

---

### Task 1: Registered Single-Input Adapter

**Files:**
- Create: `polynexus/core/project_workflow/adapters.py`
- Modify: `polynexus/core/project_workflow/service.py`
- Test: `tests/test_project_workflow_adapters.py`

- [ ] Add tests for recipe proposal, unsupported technique blocking, and multiple artifacts blocking.
- [ ] Implement adapter workflow id `project.technique.single.v1` for `ir`, `waxs`, and `saxs`.
- [ ] Register it in `ProjectWorkflowService` and use it for non-DSC plans.
- [ ] Run focused adapter/service tests and checkpoint.

### Task 2: Project Run Generalization

**Files:**
- Modify: `polynexus/core/project_workflow/service.py`
- Modify: `polynexus/core/project_workflow/evidence.py`
- Test: `tests/test_project_workflow_service.py`

- [ ] Build manifests from the selected technique step instead of assuming DSC.
- [ ] Preserve source, recipe, provider, and evidence limitations for all three techniques.
- [ ] Keep DSC behavior unchanged and reject mixed/multiple inputs explicitly.
- [ ] Run the complete project workflow matrix.

### Task 3: Real Read-Only Replay

**Files:**
- Create: `docs/acceptance/2026-08-13-project-technique-adapters-v2.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Replay one PA6 SAXS/WAXS/FTIR input through an external raw junction.
- [ ] Record exact status, source hash, output location, and review limitations.
- [ ] Run structured verification and commit the acceptance record.
