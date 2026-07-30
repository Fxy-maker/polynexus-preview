# SAXS Workbench Detector Provenance Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (inline execution). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show existing raw-detector structural audit evidence in SAXS Workbench without changing scientific semantics.

**Architecture:** Add a pure presentation helper beside the existing SAXS review-text helpers. It reads only the acceptance-audit projection and returns risk/next strings; `build_saxs_results_presentation()` composes those strings with the existing sections.

**Tech Stack:** Python mappings, localized fallback text, pytest, repository verifier.

---

### Task 1: Write and run RED tests

**Files:**
- Create: `tests/test_saxs_workbench_detector_provenance_audit.py`

- [x] **Step 1: Add focused tests**

```python
def test_workbench_shows_review_required_detector_provenance():
    presentation = build_saxs_results_presentation(
        {"scientific_acceptance_audit": {"detector_provenance_audit": {
            "raw_detector_quality_report": [{
                "status": "review_required", "level": "Diagnostic",
                "geometry": {"validity": "not_assessed"},
                "mask": {"validity": "not_assessed"},
                "reason_codes": ["geometry_validity_not_assessed", "mask_validity_not_assessed"],
            }]
        }}},
        submodule="saxs.temperature", language="en",
    )
    assert "Detector provenance audit" in presentation.risk_text
    assert "review_required" in presentation.risk_text
    assert "geometry=not_assessed" in presentation.risk_text
    assert "mask=not_assessed" in presentation.risk_text
    assert "calibration" in presentation.next_text.lower()

def test_structurally_consistent_provenance_is_advisory_not_risk():
    presentation = build_saxs_results_presentation(
        {"scientific_acceptance_audit": {"detector_provenance_audit": {
            "raw_detector_quality_report": [{
                "status": "structurally_consistent", "level": "Trend",
                "geometry": {"validity": "validated"},
                "mask": {"validity": "validated"}, "reason_codes": [],
            }]
        }}},
        submodule="saxs.static", language="en",
    )
    assert "Detector provenance audit" not in presentation.risk_text
    assert "structural evidence" in presentation.next_text

def test_malformed_detector_audit_does_not_mutate_generic_metric_review():
    params = {"metric_evidence": {"porod": {"level": "Trend", "frame_count": 1}},
              "scientific_acceptance_audit": {"detector_provenance_audit": "bad"}}
    before = deepcopy(params)
    presentation = build_saxs_results_presentation(params, submodule="saxs.static", language="en")
    assert "Detector provenance audit" not in presentation.risk_text
    assert "Porod" in presentation.next_text or not presentation.next_text
    assert params == before
```

- [x] **Step 2: Run RED**

```powershell
python -m pytest -q tests/test_saxs_workbench_detector_provenance_audit.py -vv --basetemp D:\PolyNexus_saxs_workbench_detector_provenance_audit_red
```

Expected: the new detector-audit text assertions fail because the Workbench
does not yet consume `detector_provenance_audit`.

### Task 2: Implement the presentation helper

**Files:**
- Modify: `polynexus/gui/saxs_results_table_service.py`

- [x] **Step 1: Add `_detector_provenance_audit_review_text`**

The helper must validate `scientific_acceptance_audit`, then the
`detector_provenance_audit` mapping, then the
`raw_detector_quality_report` list. For each mapping record, read only
`status`, `level`, `geometry.validity`, `mask.validity`, and up to five string
reason codes. Return empty strings when no valid record exists.

- [x] **Step 2: Compose the returned sections**

Call the helper in `build_saxs_results_presentation()` and add its returned
values after `audit_risk/audit_next`. Risk is emitted only for
`review_required` or `unusable`; next text is emitted for every valid record.

- [x] **Step 3: Run GREEN**

```powershell
python -m pytest -q tests/test_saxs_workbench_detector_provenance_audit.py --basetemp D:\PolyNexus_saxs_workbench_detector_provenance_audit_green
```

Expected: all focused tests pass.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-30-saxs-workbench-detector-provenance-audit.md`
- Create: `docs/acceptance/2026-07-30-saxs-workbench-detector-provenance-audit.md`

- [x] **Step 1: Run consumer matrix**

Run the exact consumer command in the task card and require a complete pytest
summary and exit code.

- [x] **Step 2: Run structured verifier and diff check**

Record task/memory, Ruff, compile, type baseline, quality/preprocessing, and
whitespace results. Existing unrelated parallel failures remain outside the
allowlist and are recorded as limitations.

- [x] **Step 3: Record acceptance evidence and checkpoint**

Update the task/acceptance files and run:

```powershell
python scripts/auto_commit.py --message "feat(saxs): show detector provenance audit" --files polynexus/gui/saxs_results_table_service.py tests/test_saxs_workbench_detector_provenance_audit.py docs/superpowers/specs/2026-07-30-saxs-workbench-detector-provenance-audit-design.md docs/superpowers/plans/2026-07-30-saxs-workbench-detector-provenance-audit.md docs/agent/tasks/2026-07-30-saxs-workbench-detector-provenance-audit.md docs/acceptance/2026-07-30-saxs-workbench-detector-provenance-audit.md
```
