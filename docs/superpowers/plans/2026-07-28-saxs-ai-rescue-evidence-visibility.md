# SAXS AI Rescue Evidence Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transport existing SAXS AI rescue audit fields through `get_parameters()` and expose a safe read-only Workbench review.

**Architecture:** Add one pure deep-copy helper beside the existing SAXS quality transport helpers. Each `SAXSEngine.get_parameters()` branch adds the helper output without interpreting it. Add one pure Workbench formatter that consumes only the public payload and joins its advisory text with the existing review channels.

**Tech Stack:** Python, dataclasses/typed mappings already used by PolyNexus, pytest, `scripts/verify.py`.

---

### Task 1: Define the visibility contract and regressions

**Files:**
- Create: `docs/superpowers/specs/2026-07-28-saxs-ai-rescue-evidence-visibility-design.md`
- Create: `docs/superpowers/plans/2026-07-28-saxs-ai-rescue-evidence-visibility.md`
- Create: `docs/agent/tasks/2026-07-28-saxs-ai-rescue-evidence-visibility.md`
- Test: `tests/test_saxs_batch_parameters.py`
- Test: `tests/test_saxs_workbench_series_evidence.py`

- [x] **Step 1: Write transport regressions.**

  Add tests that put `saxs_ai_rescue_plan`, `saxs_ai_rescue_decision`,
  `saxs_ai_rescue_replay`, and `saxs_confirmed_rerun_audit` on a fake engine,
  call `get_parameters()`, assert all four values are present and detached,
  and mutate the returned nested value without changing the source. Cover a
  temperature result and a static result so the helper is not accidentally
  limited to one series branch.

- [x] **Step 2: Write Workbench regressions.**

  Build a public parameter mapping containing a plan, a
  `request_confirmation` decision with `apply_allowed=True`, one replay row,
  and a rolled-back confirmed-rerun audit. Assert `risk_text` and `next_text`
  mention review/validation and the identifiers/statuses, while neither text
  contains an acceptance or physical-validity claim. Add a malformed/empty
  payload test that produces no AI rescue text.

- [x] **Step 3: Run the focused tests and record the expected RED.**

  Run:

  ```powershell
  python -m pytest -q tests/test_saxs_batch_parameters.py tests/test_saxs_workbench_series_evidence.py --basetemp C:\Temp\PolyNexus_saxs_ai_visibility_red
  ```

  Expected: the new transport and Workbench assertions fail because the
  public keys and formatter are not implemented yet.

### Task 2: Implement detached public transport

**Files:**
- Modify: `polynexus/core/saxs_batch_helpers.py`
- Modify: `polynexus/core/saxs.py`

- [x] **Step 1: Add a pure AI evidence copier.**

  Add `copy_saxs_ai_rescue_evidence(*sources)` beside
  `copy_saxs_quality_evidence()`. For each of the four public field names,
  scan the supplied objects in order, copy the first non-`None` value with
  `deepcopy`, and omit fields that are absent. Do not normalize, classify, or
  combine values.

- [x] **Step 2: Attach the copied fields in every parameter branch.**

  Update temperature, strain, aligned-batch, static single, and fallback
  analysis payload construction with the copied helper output, using the
  engine first and the result/analysis object as fallback. Keep existing
  metric, detector, orientation, and sequence evidence unchanged.

- [x] **Step 3: Run the transport tests.**

  Run:

  ```powershell
  python -m pytest -q tests/test_saxs_batch_parameters.py --basetemp C:\Temp\PolyNexus_saxs_ai_visibility_transport
  ```

  Expected: all transport tests pass and source mappings remain unchanged.

### Task 3: Implement read-only Workbench review

**Files:**
- Modify: `polynexus/gui/saxs_results_table_service.py`
- Test: `tests/test_saxs_workbench_series_evidence.py`

- [x] **Step 1: Add a pure formatter.**

  Implement `_saxs_ai_rescue_review_text(payload, language)` to inspect only
  valid mappings/list rows. Include plan candidate count, decision name and
  `apply_allowed` value, replay run status, and confirmed-rerun phase/gate
  statuses. Prefix the detail as advisory AI rescue evidence and return the
  existing localized risk/next translation keys. The next text must require
  deterministic validation and existing physical/quality gate review.

- [x] **Step 2: Join it with the existing presentation.**

  Call the formatter in `build_saxs_results_presentation()` and append its
  risk/next text after the existing sequence-rescue review. Leave table rows,
  diagnostics, and export flags unchanged.

- [x] **Step 3: Run the focused GREEN matrix.**

  Run:

  ```powershell
  python -m pytest -q tests/test_saxs_workbench_series_evidence.py tests/test_saxs_results_table_service.py --basetemp C:\Temp\PolyNexus_saxs_ai_visibility_green
  ```

  Expected: all focused Workbench tests pass.

### Task 4: Verify and checkpoint

**Files:**
- All files in the explicit task allowlist in the task card.

- [x] **Step 1: Run the complete SAXS matrix.**

  Run the PowerShell-expanded `tests/test_saxs_*.py` matrix with a dedicated
  basetemp and record the exact count and warnings.

- [x] **Step 2: Run the structured verifier and diff checks.**

  Run `python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-ai-rescue-evidence-visibility.md --changed --types` with a dedicated basetemp and `git diff --check`. Do not claim full/boundary unless it is actually run and completes.

- [ ] **Step 3: Create one explicit checkpoint.**

  Use `scripts/auto_commit.py` with exactly the allowlist from the task card;
  do not stage or commit parallel release-audit, GUI scratch, memory, or
  pytest-temporary files.
