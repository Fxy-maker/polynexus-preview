---
task_id: 2026-08-13-project-technique-series-v3
kind: architecture
status: implementation_complete_review_required
date: 2026-08-13
title: Add project technique series and ARS relation projection
---

# Project Technique Series V3

Implement a registered multi-file same-technique route for project-local
workflow requests. A series is an ordered set of indexed artifacts; ordering is
deterministic by normalized relative path unless the request supplies an
explicit order. Each provider step carries its artifact index, and source
hashes are checked before execution and packaging.

The package layer emits only conservative relations derived from explicit run
identity (same request hash and run membership). It does not infer sample,
formulation, batch, or cross-technique identity from filenames.

Design: `docs/superpowers/specs/2026-08-13-project-technique-series-v3-design.md`
Plan: `docs/superpowers/plans/2026-08-13-project-technique-series-v3.md`

Acceptance: focused series/package tests, structured verifier, and a read-only
PA6 directory smoke. Scientific and manuscript promotion remain human review.

## Goal

Allow Codex to run a deterministic multi-file sequence for one technique and
hand its bounded evidence to ARS.

## Non-goals

- No automatic sample, batch, formulation, or cross-technique identity inference.
- No new numeric analysis engine or raw-data copy.
- No unattended publication or manuscript conclusion.

## Affected boundaries

- Project workflow adapter, planner, and run artifact binding.
- Agent workflow recipe execution for indexed series steps.
- ARS evidence package relations and writing input.

## Acceptance criteria

- [ ] Same-technique IR/WAXS/SAXS series produces deterministic ordered steps.
- [ ] Each step executes against its own source and stale hashes block safely.
- [ ] Package contains conservative request-membership relations.
- [ ] PA6 FTIR read-only replay and structured verification are recorded.

## Implementation plan

1. Add and validate the series recipe adapter.
2. Bind planner and provider execution to artifact indexes and hashes.
3. Project package relations and run focused/structured verification.

## Verification

- `python -m pytest tests/test_project_workflow_adapters.py tests/test_project_workflow_service.py tests/test_project_workflow_package.py -q`
- `python scripts/verify.py --task docs/agent/tasks/2026-08-13-project-technique-series-v3.md --changed --types`
- `git diff --check`
