# Flexible AI Analysis Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Converge the existing quick-analysis UI and project evidence route around one replayable `AnalysisPlan` contract with a real PA6 four-technique handoff.

**Architecture:** Keep existing deterministic providers and public project workflow services. Add a shared plan/provenance layer below GUI and CLI, then expose bounded adaptive diagnostics and candidate comparison through DTOs. Migrate navigation and legacy tools incrementally; defer destructive module removal until usage and replacement tests exist.

**Tech Stack:** Python, PySide6, existing project-workflow services, JSON manifests, SHA-256 provenance, pytest, `scripts/verify.py`.

---

### Task 1: Quick Analysis entry convergence

**Files:**
- Modify: `polynexus/gui/main_window_navigation_mixin.py`
- Modify: `polynexus/gui/main_window_workspace_mixin.py`
- Modify: `polynexus/gui/main_window.py`
- Test: `tests/test_gui_route.py` or the focused existing navigation test module

- [ ] Write a failing route test asserting Quick Analysis is the first human-facing action, while project/evidence and advanced tools remain reachable.
- [ ] Run the focused route test and observe the expected old-order failure.
- [ ] Reorder/label only the navigation and entry wiring; preserve automatic-detection popup, folder chooser, batch selection, NMR route, chart editor, and Origin export callbacks.
- [ ] Run the route test plus existing quick-analysis smoke tests; verify no provider code changed.
- [ ] Create an allowlisted checkpoint for the GUI-only change.

### Task 2: `AnalysisPlan` schema and validation

**Files:**
- Create or extend: the existing core workflow contract module selected by the project service
- Modify: `polynexus/core/project_workflow/service.py` and manifest serializers
- Test: focused project workflow/provenance tests

- [ ] Write failing tests for required source hashes, template/conversion versions, algorithm/config versions, protected metrics, approval state, and AI hash fields.
- [ ] Run them and confirm missing/invalid fields are rejected before provider execution.
- [ ] Implement a versioned DTO/serializer using existing manifest conventions; normalize paths and stable JSON before hashing.
- [ ] Verify quick GUI requests, project CLI requests, and ARS requests can all produce the same plan representation.
- [ ] Checkpoint only the contract, serializer, and focused tests.

### Task 3: Frozen replay and immutable replans

**Files:**
- Modify: project workflow resume/replay service and run lineage persistence
- Test: recovery/replay matrix

- [ ] Add failing tests proving a frozen plan replays with no AI provider call and changed source/template/algorithm hashes fail closed.
- [ ] Add a failing test proving a new AI decision creates `replan_of` lineage and leaves the prior evidence snapshot unchanged.
- [ ] Implement replay from the persisted plan manifest and explicit replan creation.
- [ ] Run focused recovery, package, and hash-validation tests.
- [ ] Checkpoint replay behavior and evidence.

### Task 4: Adaptive diagnostics and bounded candidate evaluation

**Files:**
- Create/modify: core analysis-plan evaluation service near existing orchestrator services
- Modify: `polynexus/orchestrator*.py` compatibility adapters
- Test: focused candidate legality, stability, and deterministic-score tests

- [ ] Write failing tests for symptoms (baseline drift, peak instability, noisy frames, discontinuity) and finite legal candidates.
- [ ] Run tests to observe failure before implementation.
- [ ] Implement AI-facing symptom classification as a request/response DTO; implement deterministic candidate generation and metrics for retention, shifts, continuity, constraints, uncertainty, and cost.
- [ ] Reject arbitrary AI numeric configs and single-score acceptance; preserve all candidate reasons and protected metrics.
- [ ] Keep `ai-tune` as a compatibility wrapper that emits the new plan/evaluation representation.
- [ ] Run focused provider/orchestrator tests and checkpoint.

### Task 5: Shared GUI/CLI/ARS plan and evaluation views

**Files:**
- Modify: CLI parser/service and GUI AI-tuning/result DTO adapters
- Test: CLI JSON, GUI view-model, and ARS handoff consumer tests

- [ ] Write failing consumer tests asserting identical plan IDs, candidate statuses, review limits, and replay metadata across GUI, CLI, and ARS JSON.
- [ ] Implement technique-neutral DTO projections; GUI renders summaries and review actions without technique-private branching.
- [ ] Add explicit labels for analysis suggestions, robustness checks, and comparison; keep advanced details contextual.
- [ ] Run all affected producer/consumer tests and checkpoint.

### Task 6: Simplify Sample Hub and attach quick runs

**Files:**
- Modify: Sample Hub navigation/model adapter and quick-run attachment service
- Test: sample metadata/history and attach-to-project tests

- [ ] Write failing tests proving a quick run can remain standalone or be attached to a project without duplicate analysis/provenance objects.
- [ ] Implement contextual metadata/history access and remove any database-first requirement from the quick path.
- [ ] Run focused GUI/data tests and checkpoint.

### Task 7: Contextualize Joint, convergence, and plan evaluation

**Files:**
- Modify: Joint/convergence/plan-evaluation navigation and DTO summaries
- Test: route visibility and shared-run linkage tests

- [ ] Write failing tests for contextual visibility from a selected run/project and for AI/GUI use of the same relation/evaluation records.
- [ ] Implement summary-first GUI surfaces with detail views reachable from a run; preserve existing exports and persistence.
- [ ] Run focused route/history/export tests and checkpoint.

### Task 8: RAG dependency assessment

**Files:**
- Inspect/modify: `rag/`, adviser configuration, dependency manifests, and docs
- Test: optional-disabled startup and deterministic reference-table tests

- [ ] Write failing tests for startup and analysis when vector retrieval is disabled, while polymer reference tables remain available.
- [ ] Measure storage/startup impact and enumerate consumers before changing dependency defaults.
- [ ] Make RAG optional or document a retained bounded use only after Task 4 replacement tests pass; do not delete it in the same checkpoint as unrelated GUI work.
- [ ] Run focused optional-dependency tests and checkpoint with explicit findings.

### Task 9: Real PA6 four-technique replay and ARS handoff

**Files:**
- Modify only workflow/test harness/docs needed for the replay
- Test: read-only PA6 acceptance matrix using the existing external dataset junction

- [ ] Write the acceptance fixture/test for selected PA6 groups and explicit DSC/FTIR/SAXS/WAXS membership.
- [ ] Run the test against the real read-only project paths; confirm no raw data is copied or modified.
- [ ] Verify figures, tables, citation metrics, evidence limits, human-review actions, and `ars-writing-input` all link to source/run hashes.
- [ ] Record Results candidates versus Discussion-only diagnostics and known provider limitations.
- [ ] Create the final allowlisted acceptance checkpoint; leave full repository historical failures clearly documented.

## Plan self-review

- Every design requirement maps to a task: quick default (1), plan/replay (2-3), adaptive AI (4), shared consumers (5), module simplification (6-8), PA6 proof (9).
- The only accepted plan type name is `AnalysisPlan`; replan lineage is `replan_of`; no task uses the retired “Project Workbench default” wording.
- No placeholders or unbounded “handle edge cases” steps remain; each task names files, tests, failure expectation, implementation, and checkpoint.
