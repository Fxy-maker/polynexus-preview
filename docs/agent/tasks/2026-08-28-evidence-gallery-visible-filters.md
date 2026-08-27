---
task_id: 2026-08-28-evidence-gallery-visible-filters
kind: structured
status: implementation_complete_review_required
date: 2026-08-28
title: Expose evidence gallery logical filters in GUI
---

# Expose evidence gallery logical filters in GUI

## Goal

Let the read-only evidence package dialog filter indexed figures by technique
and group before the gallery loads assets, while retaining the existing role,
category, and search controls inside `ChartGallery`.

## Non-goals

- Do not reclassify scientific roles or delete figure assets.
- Do not add a second persistence model or provider-specific GUI logic.

## Affected boundaries

- `polynexus/gui/evidence_package_view.py`: filter controls and DTO projection.
- `tests/test_evidence_package_view.py`: GUI regression coverage.

## Acceptance criteria

- [x] Technique and group choices are derived from `EvidencePackageView.figure_views`.
- [x] Selecting a choice reloads the gallery through `EvidencePackageViewAdapter`.
- [x] The default selection shows all indexed figures.
- [x] Existing read-only behavior and role/category filters remain available.

## Implementation plan

1. Add a failing dialog regression test for technique/group selection.
2. Populate selectors from `figure_views` and reload through the adapter.
3. Run focused GUI tests, structured verification, and the allowlisted checkpoint.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_evidence_package_view.py tests/test_plot_gallery_service.py
python scripts/verify.py --task docs/agent/tasks/2026-08-28-evidence-gallery-visible-filters.md --changed --types
git diff --check
```

## Completion evidence

- Focused GUI/gallery matrix: **25 passed**.
- Task-scoped verifier: selected checks passed; quality gates **310 + 157 passed**.

## Changed-file allowlist

- `polynexus/gui/evidence_package_view.py`
- `tests/test_evidence_package_view.py`
- `docs/agent/tasks/2026-08-28-evidence-gallery-visible-filters.md`
