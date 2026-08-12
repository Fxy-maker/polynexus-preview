---
task_id: 2026-08-14-ai-native-project-entrypoint
kind: architecture
status: implementation_complete_review_required
date: 2026-08-14
title: Add AI-native project analysis entrypoint and three-layer status
---

# AI-Native Project Entrypoint

## Goal

Let Codex/ARS send a project directory and research question to one simple
entrypoint that discovers raw inputs, runs the existing project workflow, and
returns figures/tables/evidence package paths with understandable statuses.

## Non-goals

- Do not remove or break the lower-level `inspect/plan/run/package` contracts.
- Do not hide scientific limitations from the machine-readable result.
- Do not invent sample identity, background calibration, or publication approval.

## Affected boundaries

- Project workflow service: orchestration facade and status projection.
- CLI: one `analyze-project` operation for AI/ARS callers.
- Tests/docs: regression, acceptance, and durable memory.

## Acceptance criteria

- [ ] One call from a project root can inspect, plan, run, and package without a request JSON file.
- [ ] Output exposes `computation`, `data_quality`, and `publication` statuses separately.
- [ ] Output includes package path, evidence count, figures/tables, and actionable reasons.
- [ ] Existing project workflow CLI operations remain compatible.

## Implementation plan

1. Add failing service/CLI tests for the unified entrypoint and status projection.
2. Implement orchestration and parser wiring using existing contracts.
3. Run focused and structured verification; record acceptance and checkpoint.

## Verification

- `python -m pytest tests/test_ai_native_project_entrypoint.py tests/test_project_workflow_cli.py -q`
- `python scripts/verify.py --task docs/agent/tasks/2026-08-14-ai-native-project-entrypoint.md --changed --types`
- `git diff --check`
