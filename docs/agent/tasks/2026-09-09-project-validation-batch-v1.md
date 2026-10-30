---
task_id: 2026-09-09-project-validation-batch-v1
kind: architecture
status: implementation_complete_review_required
date: 2026-09-09
title: Add project validation batch aggregation
---

# Project validation batch v1

## Goal

Allow a project workspace to collect multiple technique-neutral validation
cases and persisted public result projections, run the shared validator for
each case, and persist one aggregate validation report.

## Non-goals

- No raw-data decoding, provider execution, or arbitrary Python import from a
  project manifest.
- No conversion of validation reports into Evidence Package members.
- No uncertainty, capability promotion, calibration, or scientific conclusion.

## Shared objects and entry points

- Objects: `ValidationCase`, public result projection, project validation batch
  report. Existing ProjectWorkflowRun, ComputeRun, Evidence Package, and
  WorkingEvidence objects remain unchanged and read-only.
- AI/Codex/CLI: may provide JSON cases and result projections; all comparisons
  use the shared Core validator.
- GUI: unchanged in this slice; it can consume the persisted JSON report later.
- Cross-entry rule: project aggregation is a wrapper over the same
  `run_validation` contract, never a second result representation.

## Affected boundaries

- Project workflow: new in-memory batch DTO and optional `.polynexus/validation`
  persistence helper.
- Core validation: reused without technique-specific branches.
- Security: persisted inputs are JSON-shaped and no code is imported or run.
- Scientific semantics: report remains diagnostic and review-required.

## Implementation plan

1. Add immutable batch entry/report DTOs with content hashes and aggregate
   status. Keep standard/negative-control labels on the underlying case.
2. Add a runner that compares each pair of persisted public projections through
   `run_validation`, retaining per-case reports and deterministic ordering.
3. Add a project workspace helper that writes/reads the report only beneath a
   documented derived directory.
4. Add focused tests for cross-technique aggregation, mixed pass/fail status,
   round-trip/hash tamper rejection, and no Evidence/ComputeRun mutation.

## Acceptance criteria

- [x] Multiple techniques can be aggregated with one public report contract.
- [x] Aggregate status is `passed` only when every case passes; failures remain
  per-case and do not stop unrelated cases.
- [x] Reports round-trip and reject tampering; ordering is deterministic.
- [x] Persisted reports stay in `.polynexus/validation` and never overwrite raw
  project material.
- [x] No automatic evidence inclusion, capability promotion, or uncertainty
  claim is produced.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_validation.py
python scripts/verify.py --task docs/agent/tasks/2026-09-09-project-validation-batch-v1.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(project): add validation batch aggregation" `
  --files polynexus/core/project_workflow/validation.py polynexus/core/project_workflow/workspace.py polynexus/core/project_workflow/__init__.py polynexus/cli/run_project_validation_service.py polynexus/cli/parser.py polynexus/__main__.py tests/test_project_validation.py docs/agent/tasks/2026-09-09-project-validation-batch-v1.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes: `python -m pytest -p no:cacheprovider -q
  tests/test_project_validation.py` (4 passed); task verifier passed quality
  gate 313, preprocessing 157, Ruff, compile, and `git diff --check`.
- Known limitations or follow-up: project CLI/GUI command wiring and real
  instrument/standard-sample replay remain follow-up work.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`
  and unrelated untracked plans/data.
