---
task_id: 2026-08-27-orchestrator-compute-run-bootstrap
kind: architecture
status: implementation_complete_review_required
date: 2026-08-27
title: Route AI tuning bootstrap through ComputeRun
---

# Route AI tuning bootstrap through ComputeRun

## Goal

Use the shared `ComputeRunService` for the initial AI-tuning run whenever the
source artifact is valid, while preserving the in-memory engine state needed by
subsequent controlled candidate trials.

## Non-goals

- No change to candidate parameter mutation, scoring, rollback, or scientific
  quality gates.
- No removal of compatibility behavior for synthetic or missing test inputs.
- No change to raw files or automatic publication decisions.

## Shared objects and entry points

- Producer: `ComputeRunService`.
- Consumer: `ParameterOrchestrator` bootstrap and its final report.
- AI/CLI: keeps the existing tuning report and round history; records the
  shared run projection when a valid source is available.
- GUI: unchanged; it consumes the existing AI-tuning report/persistence path.

## Affected boundaries

- `ParameterOrchestrator` baseline initialization and final report.
- `ComputeRunService` output-directory compatibility for analysis-only callers.
- Existing AI-tune CLI reports remain JSON-compatible, with an additive
  `compute_run` projection for newly canonicalized input.

## Implementation plan

1. Add focused RED tests for bootstrap routing, ambiguous input blocking, report
   projection, and no-render output compatibility.
2. Route valid bootstrap input through `ComputeRunService` and preserve the
   existing in-memory engine instance for candidate trials.
3. Record the JSON-safe shared projection in the final report without changing
   its legacy report fields.
4. Run focused producer/consumer tests and the structured verifier.

## Acceptance criteria

- [x] A valid source causes bootstrap to invoke `ComputeRunService` exactly once
  and retain the resulting `ComputeRun` on the orchestrator.
- [x] Baseline engine state and round metrics remain unchanged for existing
  callers.
- [x] Missing or synthetic compatibility inputs retain the old test-friendly
  behavior without fabricating a canonical run.
- [x] Final reports expose the shared run only as a JSON-safe projection.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_orchestrator_compute_run.py tests/test_orchestrator.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-orchestrator-compute-run-bootstrap.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(orchestrator): attach shared compute run at bootstrap" `
  --files polynexus/orchestrator_run_bootstrap.py polynexus/orchestrator_lifecycle.py polynexus/orchestrator_session.py tests/test_orchestrator_compute_run.py docs/agent/tasks/2026-08-27-orchestrator-compute-run-bootstrap.md
```

## Completion evidence

- Exact commands and outcomes: focused producer/consumer matrix `133 passed,
  3 skipped`; task verifier passed including quality `310` and preprocessing
  `157` checks.
- Known limitations or follow-up: AI-tuning directory inputs and legacy
  candidate-round mutations still use their existing adapters; full repository
  verification remains non-green due unrelated historical GUI/chart/SAXS
  failures. Human architecture/scientific review is required before deleting
  compatibility producers.
- Pre-existing changes left untouched: `tests/_tmp_phase3/` and generated local
  `active_run.json`/`runs/` artifacts.
