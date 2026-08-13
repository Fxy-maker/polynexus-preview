---
task_id: 2026-08-14-ai-project-candidate-groups
kind: architecture
status: checkpointed_review_required
date: 2026-08-14
title: Add conservative AI project candidate grouping
---

# AI Project Candidate Groups

## Goal

Turn a mixed raw directory into clear candidate experiment groups so Codex/ARS
can select the relevant sequence before running analyses.

## Non-goals

- Do not treat filename groups as verified sample, batch, or formulation facts.
- Do not automatically join different candidate groups.
- Do not alter scientific numeric pipelines.

## Affected boundaries

- AI-native project discovery and summary DTO.
- Project workflow CLI output.
- Tests and acceptance documentation.

## Acceptance criteria

- [x] FTIR-style names form JW-temperature, SW-temperature, and 250 C time candidates.
- [x] A matching research question selects exactly one candidate group.
- [x] An ambiguous question returns candidates and a concise selection prompt without running data.
- [x] Explicit `--paths` remains authoritative.

## Implementation plan

1. [x] Add tests for grouping, automatic question selection, and ambiguity.
2. [x] Implement filename-only candidate extraction and AI entrypoint selection.
3. [x] Expose candidates in the CLI, verify, document, and checkpoint.

## Verification

- `python -m pytest tests/test_ai_project_candidate_groups.py tests/test_ai_native_project_entrypoint.py -q`
- `python scripts/verify.py --task docs/agent/tasks/2026-08-14-ai-project-candidate-groups.md --changed --types`
- `git diff --check`
