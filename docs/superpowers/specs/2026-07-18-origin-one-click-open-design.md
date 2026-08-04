# Origin One-Click Open Design

**Date:** 2026-07-18  
**Status:** approved in conversation

## Goal

Clicking ChartEditor's `Export to Origin` action should open or activate the
installed OriginPro application, import the current figure's data, create a
visible Origin graph, and save the native project when the native adapter is
available.

## Non-goals

- Do not fabricate an `.opju` file without Origin performing the native save.
- Do not remove the portable `Origin_Export` fallback.
- Do not silently launch arbitrary executables; only use the configured
  `ORIGIN_EXE` path or a validated Origin capability path.

## Design

The existing export action remains the single user entry point. It will pass a
request to the adapter chain without requiring the user to select an output
directory first. The native `originpro` facade owns application visibility and
activation: it starts/attaches to Origin, imports prepared CSV sources, creates
the graph, saves the native project, and leaves the Origin window visible.

If native Origin automation is unavailable, the service keeps the portable
package fallback and reports that it created an Origin-compatible package rather
than implying that a live Origin graph was opened.

The GUI remains an `ExportResult` consumer. Launch/activation and graph creation
stay inside the Origin adapter boundary.

## Acceptance criteria

- A native-capable request reaches an Origin session and leaves its window
  visible with at least one graph.
- The ChartEditor action does not ask for an output directory before the native
  workflow starts.
- The portable fallback remains available and clearly reports its limitation.
- Adapter tests cover activation, graph creation, saving, and failure handling;
  existing ChartEditor and Origin suites remain green.
