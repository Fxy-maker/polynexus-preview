---
task_id: 2026-08-13-ars-writing-handoff
kind: scientific
status: in_progress
date: 2026-08-13
title: Versioned ARS Results and Discussion evidence handoff
---

# ARS Writing Handoff

## Goal

Publish a versioned, machine-validatable `ars-writing-input.json` in every
evidence package so ARS can prepare Results and Discussion from explicit
evidence without promoting diagnostic observations into scientific claims.

## Non-goals

- Do not generate manuscript prose, citations, or literature comparisons.
- Do not change analysis calculations, raw data, or existing provider gates.
- Do not infer cross-technique sample identity or conclusions.

## Boundaries

- `polynexus/core/project_workflow/`: package-local ARS contract and
  validation.
- Package manifest, focused tests, acceptance, and durable work memory.

## Acceptance criteria

- [ ] Package manifest declares `ars_writing_input` and package materializes a
  versioned JSON handoff.
- [ ] Each technique section carries source/run/evidence links, citable metric
  IDs, figure/table links, Result eligibility, Discussion-only evidence, and
  prohibited claims.
- [ ] Diagnostic-only values are excluded from Results candidate metric IDs but
  remain visible as Discussion/audit diagnostics with their provider reasons.
- [ ] The handoff names package-level limitations and mandatory human review
  requirements without leaking unrelated technique-local limitations.
- [ ] A validator rejects malformed IDs, missing package files, or any metric
  promoted beyond its citation ledger eligibility.
- [ ] Real four-technique PA6 replay writes and validates the handoff.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_ars_writing_handoff.py tests/test_project_workflow_package.py tests/test_ai_native_project_entrypoint.py
python scripts/verify.py --task docs/agent/tasks/2026-08-13-ars-writing-handoff.md --changed --types
git diff --check
```
