# Editor Safety and Self-Contained Project Export Design

Date: 2026-07-19
Status: approved for implementation under the active editor-improvement Goal

## Design decisions

1. `ChartEditor.closeEvent()` owns only the user decision and delegates saving
   to the existing `save_to_target()` contract. It must accept close only when
   the editor is clean, the user chooses Discard, or Save clears the dirty
   state. Save failure leaves the window open.
2. Project packaging belongs in a core service. The service writes a temporary
   zip beside the requested destination, validates every source before writing,
   records SHA-256 checksums, then atomically replaces the destination. It
   refuses an existing destination so an accidental click cannot destroy an
   archive.
3. The package contains a normalized `figure_document.json`, the selected
   figure and sibling publication assets under `assets/`, resolved data sources
   under `sources/`, and `manifest.json`. Document source paths are rewritten
   to bundle-relative paths so the package remains relocatable.
4. GUI code only chooses a destination and displays service results. It does
   not resolve paths, copy files, or construct zip entries.

## Error contract

- Missing or unreadable sources raise a structured export error before a final
  file is created.
- Absolute source paths are allowed only when they are readable files; relative
  paths resolve from the run root for `run_relative`, otherwise from the figure
  directory.
- Path traversal outside the chosen source root is rejected for run-relative
  paths.
- Inline column/value sources are serialized as CSV and do not require an
  external source file.
