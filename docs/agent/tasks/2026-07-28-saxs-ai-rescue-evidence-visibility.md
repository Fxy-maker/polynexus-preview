# SAXS AI rescue evidence visibility

## Goal

Expose the existing SAXS AI rescue plan, decision, replay, and confirmed-rerun
audit as detached public parameters and read-only Results Workbench evidence.

## Non-goals

- No model call, candidate application, deterministic rerun, interpolation, or
  missing-frame repair.
- No new physical/quality threshold or publication-role change.
- No changes to the authoritative Export audit schema or History semantics.
- `apply_allowed` remains a decision field and never means accepted or applied.

## Affected boundaries

- `polynexus/core/saxs_batch_helpers.py`
- `polynexus/core/saxs.py`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_batch_parameters.py`
- `tests/test_saxs_workbench_series_evidence.py`
- This task card, its spec, and plan

## Acceptance criteria

- [x] Existing AI plan/decision/replay/confirmed-rerun values are deep-copied
      into `get_parameters()` for static and series paths when present.
- [x] Workbench reports only valid candidate/decision/replay/audit metadata and
      requires deterministic validation plus existing physical/quality review.
- [x] Empty or malformed values do not create a rescue or acceptance claim.
- [x] Source mappings are not mutated; table, diagnostics, and Export behavior
      remain unchanged.
- [x] Focused tests, complete SAXS matrix, task-scoped verifier, and diff check
      have exact recorded results.
- [x] One explicit `auto_commit.py` checkpoint is created from the allowlist
      below; parallel workspace changes remain untouched.

## Implementation plan

1. Add RED transport and Workbench tests.
2. Add the pure detached copier and attach it in all `get_parameters()` paths.
3. Add the read-only Workbench formatter and join it to the existing review.
4. Run focused/SAXS/task verification, record limitations, and checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_saxs_batch_parameters.py tests/test_saxs_workbench_series_evidence.py --basetemp C:\Temp\PolyNexus_saxs_ai_visibility_redgreen
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_ai_visibility_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-ai-rescue-evidence-visibility.md --changed --types
$exit = $LASTEXITCODE
Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
exit $exit
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q --basetemp C:\Temp\PolyNexus_saxs_ai_visibility_saxs
git diff --check
```

## Known limitations

Full/boundary repository verification is not part of the initial focused
closure and must be reported only if actually completed. Human scientific
review, restarted-GUI inspection, model calls, candidate reruns, and
publication authorization remain outside this task.

## Verification evidence (2026-07-28)

- TDD RED: `3 failed, 44 passed`; failures were the missing AI evidence
  copier, missing temperature parameter keys, and missing Workbench review.
- Focused GREEN matrix:
  `python -m pytest -q tests/test_saxs_batch_parameters.py tests/test_saxs_workbench_series_evidence.py tests/test_saxs_results_table_service.py`
  -> **101 passed**.
- Complete SAXS matrix:
  `python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q`
  with a dedicated basetemp -> **398 passed, 6 warnings**. Warnings are the
  existing Arial CJK glyph and EDF geometry-header warnings.
- Task verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-ai-rescue-evidence-visibility.md --changed --types`
  -> exit 0; task/memory checks, Ruff, compile, quality **283 passed**,
  preprocessing **106 passed**, and whitespace all passed. The verifier also
  discovered the pre-existing untracked `tests/_tmp_phase3/test_visual_audit_capture.py`; it was not changed or added to the checkpoint.
- `git diff --check` passed.
- Full/boundary verification was not run for this transport/visibility slice;
  no full/boundary pass is claimed.

## Explicit changed-file allowlist

- `polynexus/core/saxs_batch_helpers.py`
- `polynexus/core/saxs.py`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_batch_parameters.py`
- `tests/test_saxs_workbench_series_evidence.py`
- `docs/agent/tasks/2026-07-28-saxs-ai-rescue-evidence-visibility.md`
- `docs/superpowers/specs/2026-07-28-saxs-ai-rescue-evidence-visibility-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-ai-rescue-evidence-visibility.md`
