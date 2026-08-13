---
task_id: 2026-08-13-evidence-package-view
kind: architecture
status: proposed
date: 2026-08-13
title: Technique-neutral evidence package view model
---

# Evidence Package View

## Goal

Expose one immutable, technique-neutral view model for GUI inspection of a
materialized evidence package.

## Non-goals

- Do not add provider-specific GUI branches or re-run analysis.
- Do not select manuscript figures automatically or clear review status.
- Do not modify package files or raw data.

## Affected boundaries

- `polynexus/core/project_workflow/`: package DTO and loader.
- `polynexus/gui/`: GUI-facing read-only adapter.
- Focused tests, acceptance record, durable memory, and local checkpoint.

## Acceptance criteria

- [ ] Loading a package yields package status, techniques, evidence rows,
  metrics, figure/table paths, limitations, and human-review rows.
- [ ] DTOs contain no technique algorithm state and expose stable JSON-safe
  values only.
- [ ] Loader rejects missing or inconsistent package references.
- [ ] GUI adapter consumes only the DTO and has no technique-specific branch.
- [ ] Real PA6 package loads with all four techniques and review boundaries.

## Implementation plan

1. Write failing DTO/loader and GUI adapter tests against a synthetic package.
2. Implement immutable package view records and reference validation.
3. Add the GUI adapter, replay the real PA6 package, record acceptance, and
   run structured verification before the allowlisted checkpoint.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_evidence_package_view.py tests/test_project_ars_writing_handoff.py tests/test_project_workflow_package.py
python scripts/verify.py --task docs/agent/tasks/2026-08-13-evidence-package-view.md --changed --types
git diff --check
```
