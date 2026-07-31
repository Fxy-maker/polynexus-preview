# SAXS Workbench Scientific Review Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Execute each task in order and checkpoint only the explicit allowlist.

**Goal:** Add a reviewer-selected SAXS 1D/2D scientific review entry to the Results Workbench while preserving all existing fail-closed gates.

**Architecture:** The core owns the ordered scope options; the GUI only presents the options and delegates record validation to the existing generic dialog. Persistence continues through the existing run-scoped SampleDB transaction and promotion snapshot.

**Tech Stack:** Python, PySide6, pytest, existing ScientificReviewRecord/SampleDB contracts.

---

### Task 1: Add the structured task boundary

**Files:**
- Create: `docs/superpowers/specs/2026-07-31-saxs-workbench-scientific-review-entry-design.md`
- Create: `docs/superpowers/plans/2026-07-31-saxs-workbench-scientific-review-entry.md`
- Create: `docs/agent/tasks/2026-07-31-saxs-workbench-scientific-review-entry.md`

- [x] Record the reviewer-selected scope decision, non-goals, affected files, and explicit allowlist.

### Task 2: Write and run RED tests

**Files:**
- Test: `tests/test_scientific_review.py`
- Test: `tests/test_scientific_review_workbench.py`

- [ ] Add a core test asserting SAXS returns `("saxs.1d", "saxs.2d")` while IR/NMR/Joint retain their single options and unknown techniques return `()`.
- [ ] Add a Workbench test that a persisted SAXS run presents the selected `saxs.2d` scope to the generic dialog and persists the matching snapshot.
- [ ] Add a Workbench test that cancelling the SAXS scope chooser performs no database write.
- [ ] Run the focused tests and confirm the new tests fail because the options helper and chooser path do not yet exist.

### Task 3: Implement the smallest GREEN path

**Files:**
- Modify: `polynexus/core/scientific_review.py`
- Modify: `polynexus/gui/main_window_results_mixin.py`
- Modify: `polynexus/gui/i18n.py`

- [ ] Add `review_scope_options_for_context()` without changing `review_scope_for_context()` or any required decision keys.
- [ ] Use `QInputDialog.getItem()` only when multiple scopes are returned; keep existing non-SAXS dialog flow unchanged.
- [ ] Show the review action when a scope option exists, require a persisted run, and leave cancellation side-effect free.
- [ ] Add translated chooser title/prompt strings without embedding scientific decision text.
- [ ] Run the focused tests and confirm all pass.

### Task 4: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-31-saxs-workbench-scientific-review-entry.md`
- Create: `docs/acceptance/2026-07-31-saxs-workbench-scientific-review-entry.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Run the focused scientific-review and Workbench tests.
- [ ] Run the SAXS matrix with a complete summary and exit code.
- [ ] Run `python scripts/verify.py --task ... --changed --types` and `git diff --check`.
- [ ] Run storage report and clean dry-run only; do not use `--apply`.
- [ ] Review the diff and create an explicit allowlist checkpoint with `scripts/auto_commit.py`.
