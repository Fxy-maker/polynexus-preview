# Task: SAXS empty-profile fail-closed boundary

**Status:** checkpointed locally; 2026-07-28

## Goal

Keep empty or wholly invalid SAXS q/I frames inside the existing structured
`Unusable` result/evidence contract instead of raising from a numerical method.

## Root-cause evidence

The sanitizer returns empty arrays for empty input. `analyze_single()` then
calls `lorentz_fit_long_period()`, which indexes `q[-1]` and raises
`IndexError: index -1 is out of bounds for axis 0 with size 0`. This prevents
the existing `DataQualityReport` and `GuinierEvidence` from being returned.

## Design decision

Add one early empty-profile branch immediately after sanitization. It reuses
the existing report/evidence builders and returns empty numerical DTO defaults;
it does not create points or alter the non-empty analysis path.

## Non-goals

- No numerical algorithm, threshold, physical gate, rescue, AI, or publication
  role changes.
- No interpolation, padding, frame repair, or fabricated numeric result.
- No unrelated changes to SAXS consumers or parallel GUI/editor/release files.

## Acceptance criteria

- [x] Empty q/I regression fails with the observed `IndexError` before the fix.
- [x] Empty q/I returns a `SAXSResult` with `Unusable` quality and Guinier
  evidence after the fix.
- [x] Existing source/action fields remain preserved in the early branch.
- [x] Exact SAXS matrix and structured verifier pass.
- [x] One explicit allowlist checkpoint is created after fresh verification.

## Affected boundaries

- `polynexus/core/saxs_engine/core.py`
- `tests/test_saxs_empty_profile_fail_closed.py`

## Implementation plan

1. Add a public empty-profile regression that asserts structured quality and
   evidence outputs, then run it RED.
2. Add the minimal early return after sanitization using existing DTO builders
   and no new numeric thresholds.
3. Run focused tests and the complete SAXS matrix.
4. Run the structured verifier and diff check, update durable memory, and create
   one explicit allowlist checkpoint.

## Verification evidence

- TDD RED: `1 failed` with the observed `IndexError` from
  `lorentz_fit_long_period()` at `q[-1]`.
- Focused GREEN: `17 passed` across the empty-profile, structure fail-closed,
  dirty-profile, and quality-contract tests.
- Exact SAXS matrix: `413 passed, 6 warnings`. Warnings are the existing Arial
  glyph notices and EDF geometry-default notices; no test failed.
- Structured verifier: `python scripts/verify.py --task
  docs/agent/tasks/2026-07-28-saxs-empty-profile-fail-closed.md --changed
  --types` passed. Quality gate: `283 passed`; preprocessing gate: `106
  passed`; task/memory, Ruff, compile, type baseline, and whitespace checks
  passed. `git diff --check` passed.
- The full/boundary repository verifier was not run for this scoped SAXS
  boundary task. No push, merge, release, rescue, AI, or publication approval
  is implied.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_empty_profile_red'
python -m pytest -q tests/test_saxs_empty_profile_fail_closed.py
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_empty_profile_focus'
python -m pytest -q tests/test_saxs_empty_profile_fail_closed.py tests/test_saxs_structure_params_fail_closed.py tests/test_saxs_dirty_profile_sanitization.py tests/test_saxs_quality_contracts.py
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_empty_profile_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-empty-profile-fail-closed.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/core.py`
- `tests/test_saxs_empty_profile_fail_closed.py`
- `docs/agent/tasks/2026-07-28-saxs-empty-profile-fail-closed.md`
- `docs/superpowers/specs/2026-07-28-saxs-empty-profile-fail-closed-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-empty-profile-fail-closed.md`
- `docs/agent/memory/current-state.md`
- `docs/agent/memory/active-work.md`
