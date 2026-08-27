---
task_id: 2026-08-28-review-decision-ledger
kind: architecture
status: implementation_complete_review_required
date: 2026-08-28
title: Add an ARS review decision ledger to evidence packages
---

# Add an ARS review decision ledger to evidence packages

## Goal

Persist a pending human-review decision ledger and expose it to ARS without
altering immutable evidence or scientific values.

## Non-goals

- No automatic scientific approval or metric promotion.
- No modification of raw data, run manifests, or citation values.
- No removal of historical package compatibility.

## Affected boundaries

- `polynexus/core/project_workflow/package.py`: package artifact and manifest
  reference.
- `polynexus/core/project_workflow/ars_handoff.py`: ARS input pointer/status.
- `tests/test_review_decision_ledger.py` and package handoff tests.

## Implementation plan

1. Add a failing package test requiring `review-decision.json` and an ARS
   pointer with pending status.
2. Build the deterministic pending ledger from generated human-review items.
3. Write the ledger and expose its relative path/status in ARS input and the
   package manifest.
4. Run focused package/ARS tests and the structured verifier.
5. Record acceptance and checkpoint only the allowlisted files.

## Acceptance criteria

- [x] New package has `review-decision.json` with pending entries.
- [x] Every entry references an existing evidence id.
- [x] ARS input points to the ledger and remains review-required.
- [x] Historical package loading remains compatible.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_review_decision_ledger.py tests/test_project_workflow_package.py tests/test_project_ars_writing_handoff.py
python scripts/verify.py --task docs/agent/tasks/2026-08-28-review-decision-ledger.md --changed --types
git diff --check
```

## Completion evidence

- Package/ARS/GUI compatibility matrix: **48 passed**.
- Task verifier, Ruff, compile, quality (**311**) and preprocessing (**157**)
  gates passed.
- New ledgers are pending by construction; no scientific result is promoted.
