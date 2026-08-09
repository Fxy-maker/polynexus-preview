# GUI Performance Recovery Design

**Date:** 2026-08-09

## Goal

Remove the measured GUI stalls caused by full history hydration and unbounded
log rendering, while making an analysis completion visibly interactive before
the non-critical history refresh runs. Add SAXS stage timing evidence without
changing scientific calculations or result semantics.

## Evidence and scope

The production sample database contains 423 analysis runs and about 423 MB of
stored run JSON. `collect_history_rows()` currently traverses samples and
batches, calls `get_analysis_runs()` for every batch, and eagerly decodes every
payload. The measured collection time is about 7--8 seconds. The History page
does this during deferred startup and analysis persistence refreshes it on the
GUI thread.

The GUI also forwards worker logs to an unlimited `QTextEdit`; each line reads
the full document to update the copy button and scrolls immediately. The cost
increases non-linearly as the session log grows.

In scope:

- lightweight, indexed history-list reads with on-demand full record loading;
- bounded, timer-batched GUI log rendering;
- deferred history refresh after a successful analysis is published;
- SAXS stage-duration logging around existing pipeline boundaries;
- focused regression and performance-shape tests.

Out of scope:

- changes to scientific models, numerical thresholds, raw data, result JSON,
  export formats, or sample-history retention;
- automatic database compaction or deletion of historical records;
- redesigning the Results, History, or Plots user interface.

## Design

### History list boundary

`SampleDB` will create indexes for the existing batch and run lookup paths and
will expose `list_analysis_run_headers()`. The new query returns only database
columns needed to sort and render a History row; it deliberately excludes the
large JSON columns. `collect_history_rows()` will prefer this public method and
retain its existing traversal fallback for fake databases used by tests.

The History table will keep header records in its cache. When a user selects a
header record, the existing `get_analysis_run(run_id)` API loads and replaces
only that record with its full payload. Historical list rows without an already
persisted summary show existing neutral empty values until selected; a selected
row preserves the current copy, restore, compare, and confirmation behavior.

### Log rendering boundary

The MainWindow owns a small pending-line buffer and one single-shot `QTimer`.
`log()` and warning-summary output append to this buffer. The timer flushes a
single HTML append operation at a short fixed interval, scrolls once, and keeps
at most 500 document blocks. The copy action becomes enabled on first queued
content without repeatedly materializing the full document.

`flush_pending_log_messages()` remains available for deterministic tests and
window shutdown. The worker-to-signal contract is unchanged.

### Completion priority

Persistence remains synchronous so the newly produced run has a stable ID
before later UI consumers read it. Its history refresh becomes opt-in. The
normal analysis-completion path schedules the refresh through the Qt event
loop after publishing Results and Plots, leaving the event loop a chance to
paint an interactive completed state first. Explicit History refreshes retain
their immediate behavior.

### SAXS timing evidence

The SAXS engine will measure existing high-level pipeline sections with
`time.perf_counter()` and emit one structured INFO line per completed stage.
The timing is diagnostic-only, excludes raw arrays and parameter values, and
does not alter return values, stage order, or error propagation.

## Acceptance criteria

- Refreshing History uses header queries and does not decode any large run JSON
  before the user selects a row.
- Database initialization creates lookup indexes without a destructive
  migration; existing databases remain usable.
- Selecting one header lazily hydrates only that row and preserves existing
  history actions.
- Hundreds of queued log entries create bounded document content and one flush
  per timer cycle.
- Successful analysis completion schedules rather than synchronously performs
  its non-critical History refresh.
- SAXS logs per-stage elapsed durations on success, with unchanged analysis
  results and failures.

## Verification

Run focused history/database, MainWindow, logging, and SAXS tests, then:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-09-gui-performance-recovery.md --changed --types
```

No user data will be removed, compacted, or rewritten as part of this task.
