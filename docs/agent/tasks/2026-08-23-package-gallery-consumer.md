---
task_id: 2026-08-23-package-gallery-consumer
kind: architecture
status: implementation_complete_review_required
date: 2026-08-23
title: Connect evidence-package gallery to the canonical figure index
---

# Connect Evidence-Package Gallery

## Goal

Make the Evidence Package GUI display the same logical figures exposed by
`figure-index.json`, without rescanning package directories or claiming that a
static package SVG is object-editable.

## Non-goals

- Do not change figure generation, scientific metrics, writing eligibility, or
  immutable package contents.
- Do not change the Quick Analysis/current-run gallery.
- Do not add a second GUI-only figure manifest or silently promote figures.

## Shared objects and entry points

- Objects: evidence package and chart/figure view DTOs.
- Producer: existing package `figure-index.json` and `EvidencePackageView`.
- AI/Codex/CLI: unchanged; they continue reading the canonical package index.
- GUI: `EvidencePackageViewAdapter`, `EvidencePackageDialog`, and the shared
  `ChartGallery` consume the index-backed entries.
- Cross-entry rule: package entries are derived only from `FigureIndexEntry`;
  direct SVGs remain static and package-relative paths remain traceable.

## Affected boundaries

- [x] Evidence package view: retains only the resolved package root alongside
  its existing logical figure index DTOs.
- [x] GUI gallery projection: maps index roles to existing gallery roles and
  resolves only package-relative SVG assets.
- [x] Evidence Package dialog: adds a static `ChartGallery` consumer; Quick
  Analysis and CLI remain unchanged.
- [x] Shared `ChartGallery`: its new opt-in read-only mode suppresses the
  write-capable batch-edit control without changing ordinary galleries.

## Implementation plan

1. Add acceptance tests that prove index metadata, fail-closed path handling,
   and the Gallery tab contract before changing production code.
2. Project `FigureIndexEntry` values into static `FigureGalleryEntry` values
   through the shared evidence view and gallery service, and run it in
   read-only mode for immutable packages.
3. Run the focused GUI/view tests and structured task verification, then obtain
   architecture review before merging.

## Acceptance criteria

- [x] One valid package SVG produces one gallery entry with normalized role,
  technique/group metadata, and writing-eligibility metadata.
- [x] Missing or invalid package SVGs are skipped fail-closed; sibling PNG/PDF
  files are not added as duplicate logical figures.
- [x] A package document path never upgrades the entry to object editing.
- [x] Evidence Package GUI exposes a read-only Gallery tab populated from the
  shared DTO; Quick Analysis behavior is unchanged.
- [x] Focused producer/consumer tests and the structured verifier pass.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_plot_gallery_service.py tests/test_evidence_package_view.py tests/test_main_window_figure_mixin.py
python scripts/verify.py --task docs/agent/tasks/2026-08-23-package-gallery-consumer.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(gui): consume canonical evidence package figures" `
  --files polynexus/core/project_workflow/evidence_view.py polynexus/gui/plot_gallery_service.py polynexus/gui/evidence_package_view.py polynexus/gui/widgets/chart_viewer.py tests/test_plot_gallery_service.py tests/test_evidence_package_view.py docs/agent/tasks/2026-08-23-package-gallery-consumer.md docs/superpowers/plans/2026-08-23-package-gallery-consumer.md
```

## Completion evidence

- Exact commands and outcomes: focused gallery/view/figure-mixin matrix passed
  `26`; structured verifier passed after implementation.
- Known limitations or follow-up: the gallery presents package SVGs as static
  assets. It does not create editable chart documents or change Quick Analysis.
- Pre-existing changes left untouched: the local evidence-review-loop task,
  temporary RAG test data, and other untracked diagnostics were not changed.
