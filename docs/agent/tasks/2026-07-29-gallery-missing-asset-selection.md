---
task_id: 2026-07-29-gallery-missing-asset-selection
kind: gui-regression
status: completed
---

# Gallery missing-asset selection

## Goal

Make the initial active Gallery selection skip Manifest entries whose asset
paths are non-empty but no longer exist, so Editor never receives a stale
selection when a later usable entry is available.

## Non-goals

- Do not change preferred-path or same-basename variant matching.
- Do not delete, repair, recreate, or migrate missing assets.
- Do not hide diagnostic Manifest entries from the Gallery.
- Do not change Figure Manifest schema, publication roles, or SAXS scientific
  behavior.
- Do not modify pre-existing memory, scratch, capture, or test-storage files.

## Affected boundaries

- `polynexus/gui/plot_gallery_service.py` initial Gallery entry selection.
- `tests/test_plot_gallery_service.py` regression coverage for missing assets.
- Existing Gallery-to-Editor route contracts that consume
  `PlotGallerySelection.selected_path`.

## Implementation plan

1. Add RED tests for a missing first asset, an existing later asset, and the
   all-missing conservative fallback.
2. Update only `_entry_selection_path()` to require filesystem existence for
   initial selection, while preserving candidate order and preferred matching.
3. Run the focused Gallery tests, the adjacent Gallery/Editor matrix, the
   structured verifier, and `git diff --check`.
4. Create one explicit allowlist checkpoint containing only this task's source,
   tests, and planning documents.

## Design

The initial-selection fallback will treat a candidate path as usable only when
it is non-empty and resolves to an existing filesystem entry. The existing
preferred-path branch remains unchanged, including its conservative behavior
when the preferred asset is stale. If no entry has a usable path, the current
fallback still returns the first entry with an empty selected path.

## Acceptance criteria

- [x] A stale non-empty first entry is skipped when a later entry has an
  existing asset.
- [x] An existing first entry remains selected.
- [x] When every entry is missing, selection remains conservative and returns
  the first entry with an empty selected path.
- [x] Existing preferred-path tests and the Gallery/Editor route matrix pass.
- [x] Task-scoped verification and `git diff --check` pass.
- [x] The explicit allowlist checkpoint contains only this task's files.

## Verification

```powershell
python -m pytest -q tests/test_plot_gallery_service.py
python -m pytest -q tests/test_plot_gallery_service.py tests/test_chart_gallery.py tests/test_chart_editor.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-gallery-missing-asset-selection.md --changed --types
git diff --check
```

## Actual verification evidence

- RED: `python -m pytest -q tests/test_plot_gallery_service.py` reported
  `13 passed, 2 failed`; both failures were the new missing-asset assertions.
- GREEN: the focused Gallery service suite reported `15 passed`.
- Adjacent matrix: `python -m pytest -q
  tests/test_plot_gallery_service.py tests/test_chart_gallery_management.py
  tests/test_chart_editor.py` reported `268 passed in 44.85s`, exit code `0`.
- The planned `tests/test_chart_gallery.py` does not exist in this repository;
  `tests/test_chart_gallery_management.py` was used as the existing Gallery
  management coverage instead.
- Structured verifier exited `0`; quality gate reported `290 passed` and
  preprocessing optimization reported `106 passed`. Ruff, compile, memory,
  task, and whitespace checks also passed.
- `git diff --check` exited `0`.

## Explicit changed-file allowlist

- `polynexus/gui/plot_gallery_service.py`
- `tests/test_plot_gallery_service.py`
- `docs/agent/tasks/2026-07-29-gallery-missing-asset-selection.md`
- `docs/superpowers/specs/2026-07-29-gallery-missing-asset-selection-design.md`
- `docs/superpowers/plans/2026-07-29-gallery-missing-asset-selection.md`

## Pre-existing workspace changes

Keep `docs/agent/memory/current-state.md`, all untracked test/storage/capture/
scratch directories, and unrelated tracked or untracked files outside this
task and its checkpoint.
