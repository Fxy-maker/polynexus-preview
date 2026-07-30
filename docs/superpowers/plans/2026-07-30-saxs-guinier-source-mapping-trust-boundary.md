# SAXS Guinier Source-Mapping Trust Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent malformed temperature Guinier source mappings from being emitted as trusted frame or pair identities.

**Architecture:** Keep validation in the existing `build_guinier_sequence_evidence()` contract builder. Normalize raw values only after validation, reuse the existing reason/level logic, and leave all metric and axis calculations untouched.

**Tech Stack:** Python 3.14, dataclasses, NumPy finite checks, pytest, strict JSON DTOs, PolyNexus verifier scripts.

---

### Task 1: Add source-mapping trust regression tests

**Files:**
- Create: `tests/test_saxs_guinier_source_mapping_trust.py`
- Reference: `polynexus/core/saxs_engine/saxs_quality_contracts.py`

- [x] **Step 1: Write failing tests**

Add tests that call `build_guinier_sequence_evidence()` with two valid frame
payloads and assert:

```python
valid = build_guinier_sequence_evidence(
    [170.0, 180.0], [_frame(4.0), _frame(4.2)], source_indices=[7, 3]
)
assert valid.frame_source_indices == (7, 3)
assert valid.relative_change_stats["pair_source_indices"] == ((7, 3),)

invalid = build_guinier_sequence_evidence(
    [170.0, 180.0], [_frame(4.0), _frame(4.2)], source_indices=[-1, 3]
)
assert invalid.invalid_source_index_indices == (0,)
assert invalid.frame_source_indices == ()
assert invalid.relative_change_stats["pair_source_indices"] == ()
```

Parameterize duplicate `[7, 7]`, invalid `[True, 3]`, non-finite `[inf, 3]`,
non-integral `[1.5, 3]`, non-coercible `["bad", 3]`, and length-mismatched
`[7]`. Assert each has the existing Diagnostic level/reason and no trusted
mapping. Assert omitted mappings remain empty and JSON round-trip remains safe.

- [x] **Step 2: Run the focused tests to verify RED**

Run:

```powershell
python -m pytest -q tests/test_saxs_guinier_source_mapping_trust.py -o addopts= --basetemp=D:\PolyNexus_saxs_guinier_source_mapping_trust_red
```

Expected: invalid mappings still appear in `frame_source_indices` or their
pair identities because the current builder normalizes before clearing trust.

### Task 2: Implement the minimal trusted-mapping boundary

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py:1172-1365`
- Test: `tests/test_saxs_guinier_source_mapping_trust.py`

- [x] **Step 1: Validate raw values before integer normalization**

Build `raw_source_indices` exactly once. Record invalid positions for booleans,
non-finite, negative, non-integral, and non-coercible values. Detect duplicate
positions only for a complete valid mapping. Define `trusted_source_indices` as
the full integer tuple only when the supplied mapping has expected length and
no defects; otherwise use `()`.

- [x] **Step 2: Use trusted identities only for emitted mapping fields**

Set `frame_source_indices` in the returned DTO and
`relative_change_stats["frame_source_indices"]` to the trusted tuple. Build
`pair_source_indices` only when the trusted tuple covers `frame_count`. Keep
the existing diagnostic reason codes, level downgrade, and reordered flag.

- [x] **Step 3: Run focused GREEN and existing sequence tests**

Run:

```powershell
python -m pytest -q tests/test_saxs_guinier_source_mapping_trust.py tests/test_saxs_guinier_sequence_evidence.py tests/test_saxs_series_metric_source_integrity.py -o addopts= --basetemp=D:\PolyNexus_saxs_guinier_source_mapping_trust_green
```

Expected: all tests pass and the existing valid reordered mapping remains
`Trend` with its source order preserved.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-30-saxs-guinier-source-mapping-trust-boundary.md`
- Modify: `docs/acceptance/2026-07-30-saxs-guinier-source-mapping-trust-boundary.md`
- Create: `docs/agent/memory/lessons/2026-07-30-saxs-guinier-source-mapping-trust-boundary.md`

- [x] **Step 1: Run task verifier, exact SAXS matrix, storage dry-run, and diff check**

Use the commands recorded in the task card. Count a matrix as passed only with
a complete pytest summary and exit code `0`. Do not run `test_storage.py
--apply`; do not claim a full/boundary result unless it completes with both
summaries.

Evidence: the exact SAXS matrix passed `33 passed, 1 warning`; storage report
and dry-run clean found `57` artifacts with `6` eligible and removed `0`.
Task verification passed task/memory/Ruff/compile/type checks, but its shared
quality gate returned `288 passed, 2 failed, 3 warnings` because parallel NMR
changes currently emit Chinese scientific-review labels while two existing
history-table tests still expect English labels. Those NMR files are outside
this task and remain untouched.

- [ ] **Step 2: Create one explicit allowlist checkpoint**

Use `scripts/auto_commit.py` with only the source, focused test, task,
acceptance, spec, plan, and independent lesson files. Do not include the
parallel-modified `active-work.md`, NMR files, `current-state.md`, or scratch
directories.
