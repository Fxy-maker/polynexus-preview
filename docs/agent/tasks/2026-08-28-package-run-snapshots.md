---
task_id: 2026-08-28-package-run-snapshots
kind: structured
status: implementation_complete_review_required
date: 2026-08-28
title: Make evidence packages carry relative run snapshots
---

# Make evidence packages carry relative run snapshots

## Goal

Copy each validated project run manifest into a package-relative `runs/` area
and reference those snapshots from `manifest.json`, so package provenance does
not depend on absolute host paths.

## Non-goals

- Do not copy raw input data or change provider calculations.
- Do not remove compatibility fields from existing run manifests.

## Affected boundaries

- `polynexus/core/project_workflow/package.py`: package materialization.
- `tests/test_project_workflow_package.py`: portability regression.

## Acceptance criteria

- [x] Every packaged run has `runs/<run_id>.json`.
- [x] `manifest.json.run_manifests` contains only package-relative paths.
- [x] Existing artifact-hash and evidence-view checks remain valid.

## Implementation plan

1. Add a failing package test for relative run snapshots.
2. Write validated manifest snapshots under `runs/` during packaging.
3. Run package/evidence matrices, structured verification, and an allowlisted checkpoint.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_workflow_package.py tests/test_evidence_package_view.py tests/test_ai_native_project_entrypoint.py
python scripts/verify.py --task docs/agent/tasks/2026-08-28-package-run-snapshots.md --changed --types
git diff --check
```

## Completion evidence

- Focused package/GUI/AI matrix: **50 passed**.
