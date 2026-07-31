# SAXS Workbench Review Downstream Evidence Propagation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the existing Workbench scientific-review snapshot through newly built SAXS Figure/Manifest and Export evidence.

**Architecture:** Add a small read-only resolver in `figure_evidence.py` that prefers current result metadata and falls back to the legacy config field. Existing Figure and Export consumers continue to call the source/scope/status fail-closed projector; only the payload source changes.

**Tech Stack:** Python, PySide-independent SAXS evidence DTOs, FigurePipeline, JSON export, pytest, Ruff, and `scripts/verify.py`.

---

### Task 1: Record the atomic boundary

**Files:**
- Read: `polynexus/gui/main_window_results_mixin.py`
- Read: `polynexus/core/saxs_engine/figure_evidence.py`
- Read: `polynexus/core/saxs_engine/figure_provider.py`
- Read: `polynexus/core/saxs_export_bundle.py`
- Create: `docs/superpowers/specs/2026-07-31-saxs-workbench-review-downstream-propagation-design.md`
- Create: `docs/superpowers/plans/2026-07-31-saxs-workbench-review-downstream-propagation.md`
- Create: `docs/agent/tasks/2026-07-31-saxs-workbench-review-downstream-propagation.md`

- [x] Keep this slice limited to evidence transport. The authoritative review
  write remains the Workbench/SampleDB path, and all scientific and
  publication gates remain unchanged.

### Task 2: Write the failing Figure/Manifest and Export tests

**Files:**
- Modify: `tests/test_saxs_figure_evidence_binding.py`
- Modify: `tests/test_saxs_export_bundle.py`

- [x] Add a valid accepted `saxs.1d` payload to the current result metadata
  while leaving `cfg.scientific_review` absent.
- [x] Build the existing static SAXS definitions and assert the detached
  provenance reports `review_accepted`; persist one definition through
  `FigurePipeline` and assert the same review evidence in the document.
- [x] Export a one-frame engine with the same result metadata and assert
  `quality_evidence.json` contains the accepted review evidence.
- [x] Run the two focused tests and confirm they fail because the current
  config-only adapter returns no review evidence.

### Task 3: Implement the minimal result-first resolver

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_evidence.py`

- [x] Add a private resolver that checks `source.result.metadata` for a
  non-empty mapping, then checks `source.cfg.scientific_review`, returning an
  empty/absent value otherwise.
- [x] Make both `configured_saxs_1d_review` and
  `configured_saxs_review_evidence` use that resolver.
- [x] Keep `build_saxs_review_evidence` unchanged so invalid records,
  mismatched scopes/sources, and non-accepted statuses stay fail-closed.

### Task 4: Run GREEN and regression checks

**Files:**
- The implementation and two focused test files from Tasks 2-3.

- [x] Run the focused Figure/Manifest/Export tests and confirm complete
  pytest summaries with exit code `0`.
- [x] Run the SAXS matrix covering scientific review, Figure evidence,
  Manifest, and Export consumers; record its actual non-zero result and
  unrelated D: SampleDB limitation rather than claiming a pass.
- [x] Run `python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-workbench-review-downstream-propagation.md --changed --types`
  with C: external cache/temp overrides; it exited `0`.
- [x] Run `git diff --check`.
- [x] Run `python scripts/test_storage.py report --json` and
  `python scripts/test_storage.py clean --older-than-hours 24 --json`; do not
  use `--apply`.

### Task 5: Review and checkpoint

**Files:**
- The explicit allowlist is the four files below plus the two modified tests
  and the one production adapter from Tasks 2-3.

- [x] Review cumulative diff and confirm no `active-work.md`,
  `current-state.md`, `pytest.ini`, scratch, generated output, or test-storage
  directory is included.
- [x] Create one checkpoint with `scripts/auto_commit.py` using only the
  explicit changed-file allowlist.
- [x] Record the actual commit hash and all verification limitations in the
  task card and acceptance note.
