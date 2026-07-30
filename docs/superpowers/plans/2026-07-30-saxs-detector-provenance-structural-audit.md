# SAXS Detector Provenance Structural Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Project existing raw-detector geometry and mask provenance into a conservative, strict-JSON structural audit.

**Architecture:** Keep the behavior in `saxs_quality_contracts.py` beside the existing scientific acceptance audit. A private helper will inspect detached mappings and return one compact record; the existing recursive audit will attach it without changing source reports or downstream publication decisions.

**Tech Stack:** Python dataclasses/mappings, NumPy JSON-safe normalization, pytest, repository verifier.

---

### Task 1: Lock the structural audit contract with RED tests

**Files:**
- Create: `tests/test_saxs_detector_provenance_structural_audit.py`

- [x] **Step 1: Write the failing tests**

Add tests that call the existing `build_saxs_scientific_acceptance_audit` with
these reports:

```python
def test_validated_raw_detector_provenance_is_structurally_consistent():
    report = _raw_report(validity="validated")
    audit = build_saxs_scientific_acceptance_audit(True, {"raw_detector_quality_report": report})
    record = audit["detector_provenance_audit"]["raw_detector_quality_report"][0]
    assert record["status"] == "structurally_consistent"
    assert record["level"] == "Trend"
    assert record["geometry"]["missing_field_sources"] == []
    assert record["mask"]["shape_matches_detector"] is True

def test_unassessed_provenance_stays_review_required():
    report = _raw_report(validity="not_assessed")
    audit = build_saxs_scientific_acceptance_audit(True, {"raw_detector_quality_report": report})
    record = audit["detector_provenance_audit"]["raw_detector_quality_report"][0]
    assert record["status"] == "review_required"
    assert record["level"] == "Diagnostic"
    assert "geometry_validity_not_assessed" in record["reason_codes"]

def test_invalid_or_mismatched_provenance_fails_closed():
    report = _raw_report(validity="invalid", mask_shape=[3, 3])
    audit = build_saxs_scientific_acceptance_audit(True, {"raw_detector_quality_report": report})
    record = audit["detector_provenance_audit"]["raw_detector_quality_report"][0]
    assert record["status"] == "unusable"
    assert record["level"] == "Unusable"
    assert "mask_shape_mismatch" in record["reason_codes"]

def test_sector_map_does_not_receive_raw_detector_provenance():
    audit = build_saxs_scientific_acceptance_audit(True, {"detector_quality_report": {"source_kind": "sector_map"}})
    assert "detector_provenance_audit" not in audit

def test_structural_audit_is_detached_and_strict_json_safe():
    report = _raw_report(validity="validated")
    audit = build_saxs_scientific_acceptance_audit(True, {"raw_detector_quality_report": report})
    report["geometry_provenance"]["field_sources"]["sdd_m"] = "mutated"
    assert audit["detector_provenance_audit"]["raw_detector_quality_report"][0]["geometry"]["field_sources"]["sdd_m"] == "header"
    json.dumps(audit, allow_nan=False)
```

The helper fixture must use shape `[2, 2]`, pixel count `4`, valid pixel count
`3`, matching mask shape `[2, 2]`, all five required geometry field sources,
and the same validity value for geometry and mask. The invalid test changes
the mask shape to `[3, 3]` while retaining the detector shape.

- [x] **Step 2: Run RED**

Run:

```powershell
python -m pytest -q tests/test_saxs_detector_provenance_structural_audit.py -vv --basetemp D:\PolyNexus_saxs_detector_provenance_structural_audit_red
```

Expected: collection succeeds and the new projection-key assertions fail
because the acceptance audit does not yet emit `detector_provenance_audit`.

### Task 2: Implement the minimal read-only projection

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py` near `build_saxs_scientific_acceptance_audit`

- [x] **Step 1: Add a private mapping helper**

Implement `_audit_raw_detector_provenance(report)` with this deterministic
shape:

```python
{
    "status": "structurally_consistent|review_required|unusable",
    "level": "Trend|Diagnostic|Unusable",
    "source_kind": "raw_detector",
    "reason_codes": [...],
    "geometry": {"validity": ..., "source": ..., "field_sources": {...}, "missing_field_sources": [...]},
    "mask": {"validity": ..., "source": ..., "configured": ..., "shape": ..., "shape_matches_detector": ...},
}
```

Use only mapping values already supplied in `report`. Require the field-source
names `wavelength_m`, `pixel_size_m`, `sdd_m`, `beam_center_x`, and
`beam_center_y`; treat absent values as review-required, never as defaults.
Treat `invalid`, shape/count contradictions, and mask mismatch as unusable.
Treat `validated` as structurally consistent only when no contradiction exists.
Keep all other validity values review-required.

- [x] **Step 2: Attach the projection during recursive inspection**

Inside the existing audit traversal, inspect only
`raw_detector_quality_report`:

```python
detector_audit = _audit_raw_detector_provenance(report)
if detector_audit is not None:
    detector_provenance_audit.setdefault(field_name, []).append(detector_audit)
```

Add `detector_provenance_audit` to the returned strict-JSON mapping. Do not
change existing status/reason logic or the input mappings.

- [x] **Step 3: Run GREEN**

Run the focused test command from Task 1. Expected: all focused tests pass and
the output contains no non-finite JSON values.

### Task 3: Verify and record the atomic checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-30-saxs-detector-provenance-structural-audit.md`
- Create: `docs/acceptance/2026-07-30-saxs-detector-provenance-structural-audit.md`

- [x] **Step 1: Run the exact SAXS matrix**

```powershell
python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName) --basetemp D:\PolyNexus_saxs_detector_provenance_structural_audit_saxs_matrix
```

Record only a complete pytest summary and exit code.

- [x] **Step 2: Run the structured verifier and diff check**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-detector-provenance-structural-audit.md --changed --types
git diff --check
```

Record unrelated parallel failures as limitations; do not add their files to
the allowlist.

- [x] **Step 3: Write acceptance evidence**

Record RED/GREEN, focused and SAXS matrix results, verifier limitations,
storage behavior, and the unchanged scientific boundaries. Mark the task
complete only after those results are real.

- [x] **Step 4: Create the explicit checkpoint**

```powershell
python scripts/auto_commit.py `
  --message "feat(saxs): audit detector provenance structure" `
  --files polynexus/core/saxs_engine/saxs_quality_contracts.py `
          tests/test_saxs_detector_provenance_structural_audit.py `
          docs/superpowers/specs/2026-07-30-saxs-detector-provenance-structural-audit-design.md `
          docs/superpowers/plans/2026-07-30-saxs-detector-provenance-structural-audit.md `
          docs/agent/tasks/2026-07-30-saxs-detector-provenance-structural-audit.md `
          docs/acceptance/2026-07-30-saxs-detector-provenance-structural-audit.md
```

The checkpoint must not include current-state, active-work, scratch, or
parallel NMR/Joint files.
