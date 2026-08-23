# Evidence-Package Gallery Consumer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display canonical evidence-package logical figures in the GUI Gallery.

**Architecture:** Keep `FigureIndexEntry` and `EvidencePackageView` as the
shared read model. The GUI adapter resolves package-relative SVGs through the
existing gallery service, normalizes package candidate roles to the gallery's
publication-role vocabulary, and exposes a static-only `ChartGallery` tab.

**Tech Stack:** Python, PySide6, pytest, existing figure/gallery DTOs.

---

### Task 1: Lock the package-gallery projection contract

**Files:**
- Modify: `tests/test_plot_gallery_service.py`
- Modify: `tests/test_evidence_package_view.py`

- [x] Add tests for role/technique/group projection, writing-eligibility
  capability metadata, duplicate-free SVG assets, missing/unsafe SVG skip, and
  static state even when a document path exists.
- [x] Add a GUI dialog assertion that the new Gallery tab uses the projected
  figure IDs and remains separate from the four package inspection tabs.
- [x] Run the focused tests and confirm the new expectations fail before the
  implementation changes.

### Task 2: Implement the shared projection and GUI consumer

**Files:**
- Modify: `polynexus/core/project_workflow/evidence_view.py`
- Modify: `polynexus/gui/plot_gallery_service.py`
- Modify: `polynexus/gui/evidence_package_view.py`

- [x] Preserve the package root on the read-only `EvidencePackageView` so the
  GUI can resolve canonical relative paths without rescanning.
- [x] Normalize package roles (`manuscript_candidate`, `supporting_candidate`,
  `diagnostic`) to gallery roles (`main`, `si`, `diagnostic`), retain the raw
  role and index metadata in the capability report, and keep one SVG asset.
- [x] Skip missing or unsafe SVG candidates and never infer object editing from
  a package document field.
- [x] Add `EvidencePackageViewAdapter.gallery_entries()` and a read-only Gallery
  tab backed by `ChartGallery.load_entries()`.

### Task 3: Verify and checkpoint

**Files:**
- Update: `docs/agent/tasks/2026-08-23-package-gallery-consumer.md`

- [x] Run the focused matrix, structured verifier, and `git diff --check`.
- [x] Record exact outcomes and limitations in the task card.
- [x] Create one allowlisted checkpoint with `scripts/auto_commit.py`.
