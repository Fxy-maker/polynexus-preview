# SAXS temperature dirty-frame post-processing

## Goal

Make recoverable dirty q/I observations usable by temperature-series
post-processing without losing the original frame-quality provenance.

## Non-goals

- No new physical thresholds, Guinier windows, rescue decisions, or AI calls.
- No interpolation, neighboring-frame copying, duplicate-q aggregation, or
  fabricated frames.
- No change to `analyze_single()`'s public result contract.
- No change to temperature sorting, source-index mapping, LC path selection,
  publication roles, or GUI behavior.

## Affected boundaries

- Temperature post-processing:
  `polynexus/core/saxs_engine/saxs_temperature.py`.
- Existing sanitization and quality contract, reused without modification:
  `polynexus/core/saxs_engine/saxs_quality_contracts.py`.
- Regression coverage:
  `tests/test_saxs_temperature_dirty_frame_postprocessing.py`.
- Durable task/spec/plan and SAXS agent memory.

## Acceptance criteria

- [x] A dirty frame with finite surviving q/I observations produces finite
  temperature-series invariant evidence when the existing invariant method can
  evaluate the surviving profile.
- [x] Reference Bragg/invariant and peak-intensity tracking consume only the
  existing sanitized surviving observations.
- [x] The original arrays still reach `analyze_single()` and its quality report
  retains the original defect actions/counts.
- [x] An empty sanitized frame remains fail-closed with existing warnings and
  no fabricated metric.
- [x] Clean temperature profiles retain existing outputs and source ordering.
- [x] Focused, exact SAXS, task-scoped, and fresh full/boundary verification
  all pass; unrelated GUI/Joint/editor/scratch files remain outside the
  allowlist.

## Implementation plan

1. Add a RED regression that supplies NaN, non-positive, and unsorted q/I and
   makes the invariant/Bragg test doubles reject non-finite or non-positive
   inputs; assert the current raw-array path fails with the expected unusable
   post-processing evidence.
2. Import the existing `sanitize_1d_profile()` contract into the temperature
   module and create one auxiliary sanitized profile per sorted frame without
   replacing the original arrays passed to `analyze_single()`.
3. Route only reference invariant/Bragg, per-frame invariant, and peak
   tracking through the auxiliary q/I arrays; preserve existing empty-profile
   fail-closed behavior.
4. Add GREEN assertions for quality provenance, empty-frame degradation, and
   unchanged clean-frame/source-index behavior.
5. Run the focused matrix, exact SAXS matrix, task verifier, and fresh
   full/boundary verifier; update durable memory and checkpoint only the
   explicit allowlist.

## Verification

```powershell
python -m pytest tests/test_saxs_temperature_dirty_frame_postprocessing.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_temperature_empty_series_fail_closed.py tests/test_saxs_temperature_invalid_axis_fail_closed.py tests/test_saxs_temperature_time_axis_fail_closed.py -q --basetemp D:\PolyNexus\PolyNexus_saxs_temperature_dirty_postprocess_20260728
$saxsTests=@(Get-ChildItem tests -File | Where-Object { $_.Name -like 'test_saxs*.py' } | ForEach-Object { $_.FullName })
python -m pytest $saxsTests -q --basetemp D:\PolyNexus\PolyNexus_saxs_temperature_dirty_postprocess_20260728
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-dirty-frame-postprocessing.md --changed --types
git diff --check
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-dirty-frame-postprocessing.md --changed --types --full --boundary
```

## Changed-file allowlist

- `docs/agent/tasks/2026-07-28-saxs-temperature-dirty-frame-postprocessing.md`
- `docs/superpowers/specs/2026-07-28-saxs-temperature-dirty-frame-postprocessing-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-temperature-dirty-frame-postprocessing.md`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_temperature_dirty_frame_postprocessing.py`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`

## Verification result

- TDD RED: `1 failed, 3 warnings`; the failure showed raw NaN q reaching the
  invariant helper.
- GREEN focused temperature matrix: `14 passed, 1 warning`; exact SAXS matrix:
  `425 passed, 8 warnings` in `31.15s`.
- Task-scoped verifier exited `0`: quality `283`, preprocessing `106`,
  task/memory, Ruff, compile, type baseline, and whitespace checks passed.
- A direct dirty-profile replay changed `Q_star` from the pre-fix
  `[nan, nan]` to two finite values while retaining
  `invalid_pairs_dropped`/`q_sorted` actions.
- Fresh full/boundary attempt 1 stopped during collection because a parallel
  untracked `tests/test_test_storage.py` briefly imported a not-yet-created
  `scripts/test_storage.py`. After those files appeared, a second isolated
  attempt with `POLYNEXUS_TEST_ROOT` reached full pytest but timed out at the
  1800-second tool limit without a final summary; boundary audit did not run.

## Evidence

- Dirty/empty focused regression: `2 passed`.
- Exact SAXS matrix: `425 passed, 6 warnings`.
- Task-scoped verifier: exit code `0`; quality `283 passed`, preprocessing
  `106 passed`, Ruff/compile/type/memory/task/whitespace checks passed.
- Fresh full/boundary verifier: `2869 passed, 17 skipped, 12 warnings` in
  `1686.81s`; boundary audit passed; exit code `0`.

## Known limitations

Human scientific review of real temperature trends remains a separate gate.
