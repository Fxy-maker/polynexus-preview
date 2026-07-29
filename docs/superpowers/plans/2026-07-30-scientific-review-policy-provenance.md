# Scientific Review Policy Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the reviewer `policy_version` when a scientific review decision is converted into lifecycle evidence and display it in the shared GUI review text.

**Architecture:** Keep the immutable `ScientificReviewRecord` as the source of truth. Extend the technique-neutral decision snapshot with the record's existing `policy_version`, then let the presentation adapter render that detached field without adding technique-specific branches or changing promotion rules.

**Tech Stack:** Python dataclasses/mappings, PySide6 presentation adapters, pytest, repository verifier.

---

### Task 1: Lock the missing policy provenance with RED tests

**Files:**
- Modify: `tests/test_scientific_review.py`
- Modify: `tests/test_scientific_review_presentation.py`

- [x] **Step 1: Add a snapshot assertion**

Create an accepted `ScientificReviewRecord` with `policy_version="ir-map-v1"`, call `review_decision_snapshot(...)`, and assert the returned JSON-safe mapping contains that exact value.

- [x] **Step 2: Add a display assertion**

Pass an accepted nested review snapshot containing `policy_version="ir-map-v1"` to `scientific_review_display(...)` and assert both `display.policy_version` and `policy=ir-map-v1` are present.

- [x] **Step 3: Run the focused tests and verify RED**

Run:

```powershell
python -m pytest -q tests/test_scientific_review.py tests/test_scientific_review_presentation.py
```

Expected result: the new assertions fail because the snapshot and display currently omit `policy_version`.

### Task 2: Implement the minimal technique-neutral propagation

**Files:**
- Modify: `polynexus/core/scientific_review.py`
- Modify: `polynexus/gui/scientific_review_presentation.py`

- [x] **Step 1: Add policy version to the snapshot**

In `review_decision_snapshot`, return `policy_version` from the validated `ScientificReviewRecord` when present; keep missing/invalid records fail-closed and JSON-safe.

- [x] **Step 2: Render policy version in the shared display adapter**

Add a detached `policy_version` field to `ScientificReviewDisplay` and append `policy=<value>` to the display text only when the persisted snapshot provides a non-empty version.

- [x] **Step 3: Run the focused tests and verify GREEN**

Run the same focused command and confirm all tests pass without changing `allowed`, `reason`, scope matching, or publication roles.

### Task 3: Verify lifecycle compatibility and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-30-scientific-review-policy-provenance.md`
- Create: `docs/acceptance/2026-07-30-scientific-review-policy-provenance.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run focused, task-scoped, and whitespace verification**

```powershell
python -m pytest -q tests/test_scientific_review.py tests/test_scientific_review_presentation.py tests/test_results_table_service.py tests/test_export_context_service.py tests/test_history_table_service.py
python scripts/verify.py --task docs/agent/tasks/2026-07-30-scientific-review-policy-provenance.md --changed --types
git diff --check
```

- [x] **Step 2: Record the exact result and limitations**

State that this preserves audit metadata only. It does not create reviewer values, promote IR/NMR/Joint results, or close restarted-GUI and final-release gates.

- [x] **Step 3: Create an explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(review): preserve policy provenance" --files polynexus/core/scientific_review.py polynexus/gui/scientific_review_presentation.py tests/test_scientific_review.py tests/test_scientific_review_presentation.py docs/agent/tasks/2026-07-30-scientific-review-policy-provenance.md docs/acceptance/2026-07-30-scientific-review-policy-provenance.md docs/agent/memory/active-work.md
```

The repository helper would stage the complete mixed files and therefore mix
pre-existing SAXS scope edits. The checkpoint is staged with an equivalent
selective index allowlist instead. Do not include `current-state.md`, existing
SAXS edits, or any test-storage directory.

---

## Self-review

The plan covers the design requirement that the existing reviewer policy version
travels with the shared decision snapshot and presentation. It deliberately does
not define any scientific value, threshold, conflict policy, or release decision.
