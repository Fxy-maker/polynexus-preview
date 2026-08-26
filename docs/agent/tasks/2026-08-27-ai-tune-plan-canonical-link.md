---
task_id: 2026-08-27-ai-tune-plan-canonical-link
kind: architecture
status: complete
date: 2026-08-27
title: Link AI-tuning plans to the shared canonical template
---

# Link AI-tuning plans to the shared canonical template

## Goal

When AI tuning has a completed shared `ComputeRun`, its adaptive plan must
reference that run's source-bound canonical template instead of inventing a
second legacy input template.

## Non-goals

- No change to candidate-round optimization or provider algorithms.
- No removal of historical plan fields or synthetic-path compatibility.
- No scientific promotion or automatic approval of tuning outcomes.

## Shared objects and entry points

- Producer: `polynexus/cli/run_ai_tune_service.py` plan attachment.
- Source object: orchestrator `compute_run` JSON projection.
- Consumers: AI-tune report, database persistence, and ARS plan/evaluation DTOs.

## Affected boundaries

- `run_ai_tune` plan attachment must consume the existing JSON-safe
  `compute_run` projection without mutating the run object.
- `AnalysisPlan` keeps its existing DTO shape and hash semantics; only the
  canonical template payload source changes when a valid shared projection is
  present.
- Persistence and ARS consumers continue reading the same report fields.

## Implementation plan

1. Add a regression test requiring a shared run template to appear in the
   attached adaptive plan.
2. Project and validate the shared template fields, with a compatibility
   fallback for missing or malformed reports.
3. Run the CLI/orchestrator/plan-consumer matrix and the structured verifier.

## Acceptance criteria

- [x] A report containing a valid shared canonical template copies its template
  identity and conversion version into `analysis_plan.canonical_template`.
- [x] Reports without a usable shared template retain the legacy compatibility
  template and remain JSON-safe.
- [x] Existing candidate, evaluation, persistence, and synthetic-path behavior
  remains unchanged.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_cli_run_ai_tune_service.py tests/test_orchestrator_compute_run.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-ai-tune-plan-canonical-link.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(ai-tune): link adaptive plans to shared templates" `
  --files polynexus/cli/run_ai_tune_service.py tests/test_cli_run_ai_tune_service.py docs/agent/tasks/2026-08-27-ai-tune-plan-canonical-link.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md docs/acceptance/2026-08-27-shared-compute-run-migration.md
```

## Completion evidence

- `python -m pytest -p no:cacheprovider -q tests/test_cli_run_ai_tune_service.py::test_ai_tune_plan_reuses_shared_compute_template` — 1 passed.
- `python -m pytest -p no:cacheprovider -q tests/test_cli_run_ai_tune_service.py tests/test_orchestrator_compute_run.py tests/test_analysis_plan_consumers.py tests/test_project_workflow_models.py` — 31 passed.
- `git diff --check` — passed.
- Valid shared `compute_run.canonical_template` projections now supply the
  adaptive plan's template ID, conversion version, source artifact ID, and
  available content/conversion hashes. Missing or malformed projections keep
  the legacy compatibility template.
- Known limitations: candidate rounds still use the established in-memory
  orchestrator and remain review-required; this task does not change provider
  algorithms or scientific acceptance.
- Pre-existing local runtime outputs (`active_run.json`, `runs/`,
  `tests/_tmp_phase3/`) were left untouched.
