---
task_id: 2026-08-13-project-workflow-recovery-v4
kind: architecture
status: implementation_complete_review_required
date: 2026-08-13
title: Add project workflow resume and approved context corrections
---

# Project Workflow Recovery V4

## Goal

Provide a fail-closed resume/retry entrypoint and an auditable way to attach
explicitly approved context corrections to a new request.

## Non-goals

- No automatic retry of a failed scientific interpretation.
- No mutation of raw files or indexed raw facts.
- No conversion of inferred context into verified instrument facts.

## Affected boundaries

- Project workflow service and persisted request/run manifests.
- JSON-safe request parameters and ARS writing-input provenance.

## Acceptance criteria

- [ ] Resume validates the persisted run/request/plan and source hashes.
- [ ] Resume reuses the deterministic request and produces a new validated run.
- [ ] Approved corrections are explicit, immutable request parameters.
- [ ] Invalid or unapproved corrections fail closed.

## Implementation plan

1. Add failing tests for resume and correction validation.
2. Implement service APIs and manifest provenance.
3. Run focused and structured verification, then checkpoint.

## Verification

- `python -m pytest tests/test_project_workflow_recovery.py -q`
- `python scripts/verify.py --task docs/agent/tasks/2026-08-13-project-workflow-recovery-v4.md --changed --types`
- `git diff --check`
