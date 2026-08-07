# SAXS AI Tuning and Stability Decision Repair

## Goal

Repair the SAXS AI-tuning and parameter-stability decision path so that
candidate-influenceable evidence controls acceptance, actual sequence modes are
validated, requested perturbations are effective, and strain orientation and
continuity evidence are scientifically meaningful.

## Non-goals

- Do not implement Bayesian optimization in this task.
- Do not enable unattended SAXS auto-accept.
- Do not infer missing tensile-axis, saturation, geometry, or calibration
  metadata.
- Do not weaken physical or quality gates to make a configuration applicable.
- Do not push, merge, deploy, publish, or regenerate historical results.

## Affected boundaries

- `polynexus/core/saxs_action_registry.py` and
  `polynexus/core/saxs_symptom_detector.py`: symptom ownership.
- `polynexus/orchestrator_state.py`: action-specific candidate targets.
- `polynexus/orchestrator_stability.py`: mode, active domains, and SAXS metric
  extraction.
- `polynexus/core/preprocess_optimization/stability.py`: continuity, platform,
  interval, and report contracts.
- `polynexus/core/saxs_engine`: header-relative beam-center and typed mask
  perturbation behavior.
- `polynexus/orchestrator_session.py` and `polynexus/gui`: confirmation mode and
  SAXS-specific evidence projection.
- Focused tests under `tests/`.

## Acceptance criteria

- [x] A complete, continuous filename-derived condition axis is not marked
  unstable solely because its source confidence is below 0.75.
- [x] Condition-axis symptoms cannot authorize q-crop changes.
- [x] Candidate plans bind an action-compatible symptom rather than inheriting
  an unrelated global lead symptom.
- [x] Stability trials and confirmation reports use the active static,
  temperature, or strain mode without silent fallback.
- [x] Inactive background, detector, and orientation dimensions are excluded
  with explicit reason codes.
- [x] Beam-center and mask perturbations preserve typed configuration and
  demonstrably change the trial input when active.
- [x] Smooth large strain evolution passes continuity while isolated jumps
  fail; insufficient short sequences remain explicit.
- [x] Strain stability transports Herman and orientation-axis evidence without
  promoting missing tensile-axis metadata.
- [x] Plateau selection uses selected/eligible trials, active-dimension spread,
  and perturbation-interval terminology.
- [x] `keep_original` exposes no applicable stability candidate; confirmed
  reports retain hash, rerun, rollback, audit, and Undo protections.
- [x] SAXS GUI summaries display stability-specific evidence instead of
  `protected metrics available: 0`.
- [x] Every behavior change has a focused regression observed failing before
  implementation.

## Implementation plan

1. Repair condition-axis symptom semantics and action-specific target binding.
2. Propagate the active SAXS mode through stability evaluation and confirmation.
3. Exclude inactive perturbations and make geometry/mask candidates applyable.
4. Replace magnitude limiting with robust sequence-jump evidence.
5. Add strain orientation metrics and dimension-aware platform requirements.
6. Project non-applicable and SAXS-specific evidence correctly in the GUI.
7. Run cumulative verification, independent review, memory updates, and the
   explicit-allowlist checkpoint.

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest -p no:cacheprovider -q tests/test_saxs_symptom_detector.py tests/test_saxs_action_registry.py tests/test_saxs_orchestrator_loop.py tests/test_saxs_stability_map.py tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_preprocess_decision_service.py tests/test_preprocess_decision_dialog.py tests/test_preprocess_transaction_service.py tests/test_main_window_ai_tuning_mixin.py tests/test_saxs_config_binding.py tests/test_saxs_preprocess.py tests/test_saxs_scientific_correctness_repair.py tests/test_saxs_q_resolved_orientation_reliability.py
python scripts/verify.py --task docs/agent/tasks/2026-08-07-saxs-ai-stability-decision-repair.md --changed --types --base 2d4092ab
```

## Design and plan

- Design:
  `docs/superpowers/specs/2026-08-07-saxs-ai-stability-decision-repair-design.md`
- Plan:
  `docs/superpowers/plans/2026-08-07-saxs-ai-stability-decision-repair.md`

## Status

- Status: implementation and local verification complete
- Focused cumulative matrix: `257 passed, 7 warnings`.
- Structured verification: task/memory checks, Ruff, compile, and whitespace
  passed; quality gate `297 passed`; preprocessing gate `156 passed`.
- Independent cumulative review found no Critical issue. All reported Important
  confirmation, effective-perturbation, orientation-coverage, numeric-bound,
  and continuity defects were repaired with focused RED/GREEN regressions.
- The deterministic search remains seeded Latin-hypercube exploration plus
  bounded local refinement. Bayesian optimization was not introduced.
- SAXS stability decisions remain confirmation-only. A numerically eligible
  `auto_accept` is downgraded to `request_confirmation` before the GUI.
- `bg_scale_value` is explicitly excluded as
  `background_curve_consumer_missing` until production loads and passes real
  background q/I arrays; a filename alone does not activate the dimension.
- Human review: required before merge because symptom, orientation, and
  sequence-continuity semantics are scientific behavior
