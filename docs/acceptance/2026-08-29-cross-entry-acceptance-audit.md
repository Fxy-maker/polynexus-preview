# Cross-entry acceptance audit — 2026-08-29

## Results

The focused GUI/gallery/result-table/project workflow matrix passed **147
tests**. It covers `EvidencePackageView`, chart gallery filtering, GUI result
tables and persistence, project workflow CLI/Codex summaries, ARS handoff, and
package validation.

Native GUI automation passed **9 tests** and skipped **17** window-capture
cases because the current test environment has no supported display session.
The skips are environmental, not silently treated as passes.

The v011 package remains the shared source of truth: all 42 snapshots contain a
completed `ComputeRun` and `metric_manifest`; GUI, CLI/Codex, and ARS use the
same package-relative run, table, figure, and evidence projections.

## Boundaries still open

- Scientific promotion of figures and metrics still requires human review.
- The historical full-suite failures remain a separate release boundary; no
  release-green claim is made.
- A real NMR JDF sensitivity replay was not used as an acceptance gate because
  the vendor file fit exceeded the practical diagnostic timeout; synthetic and
  focused provider tests cover the explicit region-window contract.
