# AI Platform Trust-Boundary Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make planner admission, strict shared-run parsing, scientific descriptor gates, cache invalidation, and provider-result inputs fail closed across AI/CLI/GUI/evidence consumers.

**Architecture:** Add a content-addressed planner admission to the existing capability plan item and require it at the execution graph boundary. Centralize parsing of any present `compute_run` projection and route all affected consumers through that parser. Extend existing descriptors and contracts rather than adding a second result model.

**Tech Stack:** Python dataclasses, existing JSON/hash helpers, pytest, Ruff, and the repository verifier.

---

### Task 1: Planner admission and execution enforcement

**Files:**
- Modify: `polynexus/core/ai_platform/planner.py`
- Modify: `polynexus/core/ai_platform/execution.py`
- Modify: `polynexus/core/compute/service.py`
- Test: `tests/test_ai_capability_planner.py`
- Test: `tests/test_execution_graph.py`

- [x] Write RED tests for missing/forged admission, descriptor hash/version/DataBlock mismatch, conservative execution state, and failed-cache rejection.
- [x] Run the focused tests and confirm they fail for the intended bypass behavior.
- [x] Add an immutable content-hashed admission payload to executable plan items; validate it in `ExecutionGraph.execute()` before any known descriptor executor call.
- [x] Bind each declared dependency in the target admission to its descriptor
  version/content hash and dependency admission hash; require the same
  descriptor registry and admission at execution.
- [x] Resolve the binding against the target's unique direct dependency node;
  reject same-capability node substitution and ambiguous duplicate direct
  nodes.
- [x] Resolve the descriptor before calculating the node key; derive calibration sensitivity from required calibrations/preconditions and include admission/DataBlock/calibration identity in the key.
- [x] Rebuild completion state from Core-controlled defaults and only accept cache entries with matching identity and completed/computed state; never inherit cache promotion.
- [x] Run planner and graph matrices, then inspect cross-entry adapter behavior.

### Task 2: Strict shared ComputeRun projection parser

**Files:**
- Modify: `polynexus/core/compute/models.py`
- Modify: `polynexus/core/agent_workflow/evidence.py`
- Modify: `polynexus/core/agent_workflow/models.py`
- Modify: `polynexus/core/project_workflow/evidence.py`
- Modify: `polynexus/core/project_workflow/writing_metrics.py`
- Modify: `polynexus/core/project_workflow/result_table.py`
- Modify: `polynexus/core/project_workflow/package.py`
- Modify: `polynexus/core/joint/dataset.py`
- Modify: `polynexus/gui/analysis_run_service.py`
- Test: `tests/test_ai_platform_cross_entry.py`
- Test: `tests/test_project_workflow_package.py`
- Test: `tests/test_project_writing_metrics.py`

- [x] Write RED tests showing that present nested/direct `compute_run` projections with needs-input, malformed state, or contradictory aliases are excluded/rejected, while absent keys retain explicit legacy compatibility.
- [x] Run the tests and confirm the old fail-open behavior.
- [x] Implement one strict parser returning a validated projection or a fail-closed result; enforce completed + computed for evidence and results-candidate promotion separately.
- [x] Replace consumer-specific fallback logic with the parser and reject direct-vs-summary descriptor/provenance/uncertainty divergence.
- [x] Run the producer/consumer matrix and verify GUI, Joint, package and ARS projections use the same outcome.

### Task 3: Scientific descriptor contracts and provider-result DTO

**Files:**
- Modify: `polynexus/core/ai_platform/contracts.py`
- Modify: `polynexus/core/ai_platform/capabilities.py`
- Modify: `polynexus/core/ai_platform/planner.py`
- Modify: `polynexus/core/canonical_experiments/nd_adapters.py`
- Modify: `polynexus/core/canonical_experiments/registry.py`
- Test: `tests/test_ai_platform_contracts.py`
- Test: `tests/test_ai_capability_planner.py`
- Test: `tests/test_canonical_nd_adapters.py`

- [x] Write RED tests for invalid axis units/quantities, non-monotonic or duplicate physical axes, unreviewed unbound calibration, missing NMR physical axes, and provider-result metric-path mismatch.
- [x] Run the tests and confirm the scientific semantics are currently accepted.
- [x] Add machine-checkable descriptor input constraints and enforce them in planner gates; make calibration review/scope/locator requirements explicit for quantitative capabilities.
- [x] Define and validate a formal provider-result/metric-manifest input DTO and adapt legacy descriptors to it without inventing DataBlock kinds or values.
- [x] Fix registry IR provenance forwarding and NMR `fid`/`ser`/empty-directory routing as compatibility-envelope states, then run canonical matrices.

### Task 4: Verification, durable state and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-08-31-ai-platform-trust-boundaries.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/acceptance/2026-08-31-ai-platform-trust-boundaries.md`

- [x] Run the complete focused trust-boundary matrix and the task verifier.
  The refreshed matrix passed 329 tests; the current task-scoped
  `--changed --types` verifier passed all selected checks.
- [x] Run `git diff --check` and review the cumulative diff against the task scope.
- [x] Record exact pass/fail counts, known limitations, human-review requirements, and untouched pre-existing files.
- [x] Create one allowlisted local checkpoint with `python scripts/auto_commit.py`; do not push, merge, deploy, or include user artifacts.
