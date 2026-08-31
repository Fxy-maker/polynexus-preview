---
task_id: 2026-08-31-ai-platform-trust-boundaries
kind: architecture
status: implementation_complete_review_required
date: 2026-08-31
title: Close planner admission and shared projection trust boundaries
---

# Close planner admission and shared projection trust boundaries

## Goal

Make the AI-first computation path fail closed: only Core-issued planner
admissions may execute known capabilities, shared `compute_run` projections
must be complete and internally consistent, and descriptor contracts must
control scientific gates and cache invalidation.

## Non-goals

- No new polymer algorithms or provider numerical changes.
- No removal of legacy read compatibility where the shared `compute_run` key is
  completely absent.
- No changes to raw datasets, generated evidence packages, or user files.

## Shared objects and entry points

- Objects: `CapabilityPlanItem`/planner admission, `ExecutionGraph`,
  `ComputeRun`, metric manifests, evidence items, provider-result input DTOs.
- AI/Codex/CLI: create or consume the same admission and projection contracts;
  no direct executor bypass.
- GUI: consume strict shared projections and reject contradictory persisted
  state before evidence/result presentation.
- Joint/evidence/ARS: use the same strict projection parser and retain legacy
  fallback only when `compute_run` is absent.

## Affected boundaries

- `polynexus/core/ai_platform`: planner admissions, descriptor validation,
  execution graph, cache identity, and provider-result input DTOs.
- `polynexus/core/compute`: strict shared `ComputeRun` projection parsing and
  public exports.
- `polynexus/core/agent_workflow`, `core/project_workflow`, `core/joint`, and
  `gui`: shared projection consumers; malformed or contradictory envelopes
  fail closed while truly absent envelopes retain legacy compatibility.
- `polynexus/cli` and canonical adapters: producer/consumer forwarding of the
  same public contracts, including NMR and N-D compatibility envelopes.
- Raw datasets, generated evidence packages, and user runtime artifacts remain
  outside this task.

## Implementation plan

1. Enforce content-addressed Core planner admission at the execution graph
   boundary and derive completion/cache state inside Core.
2. Centralize strict `ComputeRun` projection parsing and migrate Agent, project,
   Joint, GUI, evidence, result-table, package, and writing-metric consumers.
3. Extend descriptor gates and cache identity with calibration, axis
   provenance, units/quantities, shape, and dependency metadata; add the
   validated `ProviderResultInput`/metric-manifest DTO.
4. Add focused producer/consumer regression coverage, run the structured
   verifier, record evidence and limitations, and create an allowlisted local
   checkpoint.

## Acceptance criteria

- [x] A known descriptor cannot execute without a valid Core-issued admission
  binding capability/version, descriptor hash, selected DataBlock identity and
  successful planner gates.
- [x] Execution derives completion state conservatively and never inherits
  caller/cache publication promotion; failed or non-completed cache entries are
  misses.
- [x] Required calibration, axis, unit/quantity, shape and dependency metadata
  affect planning and cache identity where applicable.
- [x] A present `compute_run` key is parsed strictly: explicit completed status,
  valid four-axis state, and consistent aliases; malformed/non-completed data is
  rejected rather than sent through legacy extraction.
- [x] Legacy provider outputs use an explicit shared provider-result/metric
  manifest DTO with validated metric paths, instead of an impossible
  `DataBlock(kind="provider_result")`.
- [x] Focused producer/consumer regression tests, dependency-admission binding
  regressions, and task-scoped static gates pass. Existing user-created
  untracked files remain untouched.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_ai_platform_contracts.py tests/test_ai_platform_contract_hardening.py tests/test_ai_capability_planner.py tests/test_execution_graph.py tests/test_ai_platform_cross_entry.py tests/test_ai_platform_scientific_contracts.py tests/test_capability_execution.py tests/test_canonical_nd_adapters.py tests/test_compute_run_projection.py tests/test_project_workflow_package.py tests/test_project_writing_metrics.py tests/test_cli_run_ai_tune_service.py tests/test_main_window_persistence.py::test_restore_history_record_keeps_shared_compute_run_projection tests/test_main_window_persistence.py::test_restore_history_record_does_not_cache_malformed_shared_projection
python scripts/verify.py --task docs/agent/tasks/2026-08-31-ai-platform-trust-boundaries.md --changed --types
git diff --check
```

## Checkpoint allowlist

Use `scripts/auto_commit.py` with the exact changed source, test, task-card,
and plan files after verification. Do not include pre-existing untracked
artifacts.

## Completion evidence

- Exact commands and outcomes: refreshed trust-boundary matrix passed `329
  passed in 25.21s`; focused planner/graph additions passed; task-scoped Ruff,
  `py_compile`, and Pyright passed; quality/preprocessing gates passed
  `313`/`157`; `boundary_audit.py` and `git diff --check` passed. The current
  `verify.py --task ... --changed --types` run also passed all selected checks.
- Additional boundary coverage rejects flattened top-level metric-manifest
  mismatches, mapping-capable state subclasses, manually forged projection
  fields, noncanonical absent sentinels, and projection subclasses at merge.
- Dependency admissions now carry descriptor version/content hash and the
  dependency admission hash; execution rejects omitted dependency descriptors,
  missing dependency admissions, cross-registry dependency substitutions, and
  bindings that point at a different same-capability graph node. Multiple
  direct nodes for one declared capability are rejected as ambiguous.
- Known limitations or follow-up: scientific descriptor semantics, provider
  implementation coverage, and architecture review remain human-review items;
  provider numerical algorithms were not changed. The broad release boundary
  is not claimed green by this task.
- Pre-existing changes left untouched: `active_run.json`, `runs/`,
  `tests/_tmp_phase3/`, elastomer drafts/specs/plans, `li2020.txt`, and
  `lotz2021.txt`.
