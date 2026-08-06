# SAXS Stability Map and Scientific Correctness

## Goal

Integrate strict stability-map validation into the existing AI-tuning entry
point and repair the nine identified SAXS scientific/data-contract defects.

## Non-goals

- No automatic push, merge, deployment, or publication authorization.
- No implementation of a new LLM provider or raw-detector prompt transport.
- No silent application of a candidate outside the existing confirmation
  transaction.
- No replacement of the existing six-candidate preprocessing loop; stability
  studies use a separate bounded evaluation budget and cache.

## Affected boundaries

- `polynexus/core/saxs_engine`: physical helpers, correlation, preprocessing,
  temperature/strain/orientation, and input-unit contracts.
- `polynexus/core/preprocess_optimization`: stability request/report contracts
  and deterministic decision projection.
- `polynexus/gui`: one AI-tuning entry point and existing transaction service.
- `tests/`: focused scientific and integration regressions.
- `docs/agent`, `docs/superpowers`: durable task, design, and plan evidence.

## Acceptance criteria

- [x] The AI-tuning button launches a strict stability study by default. AI output
   remains candidate/ prior input only.
- [x] A stability report contains explored parameter points, accepted plateau
   bounds, bootstrap intervals, cross-frame continuity evidence, physical and
   quality gates, and one of `auto_accept`, `request_confirmation`, or
   `keep_original`.
- [x] Applying a report is possible only through the existing confirmation
   transaction; hash checks, rerun validation, rollback, and audit records stay
   active.
- [x] The crystallinity root honors `SAXSConfig.crystallinity_gt_half`.
- [x] Temperature invariant calculations preserve signed corrected residuals.
- [x] Correlation/Fourier calculations preserve signed source observations while
   logarithmic consumers remain positive-only.
- [x] Unsupported 1D and sector bins are represented as unavailable with support
   counts, never as physical zero intensity.
- [x] Strain Porod estimation uses an explicit Porod window and does not mutate
   shared configuration.
- [x] Porod evidence requires both a slope tolerance and an `I(q)q^4` plateau.
- [x] Azimuthal integration handles the periodic chi boundary.
- [x] `Kp` is present in the public static parameter output.
- [x] Common reciprocal-length spellings are normalized or fail closed with a
   typed reason.
- [x] Each behavior change has a regression test with a reproducible synthetic
   input and the new tests are observed failing before implementation.

## Implementation plan

1. Lock the identified SAXS physical and data-contract behaviors with focused
   synthetic regressions, then implement the fail-closed core fixes.
2. Implement the deterministic stability service with global sampling, local
   refinement, cache keys, plateau/bootstrap evidence, and per-trial continuity.
3. Bridge strict SAXS AI tuning to typed cloned trial engines and expose the
   report through the existing preprocessing decision contract.
4. Route confirmation and SAXS auto-accept through the existing transaction,
   including asynchronous finalization and deferred Undo.
5. Run focused and structured verification, update durable project memory, and
   create one explicit-allowlist checkpoint without push or merge.

## Verification

```powershell
python -m pytest -q tests/test_saxs_stability_map.py tests/test_saxs_scientific_correctness_repair.py tests/test_saxs_scientific_correctness_closure.py
python scripts/verify.py --task docs/agent/tasks/2026-08-05-saxs-stability-map-scientific-correctness.md --changed --types
```

The full SAXS matrix is required before completion when runtime permits. Human
scientific review remains required before merge because the change affects
physical semantics.

## Status

- Status: implementation complete; human scientific review required
- Blocker: none
- Evidence: focused stability/transaction/scientific matrix passed `94 passed,
  6 warnings`; structured verifier passed its `297` focused and `107`
  preprocessing tests. A complete `test_saxs*.py` run reached
  `916 passed, 2 skipped, 14 failed` in 235.91s; the failures are concentrated
  in real-data audit/EDF fixtures and legacy dirty-input expectations for the
  signed-source contract, so the full matrix is not claimed green.
- The stability evaluator now uses typed cloned `SAXSConfig` trials, includes
  an explicit Guinier window factor, preserves signed raw correlation channels
  while using a positive derived Fourier view, and preserves per-trial
  cross-frame continuity semantics.
- Follow-up closure now preserves valid frames when sparse sector bins are
  unavailable, fails closed with `no_valid_frames` when a discovered directory
  has no surviving frame, disables SAXS stability auto-accept by default, and
  exposes missing absolute-contrast calibration as diagnostic-only evidence.
- Follow-up focused matrix passed `122 passed, 6 warnings`; task verification
  passed quality `297` and preprocessing `107` with Ruff, compile, type
  baseline, and whitespace checks passing.
- Remaining review limits: absolute contrast/calibration, lamellar
  interpretation, publication promotion, and whether auto-accept thresholds
  are appropriate for each beamline remain human scientific decisions.
- Next action: run the structured verifier, review the cumulative diff, and
  create the explicit-allowlist local checkpoint.
