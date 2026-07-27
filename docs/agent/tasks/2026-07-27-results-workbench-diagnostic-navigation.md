# Results Workbench diagnostic navigation

## Goal

Expose the already-published diagnostic Figure Pack through every structured
Results Workbench profile and route links through the active manifest Gallery.

## Non-goals

- No changes to scientific analysis, evidence levels, publication roles,
  thresholds, fallback semantics, or AI behavior.
- No filesystem discovery or non-manifest Gallery entries.

## Affected boundaries

- `polynexus/gui/results_workbench_profiles.py`
- `polynexus/gui/main_window_output_mixin.py`
- profile and result routing regressions under `tests/`
- the design/spec and durable acceptance memory

## Implementation order

1. Lock exact/prefix link resolution and diagnostic profile contracts with TDD.
2. Add immutable resolver metadata and diagnostic Figure Pack links.
3. Route profile links through active Gallery IDs and preserve no-match behavior.
4. Run focused/structured verification, update durable memory, and checkpoint
   only the explicit allowlist.

## Implementation plan

1. Write RED tests for exact candidate precedence, deterministic prefix
   resolution, per-mode diagnostic links, and frame-indexed Gallery routing.
2. Add `WorkbenchFigureLink.prefixes` and `resolve()` without changing its
   existing `candidates` API.
3. Add provider-backed diagnostic links for every structured profile and make
   duplicate keys prefer the diagnostic link during routing.
4. Run the focused matrix and task-scoped verifier, record exact evidence, then
   create the allowlist checkpoint.

## Acceptance criteria

- [x] Every structured profile has one role=`diagnostic` Figure link.
- [x] Stable diagnostic IDs and frame-indexed prefixes match existing provider
  FigureDefinition IDs.
- [x] Exact candidates take precedence; prefix resolution is deterministic.
- [x] Workbench routing selects an available diagnostic ID from the active
  Gallery and does not fabricate or scan external files.
- [x] TDD RED is observed before production changes and GREEN is recorded after.
- [x] Focused regressions, task-scoped verifier, diff check, and explicit
  allowlist checkpoint pass.

## Implementation and verification evidence

- TDD RED: `19 failed, 16 passed`; failures were the expected missing
  `WorkbenchFigureLink.resolve()`/`prefixes` API and diagnostic links.
- TDD GREEN focused matrix: `40 passed` across Workbench profiles, SAXS/WAXS/
  DSC contracts, IR/NMR/Joint profiles, and result export contracts.
- Task-scoped verifier passed: task/memory checks, Ruff, compile, quality
  `282`, preprocessing `106`, and whitespace checks all passed.
- `git diff --check` passed as part of the verifier.
- Production behavior is navigation-only: exact IDs are checked first, then
  sorted matches from configured prefixes; the active Gallery remains the only
  source of selectable IDs. Duplicate NMR deconvolution keys prefer the
  diagnostic link so frame-indexed fallback remains reachable.

## Known limitations

- This checkpoint does not constitute real-data, restarted-GUI visual, or
  scientific release sign-off. Those remain gates in the full-software goal.
- Full/boundary verification for this checkpoint has not been run; this task
  does not claim a full-suite release pass.

## Checkpoint

The explicit allowlist checkpoint is created after the verification evidence
above. Pre-existing `.pytest_tmp*`, `.superpowers`, `tests/_tmp_phase3`, and
other untracked scratch/history files remain untouched and outside the task.

## Verification commands

```powershell
python -m pytest --basetemp=C:\Temp\PolyNexus_workbench_diag_red tests/test_results_workbench_profiles.py tests/test_ir_nmr_joint_workbench_profiles.py tests/test_saxs_workbench_figure_contracts.py -q
python -m pytest --basetemp=C:\Temp\PolyNexus_workbench_diag_green tests/test_results_workbench_profiles.py tests/test_ir_nmr_joint_workbench_profiles.py tests/test_saxs_workbench_figure_contracts.py tests/test_waxs_workbench_figure_contracts.py tests/test_dsc_workbench_figure_contracts.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-results-workbench-diagnostic-navigation.md --changed --types
git diff --check
```

## Verification

The focused matrix must cover profile construction, exact/prefix resolution,
active Gallery routing, and existing result export contracts. The structured
verifier must pass task/memory checks, changed-file Ruff/compile/type checks,
quality/preprocessing gates, and whitespace checks. Full/boundary results from
older checkpoints must not be reused for this task.

Required structured command:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-27-results-workbench-diagnostic-navigation.md --changed --types
```

## Changed-file allowlist

- `polynexus/gui/results_workbench_profiles.py`
- `polynexus/gui/main_window_output_mixin.py`
- `tests/test_results_workbench_profiles.py`
- `tests/test_ir_nmr_joint_workbench_profiles.py`
- `tests/test_saxs_workbench_figure_contracts.py`
- `tests/test_waxs_workbench_figure_contracts.py`
- `tests/test_dsc_workbench_figure_contracts.py`
- this task card
- `docs/superpowers/specs/2026-07-27-results-workbench-diagnostic-navigation-design.md`
- implementation plan and durable memory files created for this task
