---
task_id: 2026-08-26-capability-execution
kind: architecture
status: implementation_complete_review_required
date: 2026-08-26
title: Add finite canonical capability execution
---

# Add finite canonical capability execution

## Goal

Run a closed set of deterministic capability items against canonical 1-D
measurements and persist the item results on the shared `ComputeRun` object.

## Non-goals

- No changes to existing DSC/IR/SAXS/WAXS/NMR provider algorithms.
- No GUI, CLI, Batch, Codex migration in this atomic task.
- No manuscript role, evidence package, or scientific conclusion assignment.

## Shared objects and entry points

- Objects: canonical experiment, capability item result, compute run.
- AI/Codex/CLI: unchanged in this slice; future consumers read `ComputeRun`.
- GUI: unchanged in this slice; future view models read the same tuple.
- Cross-entry rule: the registry/executor is the sole producer; no entry point
  parses or recomputes these item results.

## Affected boundaries

- `polynexus.core.canonical_experiments`: closed capability declarations and
  execution over immutable measurements.
- `polynexus.core.compute`: optional capability item projection on `ComputeRun`.
- Existing provider engines and all GUI/CLI/Batch/Codex adapters are outside
  this slice and remain unchanged.

## Implementation plan

1. Add failing tests for the closed registry, deterministic curve metrics,
   failure isolation, and item serialization.
2. Implement `CapabilitySpec`, `CapabilityRegistry`, and `CapabilityExecutor`
   with explicit summary and extrema capabilities.
3. Attach validated `CapabilityItemResult` tuples to completed `ComputeRun`
   records without changing the legacy direct-run service.
4. Run focused tests and the structured verifier, then create an allowlisted
   local checkpoint.

## Acceptance criteria

- [x] The default registry exposes only explicit capability ids.
- [x] Summary and extrema capabilities return deterministic finite values.
- [x] Unsupported families become `not_applicable`; item exceptions become
  `failed`; other items still execute.
- [x] Capability item ids are stable for the same canonical template.
- [x] `ComputeRun` serializes items and rejects items on non-completed runs.
- [x] Existing direct-run tests remain green.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_capability_execution.py tests/test_compute_models.py tests/test_compute_service.py
python scripts/verify.py --task docs/agent/tasks/2026-08-26-capability-execution.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add canonical capability executor" `
  --files docs/superpowers/specs/2026-08-26-capability-execution-design.md docs/agent/tasks/2026-08-26-capability-execution.md polynexus/core/canonical_experiments/capabilities.py polynexus/core/canonical_experiments/__init__.py polynexus/core/compute/models.py tests/test_capability_execution.py tests/test_compute_models.py
```

## Completion evidence

- Exact commands and outcomes: focused tests `61 passed, 4 skipped`;
  structured verification passed task-check, Ruff, compile, quality `309`,
  preprocessing `157`, and whitespace via
  `python scripts/verify.py --task docs/agent/tasks/2026-08-26-capability-execution.md --changed --types`.
- Known limitations or follow-up: consumer migration and DSC thermal
  capabilities are separate tasks.
- Pre-existing changes left untouched: historical permission-denied pytest
  artifact directories remain untouched; no source data was changed.
