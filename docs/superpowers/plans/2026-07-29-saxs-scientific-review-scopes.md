# SAXS Scientific Review Scopes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add independent `saxs.1d` and `saxs.2d` reviewer-owned scopes to the existing immutable scientific review contract.

**Architecture:** Reuse `ScientificReviewRecord`, `_REQUIRED_DECISION_KEYS`,
and `promotion_decision`. Only the shared scope registry and required-key map
change; no SAXS engine or consumer imports the records in this slice. Tests use
real records and the existing pure gate.

**Tech Stack:** Python dataclasses, pytest, JSON-safe mapping validation, and
the repository verifier.

---

### Task 1: Add RED coverage for both SAXS scopes

**Files:**
- Modify: `tests/test_scientific_review.py`

- [x] **Step 1: Add one complete-record helper per scope.** Use the exact
  scope names and keys from the spec; use finite primitive values and one
  source reference per record.

```python
def _accepted_saxs_1d_record() -> ScientificReviewRecord:
    return ScientificReviewRecord(
        record_id="review-saxs-1d-1",
        scope="saxs.1d",
        reviewer="reviewer-saxs",
        reviewed_at="2026-07-29",
        policy_version="saxs-1d-v1",
        source_refs=("saxs-run-1",),
        decisions={
            "sequence_axis_policy": "review supplied temperature axis",
            "frame_identity_policy": "source_index is authoritative",
            "missing_repeat_policy": "retain missing status",
            "metric_claim_scope": ["Rg", "Porod"],
            "promotion_rule": "reviewed source and existing gates",
        },
        status="accepted",
    )


def _accepted_saxs_2d_record() -> ScientificReviewRecord:
    return ScientificReviewRecord(
        record_id="review-saxs-2d-1",
        scope="saxs.2d",
        reviewer="reviewer-saxs",
        reviewed_at="2026-07-29",
        policy_version="saxs-2d-v1",
        source_refs=("pad8-run-1",),
        decisions={
            "geometry_reference": "reviewed calibration record",
            "beam_center_policy": "reviewed detector coordinates",
            "mask_policy": "reviewed beamstop mask",
            "saturation_policy": "saturation status retained",
            "orientation_applicability": "orientation evidence applicable",
            "promotion_rule": "reviewed source and existing gates",
        },
        status="accepted",
    )
```

- [x] **Step 2: Add assertions for scope registration, accepted promotion,
  pending omission, missing-key rejection, and cross-scope denial.** The tests
  must assert `review_accepted`, `review_pending`, and `missing required
  decisions` rather than inspecting implementation details.

- [x] **Step 3: Run the focused test file to observe RED.**

Run:

```powershell
python -m pytest -q tests/test_scientific_review.py
```

Observed: `5 failed, 10 passed`; every new failure was caused by the two scope
names not being in `REVIEW_SCOPES`.

### Task 2: Implement the minimal shared scope extension

**Files:**
- Modify: `polynexus/core/scientific_review.py`

- [x] **Step 1: Add the two scope names.** Extend `REVIEW_SCOPES` with exactly
  `saxs.1d` and `saxs.2d`; leave all existing names unchanged.

- [x] **Step 2: Add the required-key tuples.** Add the exact keys below to
  `_REQUIRED_DECISION_KEYS`:

```python
"saxs.1d": (
    "sequence_axis_policy",
    "frame_identity_policy",
    "missing_repeat_policy",
    "metric_claim_scope",
    "promotion_rule",
),
"saxs.2d": (
    "geometry_reference",
    "beam_center_policy",
    "mask_policy",
    "saturation_policy",
    "orientation_applicability",
    "promotion_rule",
),
```

- [x] **Step 3: Run focused GREEN.**

Run:

```powershell
python -m pytest -q tests/test_scientific_review.py
```

Observed: `15 passed in 0.11s`; no SAXS engine consumer was changed.

### Task 3: Verify the boundary and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-29-saxs-scientific-review-scopes.md`
- Modify: `docs/acceptance/2026-07-29-saxs-scientific-review-scopes.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run focused and structured verification.** Record exact exit
  codes and counts; do not claim a full pass from a timeout or stale output.

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-scientific-review-scopes.md --changed --types
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName })
git diff --check
```

- [x] **Step 2: Update the acceptance and active-work records** with the fresh
  focused, verifier, SAXS matrix, and diff results. Preserve the explicit
  limitation that no real scientific promotion has occurred.

- [x] **Step 3: Create one explicit allowlist checkpoint only after all checks
  pass.**

The shared worktree contains unrelated same-file policy/provenance edits. The
repository helper would stage complete mixed files, so this checkpoint uses an
equivalent selective index allowlist and excludes all unrelated hunks.

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add SAXS scientific review scopes" `
  --files polynexus/core/scientific_review.py `
  tests/test_scientific_review.py `
  docs/superpowers/specs/2026-07-29-saxs-scientific-review-scopes-design.md `
  docs/superpowers/plans/2026-07-29-saxs-scientific-review-scopes.md `
  docs/agent/tasks/2026-07-29-saxs-scientific-review-scopes.md `
  docs/acceptance/2026-07-29-saxs-scientific-review-scopes.md `
  docs/agent/memory/active-work.md
```

The checkpoint must exclude `docs/agent/memory/current-state.md`, GUI files,
untracked visibility work, `.superpowers`, and every test-storage directory.

## Self-review

- All spec requirements map to Tasks 1-3.
- No step relies on a placeholder or an undefined function.
- The scope names and decision key names are identical in the spec, task, plan,
  and planned implementation.
- No consumer integration or scientific threshold is hidden in this schema
  slice.
