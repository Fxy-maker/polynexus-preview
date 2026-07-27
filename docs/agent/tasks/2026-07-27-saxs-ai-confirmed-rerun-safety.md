# SAXS AI Confirmed Rerun Safety Task

## Goal

Close the safety gap between a confirmed SAXS preprocessing candidate and its
post-confirmation result. A confirmed static, temperature, or strain rerun must
run once, pass the existing SAXS physical/quality evidence gates, and produce a
strict JSON-safe audit record before experience or result persistence.

## Non-goals

- No new SAXS numerical algorithm, q-window, physical threshold, or quality threshold.
- No interpolation, frame fabrication, missing-frame repair, or automatic rescue.
- No external model call, automatic acceptance promotion, calibration shortcut, or raw-curve storage.
- No publication-role, Figure, Manifest, Gallery, or editor behavior changes.
- No replacement of authoritative `quality_evidence.json` ownership.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `polynexus/core/saxs_engine/__init__.py`
- `polynexus/gui/preprocess_transaction_service.py`
- `polynexus/gui/main_window_ai_tuning_mixin.py`
- `polynexus/gui/main_window_run_mixin.py`
- `polynexus/core/saxs_export_bundle.py`
- focused SAXS, transaction, and export tests
- task/plan and durable agent memory

## Implementation plan

1. Add RED tests for strict JSON evidence projection, static/temperature/strain
   gate decisions, confirmation identity, transaction rollback/undo timing, and
   export audit provenance.
2. Implement the core SAXS confirmed-rerun evidence adapter and identity
   validator by reusing existing evidence fields and `stable_config_hash`.
3. Extend the generic transaction service with optional confirmation/post-gate
   callbacks, one-rerun state, detached audit state, and fail-closed rollback.
4. Connect the GUI lifecycle so post-gate acceptance occurs before result and
   run persistence, then expose the audit through existing SAXS export quality
   provenance.
5. Run focused, full SAXS, task-scoped, compile/type, whitespace, diff, and
   fresh full/boundary checks; update durable memory and create one explicit
   allowlist checkpoint.

## Acceptance criteria

- [x] Strict JSON audit/evidence projection maps non-finite values to `null` and excludes raw curves/arrays.
- [x] Static confirmation applies once and is accepted only after existing physical and quality evidence pass.
- [x] Temperature preserves frame evidence, series trend evidence, and original `source_index`; trend never upgrades a frame.
- [x] Strain preserves generic metric evidence separately from detector/orientation evidence and retains `strain_pct`.
- [x] Candidate/mode/hash/guard mismatch, missing/Diagnostic/Unusable evidence, physical-gate failure, selected-config hash drift, and rerun exception all restore original state with `apply_performed=false`; restore failures are explicit.
- [x] Experience persistence occurs only after post-gate success; undo revokes only after successful undo rerun.
- [x] Export carries the detached audit without changing publication roles or evidence ownership.
- [x] Focused matrix, SAXS matrix, task-scoped verifier, compile/type/whitespace, strict JSON, and diff checks have fresh recorded results.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_confirmed_rerun_verify'
python -m pytest tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_preprocess_transaction_service.py tests/test_saxs_ai_rescue_bridge.py tests/test_saxs_ai_orchestrator_handoff.py tests/test_saxs_export_bundle.py -q
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-ai-confirmed-rerun-safety.md --changed --types
python scripts/verify.py --changed --types --full --boundary
git diff --check
```

## Verification evidence (2026-07-27)

- TDD RED: the new focused test module first failed during collection with
  `ImportError: cannot import name 'assess_saxs_confirmed_rerun'`, confirming
  the missing production contract rather than a false-green test.
- Focused final matrix:
  `python -m pytest tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_preprocess_transaction_service.py tests/test_saxs_export_bundle.py -q`
  -> **33 passed**.
- Complete SAXS matrix:
  `python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q`
  -> **338 passed, 4 warnings**. Warnings are the existing Arial CJK glyph
  warnings from SAXS figure layout.
- Task-scoped verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-ai-confirmed-rerun-safety.md --changed --types`
  -> task/memory, Ruff, compile/type baseline, quality **282**, preprocessing
  **106**, and whitespace all passed.
- Fresh full/boundary command:
  `python scripts/verify.py --changed --types --full --boundary` with a
  dedicated basetemp ran the full repository chain for about **25:42**. The
  full `pytest -q` stage reached **2763 passed, 1 failed, 10 warnings**; the
  unrelated existing failure was
  `tests/test_waxs_publication_cutover.py::test_waxs_engine_publishes_manifest_backed_assets`.
  The command exited before boundary audit, so no full/boundary pass is
  claimed. No verifier or pytest processes remain.
- `git diff --check` passed after the final code changes.
- A post-amend documentation-only verifier rerun was attempted without a
  dedicated `PYTEST_ADDOPTS` override and hit the pre-existing repository
  `.pytest_tmp` lock: **229 passed, 53 setup errors** while removing the shared
  basetemp. This does not replace the successful dedicated task-scoped code
  verification above; no code or scratch path was changed to work around it.

## Known limitations

This is an automated safety closure only. Restarted-GUI confirmation behavior,
human scientific review of the definition of the existing gates, and publication
authorization remain outside automated acceptance. Full/boundary release
verification is blocked by the unrelated WAXS publication-cutover failure above;
that out-of-scope failure was left untouched.

## Checkpoint

Atomic allowlist checkpoint was created locally, followed by this doc-only
amend; no push, merge, or deploy was performed.

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `polynexus/core/saxs_engine/__init__.py`
- `polynexus/gui/preprocess_transaction_service.py`
- `polynexus/gui/main_window_ai_tuning_mixin.py`
- `polynexus/gui/main_window_run_mixin.py`
- `polynexus/core/saxs_export_bundle.py`
- `tests/test_saxs_ai_confirmed_rerun_safety.py`
- `tests/test_saxs_export_bundle.py`
- this task card
- `docs/superpowers/plans/2026-07-27-saxs-ai-confirmed-rerun-safety.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
