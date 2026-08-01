# SAXS AI Candidate-Reference Evidence Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transport the existing diagnostic SAXS AI candidate-reference resolution through Workbench, Figure/Manifest, and Export consumers.

**Architecture:** Store the latest detached resolution on the active SAXS engine/result and reuse the existing `copy_saxs_ai_rescue_evidence` channel. Keep the full per-round record in `RoundRecord.llm_advice`; consumer-specific adapters project the same record without recalculation or execution.

**Tech Stack:** Python mappings, existing SAXS DTOs, FigurePipeline provenance, Results Workbench presentation services, pytest, and the structured verifier.

---

### Task 1: Consumer RED coverage

**Files:**
- Modify: `tests/test_saxs_workbench_series_evidence.py`
- Modify: `tests/test_saxs_figure_evidence_binding.py`
- Modify: `tests/test_saxs_export_bundle.py`

- [x] Add tests for shared copy, Workbench advisory text, Figure compact projection, and Export quality evidence.
- [x] Run the four tests and confirm the expected missing-field failures.

Expected RED result: `4 failed`, with missing shared, Workbench, Figure, and
Export resolution evidence and no unrelated exception.

### Task 2: Attach latest resolution to existing SAXS state

**Files:**
- Modify: `polynexus/orchestrator_run_round.py`

- [x] After `resolve_saxs_ai_candidate_references` returns, attach its detached
  mapping to `engine.saxs_candidate_reference_resolution` and, when available,
  `engine.result.saxs_candidate_reference_resolution`.
- [x] Preserve the original advice mapping and all existing execution branches;
  do not add candidate application or validation calls.

### Task 3: Reuse the shared evidence channel

**Files:**
- Modify: `polynexus/core/saxs_batch_helpers.py`

- [x] Add `saxs_candidate_reference_resolution` to the existing AI rescue
  evidence field tuple so SAXS `get_parameters()` carries it without changing
  its schema shape.
- [x] Confirm the copy remains deep and detached.

### Task 4: Project Figure/Manifest and Export evidence

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_evidence.py`
- Modify: `polynexus/core/saxs_export_bundle.py`

- [x] Project only the compact resolution fields into Figure provenance; omit
  candidate `parameters` and retain publication roles.
- [x] Add the full detached resolution to Export's existing `ai_rescue` quality
  evidence section, preserving strict JSON conversion and missing-field
  compatibility.
- [x] Verify the existing FigurePipeline persists the same provenance in its
  Manifest-backed figure document.

### Task 5: Render Workbench advisory evidence

**Files:**
- Modify: `polynexus/gui/saxs_results_table_service.py`

- [x] Extend `_saxs_ai_rescue_review_text` to read the latest resolution from
  the existing parameter payload.
- [x] Display mode/status, resolved and unresolved IDs, and reason codes only;
  always instruct deterministic validation against existing physical and
  quality gates before any rescue action.
- [x] Keep malformed and absent mappings silent and leave input parameters
  unchanged.

### Task 6: GREEN and regression verification

- [x] Run the four new tests and the adjacent Figure/Workbench/Export/Advisor
  regression slice.
- [ ] Run the complete `test_saxs_*.py` matrix and retain only a complete
  pytest summary with exit code `0`.
- [x] Run the task-scoped structured verifier, storage report, and dry-run clean;
  never use `test_storage.py --apply`.
- [x] Run `git diff --check`, inspect the explicit allowlist, write the
  acceptance note, and create one `scripts/auto_commit.py` checkpoint.

Current verification limitation: the full matrix was attempted twice and
returned exit `124` without a pytest summary after `124s` and `604s`; those
runs are not counted as pass evidence. Focused and structured verifier evidence
is complete, and the remaining matrix limitation is recorded in the task card
and acceptance note.
