# SAXS candidate replay and calibration audit

## Goal

Add an auditable, candidate-only SAXS replay contract for static, temperature,
and strain modes, then verify that the existing calibration gate blocks unsafe
promotion until expert-labelled evidence is available.

## Non-goals

- No changes to SAXS algorithms, physical metrics, quality thresholds, or
  publication roles.
- No external LLM calls, raw-data edits, generated-output edits, or automatic
  tiered-auto enablement.
- No scientific sign-off based only on automated tests.

## Affected boundaries

- `polynexus/orchestrator_preprocess.py` and the shared preprocessing contracts.
- `polynexus/core/preprocess_optimization/replay.py` and its public package
  export.
- `polynexus/core/saxs_export_bundle.py` for read-only replay provenance.
- `polynexus/core/saxs_engine/saxs_ai_rescue.py` only if a bridge DTO needs a
  replay field.
- `polynexus/core/preprocess_optimization/calibration.py` only for missing
  contract validation needed by this task.
- focused SAXS/orchestrator/calibration tests.
- task/spec/plan and durable memory records.

## Acceptance criteria

- [x] Every SAXS candidate trial has a JSON-safe replay audit row containing
  candidate identity, mode, config hashes, run status, existing evidence,
  decision, and explicit application flags.
- [x] Static, temperature, and strain success/failure paths preserve the
  control engine and never fabricate absent frame/sequence evidence.
- [x] Default shadow and confirm-only behavior remains unchanged; replay rows
  cannot authorize application.
- [x] Calibration cases and report validation reject no-case, low-coverage,
  false-accept, disagreement, version-mismatch, and hash-mismatch promotion.
- [x] Existing SAXS physical/quality gates remain the only acceptance basis.
- [x] Task verifier and the full current-HEAD verifier pass after the change.

## Implementation plan

1. Add failing replay-row contract tests using the existing fake SAXS engines.
2. Add the minimum JSON-safe replay DTO/row builder and attach it to the
   existing report/export audit without changing the result contract.
3. Add temperature/strain fake-engine coverage and explicit missing-evidence
   downgrade tests.
4. Add failing calibration blocker tests, then implement only the required
   validation and preserve the existing report schema.
5. Run focused tests, task verifier, and full/boundary verifier with external
   basetemp; record exact results.
6. Create one `auto_commit.py` checkpoint with the explicit allowlist.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_candidate_replay'
python -m pytest tests/test_saxs_ai_rescue_bridge.py tests/test_saxs_ai_orchestrator_handoff.py tests/test_orchestrator_preprocess.py tests/test_preprocess_calibration.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-candidate-replay-calibration.md --changed --types
python scripts/verify.py --changed --types --full --boundary
```

## Changed-file allowlist

- `polynexus/orchestrator_preprocess.py`
- `polynexus/core/preprocess_optimization/replay.py`
- `polynexus/core/preprocess_optimization/__init__.py`
- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `polynexus/core/preprocess_optimization/calibration.py`
- `polynexus/core/saxs_export_bundle.py`
- focused test files for replay/calibration
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-candidate-replay-calibration-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-candidate-replay-calibration.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`

## Verification result

- Focused replay/orchestrator/export/calibration matrix: `31 passed`.
- Structured verifier: quality gate `282 passed`; preprocessing gate `106
  passed`; Ruff, compile, type baseline, memory, and whitespace checks passed.
- Current-HEAD full/boundary verifier: `2671 passed, 10 warnings` in
  `1644.65s` (`0:27:24`); boundary audit passed. Warnings remain the known
  Qt tight-layout, DSC polyfit-conditioning, and SAXS CJK glyph warnings.

## Checkpoint

- DTO checkpoint: `b23e6c4`.
- Orchestrator/export checkpoint: `320774a`.
- Mode/calibration checkpoint: `8caf4f7`.
- Final task-card/memory checkpoint: this allowlisted documentation checkpoint.

## Known release boundary

Replay rows remain candidate-only and `apply_performed=false`. External model
calls, confirmed real reruns, expert-labelled calibration promotion, user
confirmation UI, restarted-GUI review, and human scientific publication
approval remain open gates.
