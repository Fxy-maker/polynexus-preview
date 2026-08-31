---
task_id: 2026-08-31-ai-platform-trust-boundaries
date: 2026-08-31
status: implementation_complete_review_required
---

# AI platform trust-boundary repair

## Outcome

The AI-first computation path now fails closed at the shared Core boundary.
Known capability nodes require a content-addressed planner admission bound to
the descriptor, selected input, and successful gates. Execution derives its
own completion state and treats failed, blocked, non-computed, or promoted-only
cache entries as misses. Descriptor calibration, axis provenance, units,
quantities, shape, and dependencies participate in planning and cache identity.

All consumers use the strict shared `ComputeRun` projection parser. Whenever a
`compute_run` key is present, it must be a complete, internally consistent,
completed/computed four-axis envelope; malformed, contradictory, or explicit
null envelopes fail closed. Legacy extraction remains available only when the
key is genuinely absent. Provider metrics cross the boundary through the
validated `ProviderResultInput` and metric-manifest DTO rather than an
invented `DataBlock` kind.

## Changed boundaries

- Core AI platform contracts, descriptor catalog, planner, execution graph,
  cache identity, and provider-result DTO.
- Core ComputeRun projection and service exports.
- Agent workflow, project workflow, Joint, GUI, CLI, canonical adapters, and
  evidence/result/ARS projections migrated to the shared parser/contracts.
- Focused regression tests for admission forgery/mismatch, cache promotion,
  strict projection aliases/nulls, scientific descriptor gates, NMR/N-D
  compatibility envelopes, and provider metric paths.
- Planner-issued target admissions now retain content-addressed dependency
  bindings (capability ID, descriptor version/hash, and dependency admission
  hash). Execution requires the same runtime registry and a trusted admission
  for every declared dependency, so omitted or substituted dependency
  descriptors fail closed instead of using the opaque legacy path. Runtime
  validation uses the target's direct graph edge, not another node with the
  same capability ID, and rejects multiple direct nodes for one declared
  capability as ambiguous.

No provider numerical algorithm, raw dataset, generated evidence package, or
user runtime artifact was changed.

## Verification evidence

- The refreshed producer/consumer matrix (including scientific-contract,
  capability-execution, strict-projection, merge-boundary, and dependency
  binding regressions) passed **329 tests in 25.21s**:

  `python -m pytest -p no:cacheprovider -q tests/test_ai_platform_contracts.py tests/test_ai_platform_contract_hardening.py tests/test_ai_capability_planner.py tests/test_execution_graph.py tests/test_ai_platform_cross_entry.py tests/test_ai_platform_scientific_contracts.py tests/test_capability_execution.py tests/test_canonical_nd_adapters.py tests/test_compute_run_projection.py tests/test_project_workflow_package.py tests/test_project_writing_metrics.py tests/test_cli_run_ai_tune_service.py tests/test_main_window_persistence.py::test_restore_history_record_keeps_shared_compute_run_projection tests/test_main_window_persistence.py::test_restore_history_record_does_not_cache_malformed_shared_projection`
- Task-scoped `ruff check` and `python -m py_compile` passed; `pyright -p
  pyrightconfig.json` reported **0 errors, 0 warnings**.
- `python scripts/quality_gate.py --root D:\PolyNexus` — focused quality
  **313 passed**, preprocessing **157 passed**, and whitespace passed.
- `python scripts/verify.py --task docs/agent/tasks/2026-08-31-ai-platform-trust-boundaries.md --changed --types`
  passed all selected checks in the current worktree.
- `git diff --check` — passed.

Known-descriptor cache entries now require the exact Core `NodeResult` DTO
(not a subclass), complete Core provenance, and an output fingerprint matching
the canonical output. Cache-hit provenance is a strict boolean observation, so
a previously cached result can be safely reinserted without forcing execution.
The built-in descriptor catalog is authoritative: custom registries are
additive and a catalog failure fails closed instead of downgrading a known ID
to an opaque plugin path.

## Review boundaries and limitations

This is an implementation checkpoint, not scientific or release approval.
Descriptor semantics, calibration content and scope, provider coverage for
DMA/rheology/TGA/DTG/SEC/GPC/mechanics, publication promotion, and the broad
historical GUI/provider failure ledger still require human review. Existing
legacy compatibility paths remain intentionally available only for truly
absent shared envelopes.

The strict parser also validates flattened top-level `metrics`/manifest
aliases, rejects polymorphic `ComputationState` and projection DTOs, and the
merge helper re-parses and compares every present projection field before it
can be considered computed.

Calibration identity mappings are intentionally scalar: nested sequences such
as `{"scope": ["q"]}` are rejected at descriptor construction rather than
being stringified into an unmatchable planner identity.

## Preserved pre-existing workspace state

The following user-created or unrelated paths were intentionally left out of
the checkpoint: `active_run.json`, `runs/`, `tests/_tmp_phase3/`, elastomer
draft/spec/plan files, `li2020.txt`, and `lotz2021.txt`.
