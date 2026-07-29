# SAXS 2D Reviewer Evidence Consumer Propagation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Carry the existing fail-closed `saxs.2d` reviewer evidence through result, bundle, and persisted Figure consumers.

**Architecture:** Reuse the existing `build_saxs_review_evidence()` source-matching projection. Add one engine-facing adapter that builds frame views without analysis, then let the result contract and bundle exporter store the same detached snapshot. Figure persistence already serializes recipe evidence into its document and V2 sidecar, while existing generic GUI consumers read the result snapshot.

**Tech Stack:** Python, dataclasses/mappings, NumPy JSON sanitization, pytest, repository verifier, explicit-allowlist checkpoint helper.

---

### Task 1: Create consumer-boundary RED coverage

**Files:**
- Create: `tests/test_saxs_2d_review_consumer_propagation.py`

- [x] **Step 1: Write failing tests**

  Add tests for: a valid 2D review reaching result/export; persisted Figure
  document and V2 sidecar equality; and fail-closed missing/scope/source cases.
  Build a minimal engine fixture using existing SAXS test helpers and set only
  `cfg.scientific_review`; assert `scientific_review` is absent or blocked
  before the implementation is added.

- [x] **Step 2: Run RED**

  Run:

  ```powershell
  python -m pytest -q tests/test_saxs_2d_review_consumer_propagation.py -vv
  ```

  Expected: functional failures showing that result parameters and
  `quality_evidence.json` do not yet contain the 2D reviewer snapshot.

### Task 2: Add one detached engine-facing projection

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_evidence.py`
- Test: `tests/test_saxs_2d_review_consumer_propagation.py`

- [x] **Step 1: Implement the smallest adapter**

  Add `configured_saxs_review_evidence(source, frames)` that reads the existing
  config mapping, selects its declared validated scope, and delegates to
  `build_saxs_review_evidence()` with the supplied frame views. For an absent or
  invalid record return the existing fail-closed shape; never return the raw
  config mapping.

- [x] **Step 2: Run focused GREEN**

  Run the RED module again and expect all new consumer assertions to pass.

### Task 3: Bind result contract and authoritative bundle

**Files:**
- Modify: `polynexus/core/saxs_result_contract.py`
- Modify: `polynexus/core/saxs_export_bundle.py`
- Test: `tests/test_saxs_2d_review_consumer_propagation.py`

- [x] **Step 1: Publish the detached snapshot**

  Build frame views from the current engine state, call the adapter, and put the
  JSON-safe result under `result.parameters["scientific_review"]`. Add the same
  detached value to `_quality_evidence_payload()` so the bundle's existing
  `quality_evidence.json` and `bundle_manifest.files` remain authoritative.

- [x] **Step 2: Verify GREEN and no mutation**

  Assert source config and frame parameters are unchanged, strict
  `json.dumps(..., allow_nan=False)` succeeds, and missing/wrong-source cases
  remain disallowed.

### Task 4: Verify Figure persistence and generic consumers

**Files:**
- Modify: `tests/test_saxs_2d_review_consumer_propagation.py`

- [x] **Step 1: Exercise FigurePipeline**

  Create a detector FigureDefinition through the existing provider, run the
  pipeline, and assert the `saxs.2d` evidence is present and equal in
  `figure.pnfig.json` and `reactive_figure_v2.json`; assert manifest status and
  publication role are unchanged.

- [x] **Step 2: Exercise Workbench/History/Export adapters**

  Pass the result snapshot through the existing GUI presentation helpers and
  assert the display remains read-only and includes the scope/record identity.

### Task 5: Verification and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-29-saxs-2d-review-consumer-propagation.md`
- Modify: `docs/superpowers/plans/2026-07-29-saxs-2d-review-consumer-propagation.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run focused and structured verification**

  Run the focused module, the adjacent Figure/2D/Workbench/Export/History
  matrix, and:

  ```powershell
  python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-2d-review-consumer-propagation.md --changed --types
  ```

- [x] **Step 2: Run exact SAXS and storage dry-run**

  Run the repository's exact SAXS test selection and both `report` and
  non-apply `clean` storage commands. Record only final pytest exit codes and
  summaries; never run `test_storage.py --apply`.

- [x] **Step 3: Audit allowlist and checkpoint**

  Update task/plan/memory with real evidence, verify `git diff --check`, then
  call `scripts/auto_commit.py` with an explicit allowlist containing only this
  task's files. Confirm the resulting commit hash and leave all pre-existing
  parallel/scratch files untouched.
