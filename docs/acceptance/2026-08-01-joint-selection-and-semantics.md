# Joint Selection and Result Semantics

Date: 2026-08-01
Status: implementation and focused automated verification complete

## Delivered

- Joint refresh now leaves all candidate batches unchecked. The Recommended
  action remains explicit, and report scope is controlled by checked batches.
- Each selected batch retains its own newest run per technique and publishes a
  detached `source_preflight` projection with sample/batch identity, technique,
  submodule, run ID, source path, output directory, conditions, and evidence
  status/reasons. The main-window export writes
  `data/joint_hub_source_preflight.csv`.
- Validation rows now carry `OK`, `DIFF`, `SKIP`, or dataset-boundary
  `NOT_COMPARABLE` semantics. Missing inputs are `SKIP` with `INFO` severity
  and do not increment Joint issue counts.
- NMR solid-C runs marked `assignment_limited`, or carrying an uncalibrated ppm
  axis, remain visible in source evidence but do not contribute an Xc value to
  Joint comparison.
- The real PA6 lifecycle fixture now uses the PA6 static SAXS file under
  `测试数据/saxs/普通小角`, not the unrelated PAD8 `8-000-s...edf` source.
  The correct SAXS source is expected to remain diagnostic when its engine
  validation reports `saxs=ERROR`; this is asserted without changing the
  lifecycle transport/provenance checks.

## Verification Evidence

Command:

```powershell
python -m pytest -q tests/test_joint_hub_dataset.py tests/test_joint_analysis_hub.py tests/test_joint_coordinator.py tests/test_joint_figure_provider.py tests/test_joint_lifecycle_closure.py tests/test_joint_real_data_lifecycle.py
```

Result: `33 passed in 31.07s`, exit code `0`.

The focused GUI/export compatibility command also passed `19 passed in
19.01s`, exit code `0`.

Structured verification:

```text
python scripts/verify.py --task docs/agent/tasks/2026-08-01-joint-selection-and-semantics.md --changed --types
exit code 0; quality gate 297 passed; preprocessing gate 106 passed; Ruff,
compile, type baseline, memory, task, whitespace, and diff checks passed.
python scripts/boundary_audit.py --root D:\PolyNexus --json
exit code 0.
git diff --check
exit code 0.
```

## Boundaries

This checkpoint does not infer vendor-native IR mapping coordinates, assign or
calibrate solid-C NMR peaks, select a scientific winner among DSC/WAXS/SAXS,
or approve publication. It also does not change any technique-specific Xc
formula. Existing unrelated worktree changes and managed test artifacts were
left untouched.
