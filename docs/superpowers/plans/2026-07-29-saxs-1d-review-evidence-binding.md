# SAXS 1D reviewer evidence binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind an explicit `saxs.1d` reviewer record to existing temperature SAXS 1D Figure evidence without changing scientific or publication decisions.

**Architecture:** Add an optional review payload to `SAXSConfig`. Keep source matching and the detached snapshot in the existing core Figure-evidence adapter, reusing `ScientificReviewRecord` validation and promotion reasons. Thread the payload only through temperature Figure providers; leave all roles and analysis outputs untouched.

**Tech Stack:** Python dataclasses, NumPy-backed SAXS DTOs, Pytest, strict JSON projection, Ruff, and `scripts/verify.py`.

---

### Task 1: Lock the review binding contract with RED tests

**Files:**
- Create: `tests/test_saxs_1d_review_evidence_binding.py`
- Modify: `polynexus/core/saxs_engine/config.py`

- [ ] **Step 1: Write the failing tests**

Test a temperature Figure with two source paths and a complete accepted
`saxs.1d` payload. Assert the evidence snapshot is `review_accepted`, contains
both exact paths and original `source_index` values, is strict-JSON safe, and
does not change the existing publication roles. Add separate tests for a
missing payload, a malformed accepted payload, and an accepted record whose
source refs match only one frame; assert `review_missing`, `review_invalid`,
and `source_mismatch` respectively. Add a test that static/strain builders do
not gain the temperature review snapshot in this slice.

- [ ] **Step 2: Run the RED command**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_1d_review_red'
python -m pytest -q tests/test_saxs_1d_review_evidence_binding.py
```

Expected: collection succeeds and the new assertions fail because the config
payload and Figure-evidence binding are not implemented.

### Task 2: Implement the detached fail-closed snapshot

**Files:**
- Modify: `polynexus/core/saxs_engine/config.py`
- Modify: `polynexus/core/saxs_engine/figure_evidence.py`

- [ ] **Step 1: Add the optional config payload**

Add `scientific_review: Dict[str, Any] = field(default_factory=dict)` to
`SAXSConfig`. Keep it optional and JSON-compatible; an empty mapping means no
review was supplied.

- [ ] **Step 2: Add source-only review projection**

Implement a helper that restores the payload with
`review_record_from_payload()`, extracts only existing frame source values,
and evaluates every frame through the shared `promotion_decision()` contract.
Return a detached mapping with `allowed`, `reason`, `record_id`, `scope`,
`policy_version`, `source_ref`, `source_refs`, and per-frame decisions. Do not
recalculate metrics or mutate the input record, frames, or definitions.

- [ ] **Step 3: Extend Figure-evidence attachment**

Add an optional `scientific_review` argument to
`build_saxs_figure_evidence()` and `attach_saxs_figure_evidence()`. Include
the projected snapshot only when the caller supplies a mapping. Preserve the
existing acceptance-audit and AI projections byte-for-byte.

- [ ] **Step 4: Run the focused GREEN command**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_1d_review_green'
python -m pytest -q tests/test_saxs_1d_review_evidence_binding.py tests/test_saxs_figure_evidence_binding.py tests/test_saxs_acceptance_audit_surfaces.py
```

Expected: all focused review/evidence tests pass and existing role assertions
remain unchanged.

### Task 3: Thread the payload through temperature providers only

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_temperature.py`
- Modify: `polynexus/core/saxs_engine/figure_provider.py`
- Modify: `tests/test_saxs_1d_review_evidence_binding.py`

- [ ] **Step 1: Add the temperature-only payload handoff**

Read the optional mapping from the already-owned `engine.cfg` and pass it to
the existing temperature `attach_saxs_figure_evidence()` calls. Cover the
normal temperature provider and its established summary fallback. Do not add
the argument to static or strain provider calls.

- [ ] **Step 2: Run the complete focused matrix**

Run:

```powershell
$saxsReviewTests = @(
  'tests/test_saxs_1d_review_evidence_binding.py',
  'tests/test_saxs_figure_evidence_binding.py',
  'tests/test_saxs_temperature_guinier_evidence.py',
  'tests/test_saxs_workbench_series_evidence.py',
  'tests/test_scientific_review.py'
)
python -m pytest -q $saxsReviewTests
```

Expected: a final pytest summary with zero failures and only previously known
warnings, if any.

### Task 4: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-29-saxs-1d-review-evidence-binding.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Run structured verification**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-1d-review-evidence-binding.md --changed --types
```

- [ ] **Step 2: Run exact SAXS verification and diff audit**

```powershell
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests
git diff --check
```

Count a pass only from the final pytest summary and exit code `0`. Record any
timeout or active-process limitation verbatim.

- [ ] **Step 3: Inspect storage without mutation**

```powershell
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

Do not run `test_storage.py --apply` and do not include test directories in
the code checkpoint.

- [ ] **Step 4: Create the explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "feat(saxs): bind 1d reviewer evidence" --files polynexus/core/saxs_engine/config.py polynexus/core/saxs_engine/figure_evidence.py polynexus/core/saxs_engine/figure_temperature.py polynexus/core/saxs_engine/figure_provider.py tests/test_saxs_1d_review_evidence_binding.py docs/superpowers/specs/2026-07-29-saxs-1d-review-evidence-binding-design.md docs/superpowers/plans/2026-07-29-saxs-1d-review-evidence-binding.md docs/agent/tasks/2026-07-29-saxs-1d-review-evidence-binding.md docs/agent/memory/active-work.md
```

The checkpoint must exclude `docs/agent/memory/current-state.md`, GUI review
files, `.superpowers`, scratch directories, and all test-storage paths.
