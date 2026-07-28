# SAXS Guinier source-index integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make malformed or duplicated Guinier frame-to-source mappings diagnostic while preserving legitimate temperature sorting.

**Architecture:** Add source-index integrity metadata to the existing immutable `GuinierSequenceEvidence` DTO and compute it in `build_guinier_sequence_evidence()`. The builder will inspect only the supplied mapping, reuse the current evidence level/reason-code contract, and leave temperature/Rg sequence data untouched.

**Tech Stack:** Python dataclasses, NumPy, pytest, existing SAXS quality contracts, repository verification scripts.

---

### Task 1: Add source-index integrity RED tests

**Files:**
- Modify: `tests/test_saxs_guinier_sequence_evidence.py`

- [x] **Step 1: Write the failing tests**

Add this test block to the existing sequence evidence suite:

```python
def test_duplicate_source_indices_are_diagnostic_with_original_positions():
    evidence = build_guinier_sequence_evidence(
        [170.0, 180.0], [_frame(4.0), _frame(4.2)], source_indices=[7, 7]
    )

    assert evidence.duplicate_source_index_indices == (0, 1)
    assert evidence.level is QualityLevel.DIAGNOSTIC
    assert "guinier_sequence_source_index_duplicate" in evidence.reason_codes
    assert evidence.metric.applicable is False


@pytest.mark.parametrize("source_indices", [[-1, 2], [1.5, 2]])
def test_invalid_source_indices_are_diagnostic_without_rewriting_values(source_indices):
    evidence = build_guinier_sequence_evidence(
        [170.0, 180.0], [_frame(4.0), _frame(4.2)], source_indices=source_indices
    )

    assert evidence.invalid_source_index_indices == (0,)
    assert evidence.level is QualityLevel.DIAGNOSTIC
    assert "guinier_sequence_source_index_invalid" in evidence.reason_codes


def test_reordered_source_indices_are_valid_provenance_after_temperature_sorting():
    evidence = build_guinier_sequence_evidence(
        [170.0, 180.0], [_frame(4.0), _frame(4.2)], source_indices=[1, 0]
    )

    assert evidence.level is QualityLevel.TREND
    assert evidence.relative_change_stats["source_index_order_reordered"] is True
    assert "guinier_sequence_source_index_duplicate" not in evidence.reason_codes
```

Import `pytest` in the test module if it is not already imported.

- [x] **Step 2: Run the tests to verify RED**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_guinier_source_index_red'
python -m pytest -q tests/test_saxs_guinier_sequence_evidence.py -k source_index
```

Expected before implementation: the duplicate/invalid tests fail because the
DTO has no source-index diagnostic fields and the reordered test fails because
the metadata key is absent.

### Task 2: Implement the minimal immutable provenance contract

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`

- [x] **Step 1: Extend the DTO and JSON round-trip**

Add `duplicate_source_index_indices: tuple[int, ...] = ()`,
`invalid_source_index_indices: tuple[int, ...] = ()`, and
`source_index_order_reordered: bool = False` to
`GuinierSequenceEvidence`. Normalize the two index fields in
`__post_init__` and parse them in `from_dict()` using `_int_tuple`.

- [x] **Step 2: Validate the supplied source mapping without inferring gaps**

After the existing `frame_source_indices` conversion, inspect the raw supplied
values only when `source_indices is not None`. Preserve the existing integer
conversion for valid integer-like values, but mark a position invalid when the
value is negative or conversion to an integer changes a finite numeric value.
Mark every position participating in a duplicate integer mapping. Compute
`source_index_order_reordered` as true only when a complete, valid mapping has
at least one descending adjacent pair.

Add these reason codes and include them in the level guard:

```python
if duplicate_source_index_indices:
    reasons.append("guinier_sequence_source_index_duplicate")
if invalid_source_index_indices:
    reasons.append("guinier_sequence_source_index_invalid")
source_index_mapping_invalid = bool(
    source_index_mapping_mismatch
    or duplicate_source_index_indices
    or invalid_source_index_indices
)
```

Use `source_index_mapping_invalid` for `source_index_mapping_valid`, the
`Diagnostic` level condition, and `metric.applicable`. Add
`source_index_order_reordered` to `relative_change_stats` and
`physical_checks`; it must not by itself affect the level.

- [x] **Step 3: Run the focused sequence suite**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_guinier_source_index_green'
python -m pytest -q tests/test_saxs_guinier_sequence_evidence.py
```

Expected: the full sequence evidence file passes, including existing length
mismatch and `[1, 0]` source-index preservation tests.

### Task 3: Verify, document, and checkpoint

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `tests/test_saxs_guinier_sequence_evidence.py`
- Add: `docs/agent/tasks/2026-07-28-saxs-guinier-source-index-integrity.md`
- Add: `docs/superpowers/specs/2026-07-28-saxs-guinier-source-index-integrity-design.md`
- Add: `docs/superpowers/plans/2026-07-28-saxs-guinier-source-index-integrity.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run the propagation matrix and structured checks**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_guinier_source_index_focus'
python -m pytest -q tests/test_saxs_guinier_sequence_evidence.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_temperature_invalid_axis_fail_closed.py tests/test_saxs_temperature_invalid_time_values_fail_closed.py tests/test_saxs_mode_evidence_propagation.py
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-guinier-source-index-integrity.md --changed --types
git diff --check
python scripts/test_storage.py report --json
```

The storage command is dry-run only; record artifact counts and zero removals.

- [x] **Step 2: Run the exact SAXS matrix with an external basetemp**

Resolve `tests/test_saxs_*.py` through PowerShell and pass the resulting file
list to pytest. Record a fresh summary only; timeout/no-summary is not pass.

- [x] **Step 3: Update durable memory and create the explicit allowlist checkpoint**

Record exact results and limitations in the task card and
`docs/agent/memory/active-work.md`, then run:

```powershell
python scripts/auto_commit.py --message "fix(saxs): diagnose invalid Guinier source mappings" --files polynexus/core/saxs_engine/saxs_quality_contracts.py tests/test_saxs_guinier_sequence_evidence.py docs/agent/tasks/2026-07-28-saxs-guinier-source-index-integrity.md docs/superpowers/specs/2026-07-28-saxs-guinier-source-index-integrity-design.md docs/superpowers/plans/2026-07-28-saxs-guinier-source-index-integrity.md docs/agent/memory/active-work.md
```
