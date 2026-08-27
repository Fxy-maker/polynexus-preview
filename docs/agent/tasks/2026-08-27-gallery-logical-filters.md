---
task_id: 2026-08-27-gallery-logical-filters
kind: daily
status: implementation_complete_review_required
date: 2026-08-27
title: Filter evidence gallery by logical figure fields
---

# Filter evidence gallery by logical figure fields

## Goal

Allow GUI/evidence consumers to select logical figures by technique, group, and
role before loading assets, reducing duplicate format clutter.

## Non-goals

- No scientific role reclassification.
- No deletion of PNG/SVG/PDF assets.

## Affected boundaries

- GUI gallery adapter and pure gallery service only; provider and package schemas
  are unchanged.

## Acceptance criteria

- [x] Filters match technique, group, and role case-insensitively.
- [x] Filtering occurs before filesystem asset resolution.
- [x] Existing callers without filters retain behavior.

## Implementation plan

1. Add failing filter regression test.
2. Implement optional filters in gallery service and adapter.
3. Run GUI/gallery verification and checkpoint.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_plot_gallery_service.py tests/test_evidence_package_view.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-gallery-logical-filters.md --changed --types
git diff --check
```

## Completion evidence

- Focused matrix: `24 passed`.
- `python scripts/verify.py --task docs/agent/tasks/2026-08-27-gallery-logical-filters.md --changed --types` pending final checkpoint.
- Pre-existing `active_run.json`, `runs/`, and `tests/_tmp_phase3/` untouched.
