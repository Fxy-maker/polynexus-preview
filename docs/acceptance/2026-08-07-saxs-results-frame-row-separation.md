# SAXS Results Frame Row Separation Acceptance

Date: 2026-08-07
Task: `docs/agent/tasks/2026-08-07-saxs-results-frame-row-separation.md`
Status: focused and structured automated acceptance passed

## Behavior

- SAXS strain primary rows remain one-to-one with `_batch_data`; row counts
  follow the actual analyzed sequence length and are never fixed at five.
- Detail and diagnostic row collections contain frame rows plus the existing
  batch-summary row. Detached orientation-track observations no longer appear
  as repeated sample frames with empty file, long-period, and q-peak cells.
- `orientation_tracking_evidence` and `_orientation_tracking_rows` remain in
  the detached payload. Nested tracking evidence remains serialized in the
  batch-summary diagnostic cell and the adapter does not mutate its input.
- SAXS analysis, tracking, axis, and reliability semantics are unchanged.

## Evidence

- RED: the new regression reproduced `11` detail rows instead of the expected
  `6` for five frames and five detached tracking observations.
- GREEN: the focused regression passed after removing the presentation-only
  append.
- Complete result-table module: `59 passed in 0.17s`.
- Workbench/transport matrix: `29 passed in 0.26s`.
- Read-only real EDF 8 replay: five frame rows, six detail rows, and six
  diagnostic rows including the summary.
- Structured verification exited `0`: task and memory checks, Ruff, compile,
  quality `297 passed`, preprocessing `107 passed`, and whitespace passed.

Commands:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_saxs_results_table_service.py
python -m pytest -p no:cacheprovider -q tests/test_saxs_workbench_series_evidence.py tests/test_saxs_orientation_tracking_transport.py
python scripts/verify.py --task docs/agent/tasks/2026-08-07-saxs-results-frame-row-separation.md --changed --types
git diff --check
```

The read-only EDF replay used `Path.home() / "Desktop" / "edf" / "8"` and
asserted the presentation counts after a normal load/preprocess/analyze flow;
the external check is unavailable when that local five-file fixture is absent.

## Known limitation

A broader GUI integration matrix returned `11 passed, 1 failed in 168.27s`.
The failure is an unrelated pre-existing language-state symptom in history
restore (`Parameter` expected, `歌方` observed); it does not use the changed SAXS
presentation projection. A dedicated orientation-track table remains a future
enhancement rather than part of this repair.

The broader command was:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_unified_tables_gui_integration.py tests/test_saxs_orientation_tracking_transport.py
```

Its failing node was
`test_history_restore_without_submodule_clears_stale_structured_context`.
