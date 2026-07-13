# Agent Task

## Goal

Continue the AI preprocessing optimization slice from `main@4437bc90` as
reviewable, fail-closed integration tasks. Keep AI-off behavior unchanged and
require explicit confirmation, immutable original-config snapshots, structured
decision audit, and scoped experience before any future promotion.

## Non-goals

- Do not merge the historical PR #3 wholesale or import unrelated 175-file
  integration changes.
- Do not modify Unified Tables, DSC/WAXS publication packs, GUI streamlining, or
  the superseded Editor/Export reconciliation.
- Do not enable automation by changing repository policy profiles from shadow
  without an explicit calibrated report and scientific review.
- Do not change scientific analysis algorithms outside preprocessing adapters and
  their evidence contracts.

## Affected boundaries

- Preprocessing contracts, bounded candidates, adapters, and decision gates.
- Orchestrator lifecycle, round records, runtime evidence, audit, and experience
  retrieval.
- GUI confirmation/apply transaction boundary (follow-up task).
- Calibration, Golden/synthetic evaluation, AI-off compatibility, quality gate,
  and acceptance evidence.

## Acceptance criteria

- [x] Foundation, semantic intents, DSC/IR/WAXS adapters, and SAXS/NMR adapters
  are migrated onto mainline with focused tests.
- [x] Calibration configuration remains shadow-only and requires matching
  version/hash evidence for any non-shadow profile.
- [x] Invalid intents and valid decisions produce structured audit records.
- [x] Experience retrieval is scoped by technique, instrument, sample family,
  schema, and core-major version; incomplete metadata disables retrieval.
- [x] Auto-commit rechecks the original config hash and preserves the original
  snapshot on mismatch; runtime negative-signal evidence is retained.
- [x] SAXS boundary smoothing and NMR zero-fill invariants are hard guards.
- [x] GUI confirmation and transactional apply/undo are migrated without
  Editor/Export changes.
- [x] Golden and synthetic preprocessing evaluation is deterministic and passes
  twice.
- [x] Fault-injection and AI-off compatibility coverage pass.
- [x] The local focused quality gate includes a `preprocess_optimization`
  section and passes.
- [ ] Full local/CI `--all-tests` completion is still pending; the local run
  exceeded 304 seconds without reporting a failing test.
- [ ] Human scientific review is still required.

## Current checkpoint

The isolated branch is `codex/ai-preprocess-mainline-v2` from `main@4437bc90`.
The working tree contains the foundation, adapters, calibration, and
orchestration changes. The current safety checkpoint fixes experience context,
decision auditing, original snapshots, hash recheck, runtime negative-fraction
evidence, and technique-specific hard guards.

## Verification

```powershell
python -m pytest tests/test_preprocess_optimization_contracts.py tests/test_preprocess_optimization_policy.py tests/test_preprocess_optimization_candidates.py tests/test_preprocess_optimization_decision.py tests/test_preprocess_optimization_storage.py tests/test_preprocess_peak_metrics.py tests/test_preprocess_phase1_adapters.py tests/test_preprocess_saxs_adapter.py tests/test_preprocess_nmr_adapter.py tests/test_orchestrator_preprocess.py tests/test_orchestrator_preprocess_automation.py tests/test_preprocess_calibration.py -q
python -m pytest tests/test_orchestrator.py tests/test_orchestrator_preprocess.py tests/test_orchestrator_preprocess_automation.py tests/test_preprocess_nmr_adapter.py tests/test_preprocess_saxs_adapter.py tests/test_analysis_evidence.py tests/test_quality_gate.py -q
python -m compileall -q polynexus/core/preprocess_optimization polynexus/orchestrator_preprocess.py polynexus/orchestrator.py
git diff --check
```

Latest checkpoint evidence: preprocessing contract/orchestration/calibration
suite `79 passed`; broader orchestration/analysis/quality subset `244 passed,
1 skipped`.

## Review checkpoint

- Human review required: yes; this changes automation safety, scientific
  evidence, and rollback/audit semantics.
- One atomic commit/PR per reviewable slice.
- Before merge, run the full preprocessing, Golden, AI-off, GUI, quality-gate,
  and CI checks and record acceptance evidence.
