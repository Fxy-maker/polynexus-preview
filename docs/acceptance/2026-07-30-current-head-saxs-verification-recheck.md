# Current-head SAXS verification recheck

Status: SAXS matrix accepted as fresh automated evidence; full/boundary and
human release gates remain open.

The current `b5cbc92` checkout produced a fresh SAXS-only result with the
repository Python 3.14 runtime, offscreen Qt, and a writable workspace
basetemp:

```text
594 passed, 8 warnings in 524.50s (0:08:44)
exit code: 0
```

The warnings are the existing locale deprecation, Arial glyph, EDF geometry
header, and pytest cache-permission warnings. No SAXS assertion failure was
reported.

The separate full/boundary attempt is not accepted as a pass. It reached the
focused quality (`290`) and preprocessing (`106`) gates, then the full suite
crashed with Windows `0xC0000005` in `PySide6\\Qt6Widgets.dll` at about 27%,
with no final pytest summary or boundary result. An isolated ChartEditor probe
passed `57` tests, but a later offscreen full attempt was tool-aborted without
a result. These are verification limitations, not evidence of SAXS analysis
failure.

Storage remained non-destructive: the latest dry-run reported `54` artifacts,
`eligible_bytes=13390550`, `eligible=6`, and `removed=0`. No
`test_storage.py --apply` was run.

The task-scoped verifier completed task-card, memory, Ruff, compile, and type
baseline checks. Its focused quality gate returned `288 passed, 2 failed, 3
warnings` with exit code `1`; both failures are pre-existing locale expectation
mismatches in `tests/test_history_table_service.py` (`Scientific review` is
expected by the tests, while the current locale emits `科学复核`). This is a
verification limitation outside the SAXS audit, not a SAXS assertion failure.

Remaining gates are native Qt full-suite stability, restarted-GUI visual
review, reviewer-owned scientific semantics, and final release authorization.
