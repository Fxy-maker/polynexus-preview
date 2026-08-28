---
task_id: 2026-08-29-ars-evidence-file-links
kind: architecture
status: completed
date: 2026-08-29
title: Make ARS evidence file links explicit
---

# Make ARS evidence file links explicit

## Goal

Expose package-relative links to the shared result-table and writing-evidence
projections in `ars-writing-input.json`.

## Non-goals

- Do not duplicate large tables or evidence payloads into the ARS JSON.
- Do not change metric eligibility, review decisions, or scientific conclusions.
- Do not create a second GUI/CLI/ARS result representation.

## Affected boundaries

- `build_ars_writing_input` shared ARS handoff DTO.
- Evidence package `ars-writing-input.json` consumer.
- Project package and ARS handoff regression tests.

## Implementation plan

1. Add stable package-relative `result_tables` and `writing_evidence` fields to
   the shared ARS handoff payload.
2. Add regression assertions through the evidence packager test.
3. Run the handoff/package matrix and task-scoped verifier, then record the
   acceptance note and checkpoint.

## Acceptance criteria

- [x] ARS payload points to `result-tables.json` and `writing-evidence.json`.
- [x] Existing ARS validation and metric eligibility behavior is unchanged.
- [x] Focused and task-scoped verification is green; see
  `docs/acceptance/2026-08-29-ars-evidence-file-links.md`.

## Verification

```powershell
pytest -q tests/test_project_workflow_package.py::test_package_writes_citation_metrics_with_writing_evidence_links tests/test_project_ars_writing_handoff.py
python scripts/verify.py --task docs/agent/tasks/2026-08-29-ars-evidence-file-links.md --changed --types
git diff --check
```
