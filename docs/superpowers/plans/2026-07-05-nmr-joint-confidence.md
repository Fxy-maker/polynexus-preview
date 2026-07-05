# NMR and Joint Confidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build structured ssNMR confidence evidence first, then let Joint analysis consume single-technique confidence when explaining cross-technique conflicts.

**Architecture:** Extend the existing evidence-first architecture. NMR evidence is generated in `polynexus/core/analysis_evidence.py` from existing NMR parameters, with a small NMR parameter export improvement in `polynexus/core/nmr_engine/core.py`. Joint confidence is generated in `polynexus/core/joint/dataset.py` from each row's existing `parameters` and `results_summary`, avoiding a database migration.

**Tech Stack:** Python, pytest, existing PolyNexus core engines, existing sample DB and Joint Hub APIs.

---

## File Structure

- Modify `polynexus/core/analysis_evidence.py`: add NMR-specific evidence extraction, constraints, symptoms, and summary fields.
- Modify `polynexus/core/nmr_engine/core.py`: expose per-peak `phase`, `delta_ppm`, and `possible_solvent` fields in `NMRResult.parameters`.
- Modify `polynexus/core/joint/dataset.py`: add per-technique confidence summaries and richer Joint AI context.
- Modify `tests/test_analysis_evidence.py`: add NMR evidence and symptom tests.
- Modify `tests/test_nmr_engine.py`: add NMR parameter export test for phase and assignment support.
- Modify `tests/test_joint_hub_dataset.py`: add Joint confidence context tests.
- Optionally modify `polynexus/orchestrator.py`: add NMR confidence snapshot only if the evidence summary is not already enough for scoring.

---

### Task 1: NMR Evidence Sections

**Files:**
- Modify: `tests/test_analysis_evidence.py`
- Modify: `polynexus/core/analysis_evidence.py`

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_analysis_evidence.py`:

```python
def test_nmr_analysis_evidence_surfaces_signal_peak_assignment_sections() -> None:
    evidence = build_analysis_evidence(
        "NMR",
        output_parameters={
            "nucleus": "13C",
            "sample_state": "solid",
            "n_peaks": 4,
            "median_snr": 9.5,
            "mean_fwhm_ppm": 1.8,
            "r_squared": 0.91,
            "dominant_peak_ppm": 172.4,
            "peak_area_total": 120.0,
            "quality_noise_mad": 0.012,
            "quality_fit_quality": 2.0,
            "peak_0_assignment": "C=O (c)",
            "peak_0_phase": "c",
            "peak_0_delta_ppm": 0.4,
            "peak_0_snr": 12.0,
            "peak_1_assignment": "C=O (a)",
            "peak_1_phase": "a",
            "peak_1_delta_ppm": 0.8,
            "peak_1_snr": 10.0,
            "Xc_pct": 47.0,
            "Xc_method": "solid_13c_peak_area",
            "n_matches": 2,
        },
        residual_pattern={"residual_type": "noise", "summary": "noise remains"},
    ).to_dict()

    assert evidence["technique"] == "NMR"
    assert evidence["signal_evidence"]["median_snr"] == 9.5
    assert evidence["peak_evidence"]["peak_count"] == 4
    assert evidence["assignment_evidence"]["phase_assignment_count"] == 2
    assert evidence["assignment_evidence"]["assigned_peak_fraction"] > 0
    assert evidence["phase_evidence"]["crystalline_peak_count"] == 1
    assert evidence["phase_evidence"]["amorphous_peak_count"] == 1
    assert evidence["structure_evidence"]["Xc_assignment_status"] == "supported"
    assert "nmr_xc=supported" in evidence["summary"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_analysis_evidence.py::test_nmr_analysis_evidence_surfaces_signal_peak_assignment_sections -q`

Expected: FAIL because NMR evidence sections do not yet expose these fields.

- [ ] **Step 3: Implement minimal NMR evidence extraction**

In `polynexus/core/analysis_evidence.py`, add helper logic near the other evidence helpers:

```python
def _nmr_peak_rows(output: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx in range(10):
        ppm = _clean_float(output.get(f"peak_{idx}_ppm"))
        assignment = str(output.get(f"peak_{idx}_assignment") or "").strip()
        phase = str(output.get(f"peak_{idx}_phase") or "").strip().lower()
        if ppm is None and not assignment and not phase:
            continue
        rows.append(
            _non_empty_mapping(
                [
                    ("index", idx),
                    ("ppm", ppm),
                    ("assignment", assignment or None),
                    ("phase", phase or None),
                    ("snr", _clean_float(output.get(f"peak_{idx}_snr"))),
                    ("fwhm_ppm", _clean_float(output.get(f"peak_{idx}_fwhm_ppm"))),
                    ("area", _clean_float(output.get(f"peak_{idx}_area"))),
                    ("delta_ppm", _clean_float(output.get(f"peak_{idx}_delta_ppm"))),
                    ("possible_solvent", str(output.get(f"peak_{idx}_possible_solvent") or "").strip() or None),
                ]
            )
        )
    return rows
```

Then inside `build_analysis_evidence()` for `technique_key == "NMR"`, populate `signal_evidence`, `peak_evidence`, `assignment_evidence`, `phase_evidence`, and `structure_evidence` using existing output keys.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_analysis_evidence.py::test_nmr_analysis_evidence_surfaces_signal_peak_assignment_sections -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_analysis_evidence.py polynexus/core/analysis_evidence.py
git commit -m "feat: add NMR confidence evidence sections"
```

---

### Task 2: NMR Parameter Export for Phase and Match Evidence

**Files:**
- Modify: `tests/test_nmr_engine.py`
- Modify: `polynexus/core/nmr_engine/core.py`

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_nmr_engine.py`:

```python
def test_nmr_result_parameters_include_phase_and_match_evidence() -> None:
    from polynexus.core.nmr_engine.core import NMRResult

    result = NMRResult(nucleus="13C", sample_state="solid")
    result.peaks = [
        {
            "ppm": 172.0,
            "assignment": "C=O (c)",
            "phase": "c",
            "delta_ppm": 0.4,
            "snr": 12.0,
            "possible_solvent": "",
        },
        {
            "ppm": 170.5,
            "assignment": "C=O (a)",
            "phase": "a",
            "delta_ppm": 0.7,
            "snr": 9.0,
            "possible_solvent": "",
        },
    ]
    result.n_peaks = 2

    params = result.parameters

    assert params["peak_0_phase"] == "c"
    assert params["peak_1_phase"] == "a"
    assert params["peak_0_delta_ppm"] == 0.4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_nmr_engine.py::test_nmr_result_parameters_include_phase_and_match_evidence -q`

Expected: FAIL because `NMRResult.parameters` does not export `phase` or `delta_ppm`.

- [ ] **Step 3: Export the missing fields**

In `polynexus/core/nmr_engine/core.py`, extend the per-peak loop in `NMRResult.parameters`:

```python
p[f"peak_{i}_phase"] = pk.get("phase", "")
p[f"peak_{i}_delta_ppm"] = pk.get("delta_ppm", np.nan)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_nmr_engine.py::test_nmr_result_parameters_include_phase_and_match_evidence -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_nmr_engine.py polynexus/core/nmr_engine/core.py
git commit -m "feat: expose NMR assignment evidence in parameters"
```

---

### Task 3: NMR Constraints and Actionable Symptoms

**Files:**
- Modify: `tests/test_analysis_evidence.py`
- Modify: `polynexus/core/analysis_evidence.py`

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_analysis_evidence.py`:

```python
def test_nmr_low_confidence_symptoms_are_actionable() -> None:
    evidence = build_analysis_evidence(
        "NMR",
        output_parameters={
            "nucleus": "13C",
            "sample_state": "solid",
            "n_peaks": 1,
            "median_snr": 2.1,
            "mean_fwhm_ppm": 45.0,
            "quality_fit_quality": 0.0,
            "Xc_method": "requires_crystalline_amorphous_assignment",
        },
        residual_pattern={"residual_type": "structured", "summary": "structured residual"},
    ).to_dict()

    names = {item["name"] for item in evidence["symptoms"]}
    assert "nmr_low_snr" in names
    assert "nmr_broad_linewidth" in names
    assert "nmr_xc_assignment_missing" in names
    assert any("baseline" in item or "peak" in item for item in evidence["actionable_symptoms"])
    assert evidence["constraint_summary"]["status"] in {"soft_warn", "hard_fail"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_analysis_evidence.py::test_nmr_low_confidence_symptoms_are_actionable -q`

Expected: FAIL because these NMR symptoms do not yet exist.

- [ ] **Step 3: Add constraints and symptom construction**

In `physical_constraint_inventory("NMR")`, add constraints for low peak count, low SNR, broad linewidth, weak assignment, solvent risk, and missing Xc assignment. In `build_analysis_evidence()`, create symptom dictionaries like:

```python
{
    "name": "nmr_low_snr",
    "severity": "WARN",
    "summary": "NMR median SNR is too low for strong assignment confidence.",
    "target": "peak_height_min",
}
```

Also append actionable strings such as:

```python
"nmr_low_snr -> review baseline correction and peak threshold before trusting assignments"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_analysis_evidence.py::test_nmr_low_confidence_symptoms_are_actionable -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_analysis_evidence.py polynexus/core/analysis_evidence.py
git commit -m "feat: add NMR confidence symptoms"
```

---

### Task 4: Joint Technique Evidence Status

**Files:**
- Modify: `tests/test_joint_hub_dataset.py`
- Modify: `polynexus/core/joint/dataset.py`

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_joint_hub_dataset.py`:

```python
def test_joint_hub_report_surfaces_technique_evidence_status(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "annealed")
    db.create_analysis_run(
        batch_id,
        "dsc",
        results_summary={"Xc_pct": 42.0, "analysis_evidence": {"constraint_summary": {"status": "ok"}}},
    )
    db.create_analysis_run(
        batch_id,
        "nmr",
        results_summary={
            "Xc_pct": 45.0,
            "Xc_method": "requires_crystalline_amorphous_assignment",
            "analysis_evidence": {
                "constraint_summary": {"status": "soft_warn"},
                "structure_evidence": {"Xc_assignment_status": "assignment_limited"},
                "risk_flags": ["nmr_xc_assignment_missing"],
            },
        },
    )

    report = build_joint_hub_report(collect_joint_dataset(db))

    row = report["rows"][0]
    context = report["ai_context"]
    assert row["technique_confidence"]["nmr"]["status"] == "soft_warn"
    assert row["paper_conclusion_ready_by_technique"]["nmr"] is False
    assert "NMR assignment limited" in context["issue_families"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_joint_hub_dataset.py::test_joint_hub_report_surfaces_technique_evidence_status -q`

Expected: FAIL because Joint rows do not yet expose technique confidence summaries.

- [ ] **Step 3: Implement technique evidence summary**

In `polynexus/core/joint/dataset.py`, add helpers:

```python
def _run_analysis_evidence(run: JointRunRecord | None) -> dict[str, Any]:
    if not run:
        return {}
    for payload in (run.results_summary, run.parameters):
        if isinstance(payload, dict) and isinstance(payload.get("analysis_evidence"), dict):
            return payload["analysis_evidence"]
    return {}


def _technique_confidence(run: JointRunRecord | None) -> dict[str, Any]:
    evidence = _run_analysis_evidence(run)
    summary = evidence.get("constraint_summary", {}) if isinstance(evidence, dict) else {}
    status = str(summary.get("status") or "unknown").strip() or "unknown"
    risk_flags = evidence.get("risk_flags", []) if isinstance(evidence.get("risk_flags"), list) else []
    structure = evidence.get("structure_evidence", {}) if isinstance(evidence.get("structure_evidence"), dict) else {}
    paper_ready = bool(structure.get("paper_conclusion_ready", status == "ok"))
    if run and run.technique == "nmr" and structure.get("Xc_assignment_status") != "supported":
        paper_ready = False
    return {"status": status, "risk_flags": risk_flags, "paper_conclusion_ready": paper_ready}
```

Add `technique_confidence` and `paper_conclusion_ready_by_technique` to each summary row.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_joint_hub_dataset.py::test_joint_hub_report_surfaces_technique_evidence_status -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_joint_hub_dataset.py polynexus/core/joint/dataset.py
git commit -m "feat: surface technique confidence in joint reports"
```

---

### Task 5: Joint Context Downgrades Weak Xc Sources

**Files:**
- Modify: `tests/test_joint_hub_dataset.py`
- Modify: `polynexus/core/joint/dataset.py`

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_joint_hub_dataset.py`:

```python
def test_joint_context_downgrades_assignment_limited_nmr_xc(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "annealed")
    db.create_analysis_run(batch_id, "dsc", results_summary={"Xc_pct": 42.0})
    db.create_analysis_run(
        batch_id,
        "nmr",
        results_summary={
            "Xc_pct": 80.0,
            "Xc_method": "requires_crystalline_amorphous_assignment",
            "analysis_evidence": {
                "constraint_summary": {"status": "soft_warn"},
                "structure_evidence": {"Xc_assignment_status": "assignment_limited"},
            },
        },
    )

    report = build_joint_hub_report(collect_joint_dataset(db))

    assert report["ai_context"]["weak_xc_sources"]["nmr"] == "assignment_limited"
    assert "NMR assignment limited" in report["ai_context"]["issue_families"]
    assert "nmr" in report["ai_context"]["recommended_review_targets"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_joint_hub_dataset.py::test_joint_context_downgrades_assignment_limited_nmr_xc -q`

Expected: FAIL because `weak_xc_sources` and review targets do not exist.

- [ ] **Step 3: Add weak-source detection to Joint AI context**

In `_build_joint_ai_context()`, inspect summary row `technique_confidence` and Xc source fields. Add:

```python
"weak_xc_sources": weak_xc_sources,
"recommended_review_targets": recommended_review_targets,
```

When NMR `Xc_assignment_status != "supported"`, set `weak_xc_sources["nmr"] = "assignment_limited"` and include `NMR assignment limited` as an issue family.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_joint_hub_dataset.py::test_joint_context_downgrades_assignment_limited_nmr_xc -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_joint_hub_dataset.py polynexus/core/joint/dataset.py
git commit -m "feat: downgrade weak NMR crystallinity in joint context"
```

---

### Task 6: Targeted Regression

**Files:**
- No new files unless a regression exposes a missing test.

- [ ] **Step 1: Run NMR evidence tests**

Run: `pytest tests/test_analysis_evidence.py::test_nmr_analysis_evidence_surfaces_signal_peak_assignment_sections tests/test_analysis_evidence.py::test_nmr_low_confidence_symptoms_are_actionable tests/test_nmr_engine.py::test_nmr_result_parameters_include_phase_and_match_evidence -q`

Expected: all selected tests PASS.

- [ ] **Step 2: Run Joint confidence tests**

Run: `pytest tests/test_joint_hub_dataset.py -q`

Expected: all tests in `tests/test_joint_hub_dataset.py` PASS.

- [ ] **Step 3: Run nearby orchestrator/evidence smoke tests**

Run: `pytest tests/test_analysis_evidence.py tests/test_joint_hub_dataset.py tests/test_nmr_engine.py -q`

Expected: all selected tests PASS.

- [ ] **Step 4: Check Git status**

Run: `git status --short`

Expected: clean after all task commits.

---

## Self-Review

- Spec coverage: J-T2/J-T3/J-T4 are covered by Tasks 1-3. K-T2/K-T3/K-T5 are covered by Tasks 4-5. K-T1/J-T1 were completed as documentation baselines before this plan. GUI/export work remains intentionally minimal in this first implementation slice because existing summaries can consume the richer evidence dictionaries.
- Placeholder scan: no unfinished-marker or deferred implementation placeholders are used.
- Type consistency: `Xc_assignment_status`, `technique_confidence`, `weak_xc_sources`, and `recommended_review_targets` are used consistently across tests and implementation notes.
