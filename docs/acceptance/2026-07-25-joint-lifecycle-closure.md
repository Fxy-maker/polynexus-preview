# Joint lifecycle closure acceptance

## Delivered

The unified regression publishes a deterministic Joint report and verifies one
run-relative identity through:

`JointCoordinator -> Manifest/Gallery -> Editor working/published revisions ->
export bundle -> MainWindow History restore`.

It preserves the existing publication roles:

- `joint.series.crystallinity`: Main
- `joint.series.multiscale`: SI
- `joint.series.coverage`: diagnostic

## Verification evidence

```text
python -m pytest tests/test_joint_lifecycle_closure.py -q
1 passed in 4.39s

python -m pytest tests/test_joint_lifecycle_closure.py tests/test_joint_figure_provider.py tests/test_joint_hub_dataset.py tests/test_joint_coordinator.py tests/test_joint_analysis_hub.py tests/test_nmr_joint_provenance_matrix.py -q
23 passed in 13.19s

python -m pytest tests/test_main_window_persistence.py -q -k "joint and not ai_tuning"
14 passed in 18.72s

python -m pytest tests/test_preprocess_cross_technique_matrix.py tests/test_preprocess_ai_off_compat.py tests/test_preprocess_fault_injection.py tests/test_preprocess_calibration.py tests/test_preprocess_optimization_contracts.py tests/test_preprocess_optimization_decision.py tests/test_preprocess_optimization_policy.py tests/eval/preprocess/test_preprocess_golden.py tests/eval/preprocess/test_preprocess_synthetic.py -q
66 passed in 0.53s

python scripts/verify.py --task docs/agent/tasks/2026-07-25-joint-lifecycle-closure.md --changed --types
selected checks passed; quality gate 282 passed, preprocessing gate 103 passed
```

The regression writes only to pytest temporary directories and asserts the
export paths `metadata/runs/` and `metadata/active_run.json`.

## Remaining acceptance boundary

This closes the automated Joint lifecycle contract. Real-data review,
restarted-GUI visual inspection, AI-off/failure/fallback release evidence, and
human scientific sign-off remain open in the full-software ledger.
