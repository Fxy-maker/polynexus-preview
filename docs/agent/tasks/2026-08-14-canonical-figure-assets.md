---
task_id: 2026-08-14-canonical-figure-assets
kind: architecture
status: active
date: 2026-08-14
title: Canonicalize evidence-package figure assets
---

# Canonicalize Evidence-Package Figure Assets

## Goal

New evidence packages expose one SVG-centered logical figure asset set through
`figure-index.json`, while publication formats remain explicit exports and
existing Chart Editor object editing remains available for valid Figure Project
documents.

## Non-goals

- Change scientific analysis, metrics, canonical source conversion, or writing
  eligibility.
- Rewrite old evidence packages or raw/run data.
- Convert direct ARS Matplotlib group figures into editable object documents.
- Remove Quick Analysis, Origin export, or explicit PNG/PDF/TIFF export.

## Shared objects and entry points

- Objects: chart, export, evidence package.
- Producer: figure profiles/export/pipeline and project evidence packager.
- AI/Codex/CLI: reads the same package figure index and structured evidence;
  no private figure manifest.
- GUI: reads index-backed/legacy DTOs, displays SVG, and uses a valid
  `figure.pnfig.json` only for object editing.
- Cross-entry rule: manifest-backed figures may be object-editable; direct ARS
  group SVGs are static.  Neither path invents scientific values or provenance.

## Context and output budget

- Read first: design and implementation plan, figure export/manifest/package
  contracts, focused tests, and current memory entries.
- Search scope: `polynexus/core/figures`, `polynexus/core/project_workflow`,
  `polynexus/gui/plot_gallery_service.py`, and named tests.
- Expand only for: missing contract evidence, repeated failures, architecture,
  or shared-consumer impact.
- Report: outcome, changed files, exact verification result, limitations, and
  untouched user changes.

## Acceptance criteria

- [ ] New default evidence assets contain one SVG visual per logical figure and
  no persisted PNG/PDF/TIFF duplicates.
- [ ] Explicit publication export continues to generate requested publication
  formats from a frozen Figure Project revision.
- [ ] A package index maps every included logical figure to package-relative
  canonical assets and deduplicates legacy sibling formats.
- [ ] GUI, CLI/Codex, and ARS load the same logical figure DTO; old packages
  remain readable without write-back.
- [ ] Valid `figure.pnfig.json` opens object editing; direct group SVGs open
  static and do not falsely claim editable internal objects.
- [ ] The structured verification and focused producer/consumer tests pass.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_run_figure_manifest.py tests/test_reactive_figure_matplotlib_renderer.py tests/test_project_workflow_package.py tests/test_ars_group_figure_candidates.py tests/test_evidence_package_view.py tests/test_ai_native_project_entrypoint.py tests/test_plot_gallery_service.py tests/test_figure_window_service.py tests/test_chart_editor_save_mixin.py
python scripts/verify.py --task docs/agent/tasks/2026-08-14-canonical-figure-assets.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py --message "feat(evidence): canonicalize figure assets" --files <explicit changed files>
```

## Completion evidence

- Exact commands and outcomes:
- Known limitations or follow-up: direct ARS group figures remain static until
  their generators can produce real Figure Project object documents.
- Pre-existing changes left untouched: `.superpowers/` and
  `tests/_tmp_phase3/`.
