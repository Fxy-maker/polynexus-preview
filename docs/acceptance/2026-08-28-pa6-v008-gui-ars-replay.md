# PA6 v008 GUI/ARS replay acceptance — 2026-08-28

The six-sample project was replayed through the shared public workflow at
`D:\PolyNexus-six-sample-replay-20260827-v007`.

- 42 planned runs: 40 `review_required`, one PA11 isothermal provider failure,
  and one PA12-50 isothermal canonical qualification block.
- Original inputs remained unchanged; the replay uses the existing source
  hashes and writes only derived `.polynexus` state.
- Evidence package:
  `D:\PolyNexus-six-sample-replay-20260827-v007\.polynexus\evidence\pa6-six-sample-v008-v001`
- Package contents: 40 runs, 268 evidence items, 1068 logical figures, and
  268 pending review decisions. The package includes
  `review-decision.json` and package-relative run snapshots.

GUI restart/readback verification loaded the package twice through
`EvidencePackageDialog`:

- 1068 figures visible initially and after reload;
- 72 SAXS figures after technique filtering;
- 4 technique selector entries, read-only gallery enabled.

The package remains `review_required`. This proves the shared GUI/CLI/ARS
object path and provenance, not scientific publication approval.
