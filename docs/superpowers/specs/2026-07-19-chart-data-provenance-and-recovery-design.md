# Chart Data Provenance and Historical Recovery Design

Date: 2026-07-19
Status: approved for implementation under the active editor-improvement Goal

## Goal

Ensure that a chart viewer displays the data that produced the selected figure,
and ensure that historical recovery uses a widget with the correct gallery
contract.

## Current failure boundary

`ChartViewer.load_figure()` currently accepts an optional `raw_data` argument.
The main window passes the current technique's raw data for any selected figure,
while `ChartGallery._open_viewer()` passes no raw data at all. This creates two
user-visible failures: an empty data tab when opening from a card, or data from
another figure when opening through the main window.

The historical recovery path creates `ChartViewer` and calls `load_entries()`.
`load_entries()` is implemented by `ChartGallery`, so the recovery action does
not satisfy its runtime widget contract.

## Design

### Source resolution

Add a small, GUI-independent resolver in the existing figure-window service
boundary. Its input is a figure path plus optional gallery entry/document. It
returns a normalized result containing:

- `headers` and `rows` suitable for `ChartViewer`;
- the exact source path or inline source identifier;
- a human-readable status/error when no source is available.

Resolution order:

1. Use the selected figure document's `data_sources` and each plot object's
   `data_ref` to identify the exact source.
2. Resolve `run_relative` paths through the gallery entry's `run_root`.
3. Resolve absolute paths directly.
4. Use inline `data` only when the document explicitly contains it.
5. Retain the old caller-provided `raw_data` as a compatibility fallback only
   when no figure document/source metadata exists.

The resolver must never substitute the current technique's raw data for a
different selected figure when figure-specific metadata exists.

### Viewer context

`ChartViewer.load_figure()` will accept optional `entry` and `document` context
without removing the existing `raw_data` argument. The viewer stores a source
status line and uses the resolver before populating the data table. The figure
preview remains usable even when data loading fails.

### Historical recovery

The recovery window will use `ChartGallery`, because it owns `load_entries()`
and already models entry selection, assets, and editor signals. It may open a
standalone `ChartViewer` for one selected recovery entry, but the recovery
gallery itself must remain separate from the active gallery and must not change
the active run.

## Error handling

- Missing source: show a localized “data source unavailable” status.
- Invalid source shape: show a localized “data source unreadable” status.
- Preview failure: preserve the existing preview failure behavior.
- Legacy image without data metadata: show the image and explicitly state that
  no source data is attached.

## Testing

- Pure resolver tests for absolute, run-relative, inline, missing, and
  `data_ref`-selected sources.
- Viewer test proving entry-specific data wins over unrelated fallback data.
- Viewer test proving missing data does not clear the image preview.
- Main-window recovery test using the real `ChartGallery` class contract.

## Compatibility

No scientific result contracts or figure-generation providers change. Existing
callers that pass `raw_data` continue to work for documents without provenance.
