# SAXS Workbench Detector Evidence Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Project existing raw-detector and sector-map quality evidence into the SAXS Results Workbench as conservative review context.

**Architecture:** Keep detector evidence production and persistence in the core. Add one pure formatter in `saxs_results_table_service.py`, call it from the existing SAXS presentation builder, and concatenate its output with the existing metric/axis/Guinier review channels. The formatter reads only persisted mappings and never recomputes detector state.

**Tech Stack:** Python, typed mapping contracts, PySide6 presentation DTOs, pytest, repository verifier.

---

### Task 1: Add the detector review RED tests

**Files:**
- Modify: `tests/test_saxs_results_table_service.py`

- [x] **Step 1: Add a raw-detector report fixture and assert the desired English review.**

Use the existing SAXS presentation test helpers and a parameter payload containing:

```python
{
    "raw_detector_quality_report": {
        "metric_name": "DetectorQuality",
        "source_kind": "raw_detector",
        "level": "Unusable",
        "frame_count": 5,
        "evidence_frame_count": 5,
        "coverage_fraction": 0.8,
        "reason_codes": ["detector_saturation_unknown", "beam_center_missing"],
    }
}
```

Call `build_saxs_results_presentation(..., submodule="saxs.temperature", language="en")` and assert that `risk_text` or `next_text` contains `raw detector`, `Unusable`, `5/5`, and the two existing reason codes. Assert the source text is separate from any sector-map text.

- [x] **Step 2: Add sector-only, dual-source, missing, partial, and Chinese cases.**

Assert `source_kind="sector_map"` is labeled sector-map evidence, both fields produce two source fragments, an absent report produces no detector-specific text, and Chinese output is deterministic. Deep-copy the input parameters before presentation and assert the original mapping is unchanged.

- [x] **Step 3: Run the focused tests to confirm RED.**

Run:

```powershell
python -m pytest -q tests/test_saxs_results_table_service.py -k detector -vv --basetemp C:\Temp\PolyNexus_saxs_workbench_detector_red
```

Expected: FAIL because the presentation builder does not yet consume detector reports.

### Task 2: Implement the pure Workbench formatter

**Files:**
- Modify: `polynexus/gui/saxs_results_table_service.py`

- [x] **Step 1: Add `_detector_evidence_review_text(payload, language)`.**

Read the two fields separately in this order: `raw_detector_quality_report`, then `detector_quality_report`. For each mapping, normalize only display values:

```python
source = "raw detector" if field == "raw_detector_quality_report" else "sector map"
level = str(report.get("level") or "Unusable")
evidence = _count(report, "evidence_frame_count")
total = _count(report, "frame_count")
coverage = _finite_fraction(report.get("coverage_fraction"))
reasons = _text_list(report.get("reason_codes"))[:3]
```

Build one deterministic source fragment containing source, level, `evidence/total`, optional percentage, and optional reasons. Do not sort frames, interpret geometry, or alter the report.

- [x] **Step 2: Add conservative risk/next-step behavior.**

Set the risk flag when the report level is `Diagnostic`/`Unusable`, evidence is incomplete, or reason codes are present. Return the existing translated `RESULTS_REVIEW_RISK` and `RESULTS_REVIEW_NEXT` wrappers with text telling the user to review detector provenance before using the result. Return an empty risk string and a detail next string for complete reports without reasons.

- [x] **Step 3: Combine it in `build_saxs_results_presentation`.**

Call the new formatter beside `_series_metric_review_text`, `_condition_axis_review_text`, and `_guinier_sequence_review_text`; concatenate non-empty detector risk/next text without changing existing ordering or payload data.

### Task 3: Verify and checkpoint

**Files:**
- Modify: the task card, spec, plan, and durable memory files in the explicit allowlist.

- [x] **Step 1: Run focused consumer tests.**

```powershell
python -m pytest -q tests/test_saxs_results_table_service.py tests/test_saxs_export_bundle.py tests/test_saxs_figure_evidence_binding.py -vv --basetemp C:\Temp\PolyNexus_saxs_workbench_detector_matrix
```

Expected: all selected tests pass; existing Figure/Export transport remains unchanged.

- [x] **Step 2: Run the exact SAXS matrix and structured verifier.**

Run the PowerShell-expanded `tests/test_saxs_*.py` matrix, then:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-workbench-detector-evidence-visibility.md --changed --types
git diff --check
```

Record exact exit codes, counts, warnings, and any timeout or basetemp limitation. Do not use the historical `2793` full result as fresh evidence.

- [x] **Step 3: Update durable memory and inspect the allowlist.**

Add one dated entry to `active-work.md` and `current-state.md` describing the Workbench-only projection and the continuing human geometry/mask limitation. Confirm `git diff --name-only` contains only allowlisted files and no scratch directories.

- [x] **Step 4: Create the explicit checkpoint.**

```powershell
python scripts/auto_commit.py `
  --message "feat(saxs): expose detector evidence in workbench" `
  --files docs/agent/tasks/2026-07-28-saxs-workbench-detector-evidence-visibility.md docs/superpowers/specs/2026-07-28-saxs-workbench-detector-evidence-visibility-design.md docs/superpowers/plans/2026-07-28-saxs-workbench-detector-evidence-visibility.md polynexus/gui/saxs_results_table_service.py tests/test_saxs_results_table_service.py docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

Record the resulting commit hash. Do not push, merge, clean untracked files, or include parallel GUI/editor/scratch changes.
