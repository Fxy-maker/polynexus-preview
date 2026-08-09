---
task_id: 2026-08-09-gui-performance-recovery
kind: performance
status: ready-for-checkpoint
date: 2026-08-09
title: Recover GUI responsiveness for history, logging, and SAXS diagnostics
---

# GUI performance recovery

## Goal

Remove measured UI stalls caused by all-history JSON hydration and unbounded
GUI log updates, without changing scientific computations or stored results.

## Boundaries

- `polynexus.data.sample_db`: indexed lightweight list reads only.
- `polynexus.gui`: history hydration, log rendering, and completion scheduling.
- `polynexus.core.saxs`: diagnostic-only stage timing.

## Affected boundaries

- `polynexus/data/sample_db.py`
- `polynexus/gui/analysis_history_service.py`
- `polynexus/gui/main_window*.py`
- `polynexus/core/engine.py` and `polynexus/core/saxs.py`
- Focused regression tests and task/design/plan memory documents.

## Implementation plan

1. Add indexed header-only history queries and lazy full-record hydration.
2. Buffer and bound GUI log rendering, including deterministic shutdown flush.
3. Defer non-critical History refresh after analysis completion.
4. Add optional SAXS load/preprocess/analyze/plot stage timing diagnostics.
5. Run focused tests, structured verification, and create an explicit local
   checkpoint commit.

## Acceptance criteria

- [x] History listing does not fetch or JSON-decode full result payloads.
- [x] A selected history entry loads its full record only when needed.
- [x] GUI logging is buffered, bounded, and deterministic to flush in tests.
- [x] Analysis completion yields to the event loop before its History refresh.
- [x] SAXS records stage durations without changing results or failure behavior.

## Verification

```powershell
python -m pytest tests/test_sample_db.py tests/test_analysis_history_service.py tests/test_main_window_persistence.py tests/test_gui_startup.py -q
python scripts/verify.py --task docs/agent/tasks/2026-08-09-gui-performance-recovery.md --changed --types
```

## Non-goals

No raw data, historical runs, scientific thresholds, numerical output, exports,
or database cleanup operations are modified.

## Evidence and limitation

Focused regressions cover header queries, lazy hydration/export, log buffering,
completion scheduling, and SAXS stage timing. A batch comparison candidate list
is intentionally bounded to 500 headers; larger batches require an explicit
follow-up design if that cap becomes a practical workload.
