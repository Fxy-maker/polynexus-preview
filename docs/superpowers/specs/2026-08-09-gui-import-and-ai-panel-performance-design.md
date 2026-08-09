# GUI Import and AI Panel Performance Recovery Design

## Evidence

On the production local database, importing
`C:\Users\Fan Xuyi\Desktop\edf\8` took 18.662 seconds after file-type
detection. Detection itself took 0.001 seconds. The import path called
`_update_workspace_context()` three times; each call rebuilt work memory by
visiting every batch and decoding every historical analysis-run JSON payload.
The profile recorded 552 batch reads and 5,408 JSON decodes.

The Results-page comparison card, immediately above the AI tuning entry card,
took 3.307 seconds to populate for a SAXS strain result. It decoded 357 run
payloads on the GUI thread.

## Decision

Keep full run documents authoritative, but make lightweight UI surfaces use
indexed headers. Work memory will obtain sample/batch counts and a recent run
header without iterating batches. It will hydrate at most that one recent run
only when metric text is needed. The comparison selector will rank bounded
run headers; clicking Open comparison will hydrate only the chosen baseline.

## Boundaries

- Do not change analysis algorithms, SQLite schema semantics, result JSON,
  historical exports, or comparison calculations.
- Preserve current labels where their header fields are available. A chosen
  comparison record is always fully hydrated before detailed comparison.
- Keep database work synchronous but bounded; no cross-thread SQLite access.

The header query includes only relational `sample_id` and `sample_name` in
addition to run columns, so comparison selection preserves same-sample
priority without reading result JSON. Source-file affinity remains unavailable
until a user opens a single selected comparison record.

## Acceptance

- Import and workspace refresh do not call `get_analysis_runs()` for each
  batch when building work memory.
- Results comparison discovery does not decode full run JSON documents.
- Opening a comparison loads only its selected full historical record.
- Existing result/history tests and structured verification remain green.
