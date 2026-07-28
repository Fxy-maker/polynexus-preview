---
task_id: 2026-07-29-joint-real-data-lifecycle
kind: scientific-cross-module
status: in_progress
---

# Joint real-data lifecycle acceptance

## Goal

Prove that real DSC, SAXS, and WAXS engine outputs can flow through the
existing SampleDB run contract into the Joint dataset/report and shared Figure
Manifest publication path.

## Non-goals

- Do not add raw-file ingestion to `JointCoordinator`.
- Do not change Joint formulas, thresholds, conflict severities, or publication
  roles.
- Do not infer scientific agreement from the real fixture values.
- Do not close restarted-GUI, IR vendor mapping, or human scientific release
  approval gates.

## Affected boundaries

- `tests/test_joint_real_data_lifecycle.py`: real engine → SampleDB → Joint
  dataset/report/publication acceptance.
- Existing public contracts only: `get_engine()`, `AnalysisResult`,
  `SampleDB.create_analysis_run()`, `collect_joint_dataset()`,
  `build_joint_hub_report()`, and `JointCoordinator.publish_hub_report()`.
- `docs/acceptance/2026-07-27-full-software-release-audit.md` and agent memory:
  record the strength and limits of this evidence after verification.

## Implementation plan

1. Run the real DSC, SAXS, and WAXS engines against the repository fixtures and
   persist their existing result payloads through the SampleDB run contract.
2. Collect the persisted runs through the existing Joint dataset/report APIs
   and assert source-run and cross-technique validation provenance.
3. Publish the Joint report through the existing Figure Manifest route and
   assert the three existing figure definitions share one run ID.
4. Run the focused Joint/NMR matrix, the task-scoped verifier, and whitespace
   checks; record exact summaries and keep scientific/release gates open.

## Acceptance criteria

- [x] The real DSC standard, SAXS static, and WAXS static fixtures execute in
  isolated output directories.
- [x] Their persisted SampleDB runs retain source paths, submodule IDs, result
  summaries, analysis evidence, and output directories.
- [x] Joint returns one batch row with three real source run IDs and visible
  cross-technique validation rows.
- [x] Joint publication produces the existing crystallinity, multiscale, and
  coverage FigureDefinitions under one run ID with manifest provenance.
- [x] The focused test and task-scoped verifier pass with exact exit codes.
- [x] Real-data transport is recorded as automated evidence only; scientific
  interpretation and final publication approval remain open.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_joint_real_data_verify_20260729'
python -m pytest -q tests/test_joint_real_data_lifecycle.py
python -m pytest -q tests/test_joint_hub_dataset.py tests/test_joint_figure_provider.py tests/test_joint_coordinator.py tests/test_joint_lifecycle_closure.py tests/test_nmr_joint_provenance_matrix.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-joint-real-data-lifecycle.md --changed --types
git diff --check
```

## Known limitations

This task does not supply a real Joint instrument file because the current
Joint contract consumes persisted analysis runs. It cannot establish IR vendor
mapping conventions, NMR assignment semantics, or human scientific sign-off.

## Evidence before checkpoint

- Fresh real-data lifecycle test: `1 passed, 1 warning in 14.86s`, exit code
  `0`.
- Focused Joint/NMR matrix: `23 passed, 2 warnings in 14.83s`, exit code `0`.
- Task-scoped verifier: exit code `0`; task-card and memory checks, Ruff,
  compile, quality (`283 passed, 2 warnings`), preprocessing (`106 passed, 2
  warnings`), and whitespace passed. No changed type-baseline targets were
  selected.
- The final verifier used the bundled Python runtime with its `Scripts`
  directory added inside the same Python process because the desktop shell
  resets PATH for child interpreters; repository verifier code was unchanged.

## Explicit changed-file allowlist

- `tests/test_joint_real_data_lifecycle.py`
- `docs/agent/tasks/2026-07-29-joint-real-data-lifecycle.md`
- `docs/superpowers/plans/2026-07-29-joint-real-data-lifecycle.md`
- `docs/acceptance/2026-07-27-full-software-release-audit.md`
- `docs/agent/memory/current-state.md`
- `docs/agent/memory/active-work.md`
