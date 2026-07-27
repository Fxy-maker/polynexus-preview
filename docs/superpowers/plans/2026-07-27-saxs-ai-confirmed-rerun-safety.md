# SAXS AI Confirmed Rerun Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a user-confirmed SAXS preprocessing rerun a single auditable transaction that is accepted only after the existing SAXS physical and quality evidence gates pass.

**Architecture:** A core SAXS adapter will validate confirmation identity and project the existing static, temperature, or strain result evidence into a strict JSON-safe post-rerun gate record. The generic GUI transaction service will own apply/rerun/rollback state and consume that adapter through callbacks; the run lifecycle will gate publication and persistence before accepting the candidate. Export will carry the detached audit under the existing `quality_evidence.json` provenance without changing figure roles.

**Tech Stack:** Python dataclasses, existing `stable_config_hash`, SAXS `DataQualityReport`/metric/detector/orientation contracts, PySide6 mixins, pytest, `scripts/verify.py`, and `scripts/auto_commit.py`.

---

### Task 1: Add RED tests for the SAXS evidence and audit contracts

**Files:**
- Create: `tests/test_saxs_ai_confirmed_rerun_safety.py`
- Modify: `tests/test_preprocess_transaction_service.py`
- Modify: `tests/test_saxs_export_bundle.py`

- [x] **Step 1: Write tests for strict evidence projection and mode boundaries.**

  Build small `SimpleNamespace` result fixtures for static, temperature, and strain. Assert that accepted evidence uses only existing `data_quality_report`, `metric_evidence`, `guinier_sequence_evidence`, `detector_quality_report`, `orientation_evidence`, `quality_flag`, and `Q_star_valid`; temperature keeps point `source_index` order and strain keeps orientation separate. Include a NaN and assert `json.dumps(payload, allow_nan=False)` succeeds and emits `None`.

- [x] **Step 2: Write tests for confirmation identity validation.**

  Create a confirm-only SAXS report containing one selected candidate and its `base_config_hash`. Assert that matching identity is accepted, while a missing candidate, mismatched candidate, mismatched base hash, unsupported mode, or a false hard guard is rejected before the rerun callback is called.

- [x] **Step 3: Write tests for transaction post-gate behavior.**

  Extend the existing transaction harness with a SAXS validator. Assert that a static/temperature/strain accepted result applies once and persists experience only after the validator returns passing evidence; missing, Diagnostic, Unusable, physical-failure, hash-mismatch, and validator-exception paths restore the original config/result and keep `apply_performed` false. Assert that undo does not revoke experience until its rerun also succeeds.

- [x] **Step 4: Write the export provenance regression.**

  Attach a detached confirmed-rerun audit to the fake SAXS engine and assert it is present under `quality_evidence.json` while the existing AI plan/decision fields remain unchanged.

- [x] **Step 5: Run the RED command and record the expected missing-API failures.**

  Run:

  ```powershell
  $env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_confirmed_rerun_red'
  python -m pytest tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_preprocess_transaction_service.py tests/test_saxs_export_bundle.py -q
  ```

  Expected: the new tests fail because the core adapter, transaction validator hooks, and export audit field do not yet exist; existing unrelated tests must not be “fixed” by weakening the new assertions.

### Task 2: Implement the core SAXS confirmation and evidence adapter

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- Modify: `polynexus/core/saxs_engine/__init__.py`
- Test: `tests/test_saxs_ai_confirmed_rerun_safety.py`

- [x] **Step 1: Implement strict JSON-safe detached projection.**

  Add a private recursive JSON normalizer that maps non-finite numeric values to `None`, copies mappings/sequences, and never retains raw curves or detector arrays. Add `build_saxs_confirmed_rerun_evidence(result, mode=...)` with normalized `static`, `temperature`, and `strain` frame/series projections. Missing or malformed evidence is represented as `status: unavailable`, never inferred.

- [x] **Step 2: Implement existing-gate evaluation.**

  Add `assess_saxs_confirmed_rerun(result, mode=...)`. It must require a result, reject `quality_flag` errors and `Q_star_valid=False`, reject missing/Diagnostic/Unusable required frame quality evidence, retain temperature `source_index` and series trend evidence without promoting it, and keep strain detector/orientation evidence independent. It may only copy existing gate outcomes; it must not introduce a new numeric threshold.

- [x] **Step 3: Implement confirmation identity validation.**

  Add `validate_saxs_confirmation_report(report, current_config, mode=...)` using the selected candidate row and existing `hard_guard_results`; compare the candidate base hash with `stable_config_hash(current_config)`, require `request_confirmation`, a selected candidate ID, and one of the three supported modes. Return only detached metadata needed by the transaction service.

- [x] **Step 4: Export the new public adapter contract and run the focused GREEN tests.**

  Export the adapter functions from `saxs_engine.__init__`, then run the Task 1 focused command. Expected: all new core contract tests and unchanged transaction/export tests pass.

### Task 3: Make the generic transaction service post-gate and auditable

**Files:**
- Modify: `polynexus/gui/preprocess_transaction_service.py`
- Modify: `tests/test_preprocess_transaction_service.py`
- Test: `tests/test_saxs_ai_confirmed_rerun_safety.py`

- [x] **Step 1: Add detached transaction audit state and callback hooks.**

  Extend the service with optional `technique`, `mode_provider`, `validate_rerun`, and `record_audit` callbacks. Preserve the existing generic behavior when no SAXS validator is supplied. Keep the original config/result until post-gate acceptance and compute before/after hashes with the shared hash helper.

- [x] **Step 2: Gate confirmation before mutation and enforce one rerun.**

  For SAXS, call the core identity validator before `_apply_config`; reject pending transactions, candidate/hash/guard/mode mismatches without invoking `_rerun`. Store an `apply_pending` audit, then invoke the rerun callback at most once.

- [x] **Step 3: Gate successful reruns before persistence.**

  Change `finalize_success(result=None)` to validate the supplied post-rerun result and selected-config hash before persisting experience. On any failed gate or exception, restore the original config/result, set `apply_performed=False`, and record a rollback reason. Persist experience only on accepted post-gate evidence.

- [x] **Step 4: Preserve undo semantics and audit it.**

  Validate an undo rerun through the same callback; revoke the stored experience only after successful undo completion. If undo fails, restore the accepted candidate state and keep the experience active.

- [x] **Step 5: Run the transaction-focused GREEN matrix.**

  Run:

  ```powershell
  $env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_confirmed_rerun_transaction_green'
  python -m pytest tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_preprocess_transaction_service.py -q
  ```

### Task 4: Connect GUI lifecycle and SAXS export provenance

**Files:**
- Modify: `polynexus/gui/main_window_ai_tuning_mixin.py`
- Modify: `polynexus/gui/main_window_run_mixin.py`
- Modify: `polynexus/core/saxs_export_bundle.py`
- Modify: `tests/test_saxs_export_bundle.py`
- Test: `tests/test_saxs_ai_confirmed_rerun_safety.py`

- [x] **Step 1: Inject the SAXS adapter through the GUI service boundary.**

  Pass the current mode and validator as callbacks from the mixin; keep technique-specific decisions outside widget event handlers. Record the detached audit on the current SAXS engine/result provenance object without copying raw analysis data.

- [x] **Step 2: Move post-gate finalization ahead of candidate persistence.**

  In `_on_finished`, call the transaction finalizer with the worker result before assigning/persisting it. If the gate rejects, retain the restored original result and do not persist the failed candidate run. Keep `_on_error` rollback behavior and existing UI error diagnostics intact.

- [x] **Step 3: Add audit to the existing quality evidence payload.**

  Read `saxs_confirmed_rerun_audit` from the engine, with result fallback, and include it under `ai_rescue.confirmed_rerun`. Preserve `quality_evidence.json` as the authoritative source and leave publication roles and Figure/Manifest behavior unchanged.

- [x] **Step 4: Run the integration matrix.**

  Run:

  ```powershell
  $env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_confirmed_rerun_integration'
  python -m pytest tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_preprocess_transaction_service.py tests/test_saxs_ai_rescue_bridge.py tests/test_saxs_ai_orchestrator_handoff.py tests/test_saxs_export_bundle.py -q
  ```

### Task 5: Verify, update durable state, and create the allowlist checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-27-saxs-ai-confirmed-rerun-safety.md`
- Modify: `docs/superpowers/plans/2026-07-27-saxs-ai-confirmed-rerun-safety.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [x] **Step 1: Run focused, SAXS, and task-scoped verification.**

  Run the focused integration command, the full `tests/test_saxs_*.py` matrix, and:

  ```powershell
  $env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_confirmed_rerun_verify'
  python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-ai-confirmed-rerun-safety.md --changed --types
  git diff --check
  ```

  Record exact counts, warnings, and any timeout or boundary limitation. Do not reuse prior full/boundary evidence as evidence for this change.

- [x] **Step 2: Run fresh full/boundary verification when feasible; record the unrelated WAXS failure and boundary non-execution.**

  Run `python scripts/verify.py --changed --types --full --boundary` with a dedicated base temp directory. If the command times out or reports a basetemp lock, report that exact limitation rather than converting an older pass into current evidence.

- [x] **Step 3: Request code review and resolve material findings.**

  Review the cumulative diff against this plan, the design, and the scientific review boundary. Fix critical/important findings before checkpointing; leave GUI restart and human scientific review as explicit limitations.

- [x] **Step 4: Create the single explicit allowlist checkpoint.** The
  allowlist checkpoint was created, and this documentation-only amend records
  the final state without adding files.

  ```powershell
  python scripts/auto_commit.py --message "feat(saxs): close confirmed rerun safety" --files polynexus/core/saxs_engine/saxs_ai_rescue.py polynexus/core/saxs_engine/__init__.py polynexus/gui/preprocess_transaction_service.py polynexus/gui/main_window_ai_tuning_mixin.py polynexus/gui/main_window_run_mixin.py polynexus/core/saxs_export_bundle.py tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_preprocess_transaction_service.py tests/test_saxs_export_bundle.py docs/agent/tasks/2026-07-27-saxs-ai-confirmed-rerun-safety.md docs/superpowers/plans/2026-07-27-saxs-ai-confirmed-rerun-safety.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md
  ```

  The checkpoint must include only these files, never GUI scratch, review hints, pytest temp directories, or unrelated parallel changes.
