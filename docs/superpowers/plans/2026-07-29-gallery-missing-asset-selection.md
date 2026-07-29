# Gallery Missing-Asset Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent initial active Gallery selection from choosing Manifest asset paths that no longer exist.

**Architecture:** Keep selection policy in the pure Gallery service. Add one filesystem-existence predicate to the existing no-preference fallback only; preserve preferred-path matching and the first-entry empty fallback.

**Tech Stack:** Python, pathlib, pytest, repository verifier.

---

### Task 1: Add the regression tests

**Files:**
- Modify: `tests/test_plot_gallery_service.py`

- [x] **Step 1: Add a stale-first-entry regression**

Create a `FigureGalleryEntry` whose `preview_path` is non-empty but points to a
missing file, followed by an entry whose preview file exists. Assert that the
second entry and its existing path are selected.

- [x] **Step 2: Add the all-missing conservative regression**

Create two entries whose non-empty preview paths do not exist. Assert that the
first entry remains selected and `selected_path == ""`.

- [x] **Step 3: Run the focused tests before implementation**

Run:

```powershell
python -m pytest -q tests/test_plot_gallery_service.py
```

Expected: the new stale-first-entry test fails because `_entry_selection_path`
currently treats any non-empty string as usable; the existing tests pass.

### Task 2: Implement the minimal selection guard

**Files:**
- Modify: `polynexus/gui/plot_gallery_service.py`

- [x] **Step 1: Make `_entry_selection_path` reject missing files**

Keep candidate ordering unchanged. Strip the candidate text, then return it
only when `Path(path).exists()` succeeds. Catch `OSError` and continue to the
next candidate. Return `""` when no candidate is both non-empty and existing.

- [x] **Step 2: Run focused GREEN verification**

Run:

```powershell
python -m pytest -q tests/test_plot_gallery_service.py
```

Expected: all Gallery service tests pass, including the new regressions.

### Task 3: Verify the adjacent route and repository contract

**Files:**
- No additional source files.

- [x] **Step 1: Run the Gallery/Editor matrix**

Run:

```powershell
python -m pytest -q tests/test_plot_gallery_service.py tests/test_chart_gallery.py tests/test_chart_editor.py
```

Expected: exit code `0` with zero failed tests. If a named test module is not
present, record that exact limitation and run the discovered adjacent Gallery
and Editor modules instead.

- [x] **Step 2: Run the structured verifier and whitespace check**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-gallery-missing-asset-selection.md --changed --types
git diff --check
```

Record exact exit codes and summaries; do not infer a full-suite result from
the task-scoped verifier.

- [x] **Step 3: Create the explicit allowlist checkpoint**

After verification, run:

```powershell
python scripts/auto_commit.py --message "fix(gui): skip missing gallery assets" --files polynexus/gui/plot_gallery_service.py tests/test_plot_gallery_service.py docs/agent/tasks/2026-07-29-gallery-missing-asset-selection.md docs/superpowers/specs/2026-07-29-gallery-missing-asset-selection-design.md docs/superpowers/plans/2026-07-29-gallery-missing-asset-selection.md
```

Confirm the resulting commit contains only the five allowlisted files. Leave
all pre-existing workspace changes untouched.
