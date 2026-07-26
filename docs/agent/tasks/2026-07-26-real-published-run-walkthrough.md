# Real published-run walkthrough matrix

## Goal

Turn repository real fixtures into a repeatable shared-lifecycle acceptance
matrix: engine run -> active Manifest Gallery -> Editor working/published
revision -> export bundle -> MainWindow History restore.

## Non-goals

- Do not alter scientific thresholds, vendor semantics, or publication-role
  policy.
- Do not treat a validation-warning/error result as a scientific sign-off.
- Do not cover IR mapping vendor semantics, Joint scientific conclusions, or
  the bounded-timeout real directories in this task.

## Affected boundaries

- Real repository fixtures under `测试数据/`.
- `polynexus.core.engine.get_engine` and each engine's existing
  `run_pipeline` publication route.
- Shared `FigureProjectService`, manifest-only Gallery, export-context helpers,
  and `MainWindow._restore_history_record`.
- Qt offscreen lifecycle cleanup in the new regression module.

## Acceptance criteria

- [x] DSC standard/isothermal/non-isothermal, SAXS static, WAXS
  static/temperature, IR standard, and NMR liquid/solid H/C each complete the
  shared walkthrough against a real fixture.
- [x] The selected Main entry preserves its run ID through working save,
  published revision, export `metadata/runs/`, active pointer, and History
  restore.
- [x] Scientific validation state remains observable; the test does not assert
  that warnings or diagnostic-only results are publishable science. When the
  non-isothermal fixture has no Main figure, the lifecycle uses its existing
  SI conversion entry and preserves that role.
- [x] Focused test and task-scoped verifier pass.

## Implementation plan

1. Add a parameterized real-fixture test that invokes the existing engine
   pipeline and asserts a manifest-backed Gallery.
2. Reuse the public figure project, export-context, and History restore
   services to exercise Editor revisions, provenance, and run restoration.
3. Run the real matrix with an external basetemp, then update the acceptance
   ledger and memory with exact counts and any scientific warnings.

## Verification

```powershell
python -m pytest --basetemp=C:\Temp\PolyNexus_real_walkthrough tests\test_real_published_run_walkthrough.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-26-real-published-run-walkthrough.md --changed --types
```

## Changed-file allowlist

- `tests/test_real_published_run_walkthrough.py`
- this task card
- `docs/acceptance/2026-07-26-real-published-run-audit.md`
- real-run memory files only when fresh results change status
