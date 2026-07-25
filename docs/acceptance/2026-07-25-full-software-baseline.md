# PolyNexus full-software baseline

Date: 2026-07-25
Branch: `codex/origin-editor-usable-controls`
Scope: shared lifecycle, Results Workbench, SAXS, DSC, WAXS, IR, NMR, Joint.

This is an evidence ledger, not a release approval. A mode is only complete
when the entire vertical definition in the full-software task card is proven.

## Shared platform

| Boundary | Current implementation | Evidence | Status |
|---|---|---|---|
| Typed result/evidence presentation | `AnalysisResult`/evidence adapters, `ResultsTableModel`, typed Workbench profiles | quality gate and Workbench tests | foundation delivered |
| Figure lifecycle | `FigureDefinition` -> `FigurePipeline` -> `RunFigureManifest` -> manifest-only Gallery -> ChartEditor | shared figure, manifest, Gallery, Editor tests | foundation delivered |
| History/persistence | SQLite analysis runs, context restore, export context | analysis-run/history/export tests | foundation delivered |
| Export/provenance | report/data/metadata bundle, Origin adapters, preserved `metadata/runs/<run_id>/` | export-context and Origin tests | foundation delivered; release audit open |

## Mode ledger

| Mode | Analysis/result contract | Figure/Manifest | Workbench | History/export | AI-off/fallback/real/visual |
|---|---|---|---|---|---|
| SAXS static | existing engine/evidence/result table | provider and publication IDs | customized | covered by focused regressions | human and release audit open |
| SAXS temperature | evolution/Avrami/condition evidence | waterfall plus evolution/support/diagnostic IDs | customized | covered by focused regressions | human and release audit open |
| SAXS strain | morphology/orientation/phase evidence | sequence/support/diagnostic IDs | customized | covered by focused regressions | human and release audit open |
| DSC standard | thermal events, baseline/integration diagnostics | standard provider IDs | customized tabs/profile | existing export/history contracts | release audit open |
| DSC isothermal | crystallization/Avrami/fit diagnostics | isothermal provider IDs | customized tabs/profile | existing export/history contracts | release audit open |
| DSC non-isothermal | conversion/kinetic-method diagnostics | non-isothermal provider IDs | customized tabs/profile | existing export/history contracts | release audit open |
| WAXS static | phase/size/orientation evidence | static provider IDs | customized tabs/profile | existing export/history contracts | release audit open |
| WAXS temperature | transition/trend evidence | temperature provider IDs | customized tabs/profile | existing export/history contracts | release audit open |
| WAXS strain/2D | orientation/phase/size and image-grid contracts | strain/2D provider IDs | customized tabs/profile | existing export/history contracts | release audit open |
| IR standard | spectrum/peak/band/evidence result | standard provider IDs | customized profile | existing export/history contracts | mapping-independent release audit open |
| IR temperature-2D | matrix, transition bands, 2D-COS evidence | heatmap/tracking/indices/COS IDs | customized profile | existing export/history contracts | release audit open |
| IR mapping/ROI | registry/template only; no agreed map/ROI input contract | no mapping provider | profile only | not proven | blocked on scientific data contract |
| NMR liquid H/C | peak, assignment, solvent and quality evidence | spectrum/deconvolution/comparison IDs | four partition profiles | CSV/API compatibility restored; real engine smoke passed | GUI/visual/release audit open |
| NMR solid H/C | assignment-gated phase/Xc evidence | assignment-gated provider IDs | four partition profiles | CSV/API compatibility restored; real engine smoke passed | GUI/visual/release audit open |
| Joint | cross-technique rows, validations and provenance context | crystallinity/multiscale/coverage IDs | custom typed report Workbench | completion + restore + export context covered | conflict/fallback/real/visual audit open |

## Core test evidence

With an external pytest basetemp, the current core matrices pass:

- SAXS: 210 passed (4 font glyph warnings)
- DSC: 64 passed
- WAXS: 46 passed
- IR: 30 passed
- NMR: 24 passed
- Joint: 18 passed
- Shared quality gate: 282 passed
- Preprocessing gate: 103 passed

These counts prove the selected contracts, not the complete vertical release
definition. A mixed GUI suite previously hit Windows Qt cleanup failure in
`ChartEditor.closeEvent`; that run is not used as release evidence.

## Open acceptance gates

1. Define and implement IR mapping/ROI input, invalid-pixel, ROI spectra, and
   map provenance contracts without guessing instrument semantics.
2. Exercise every mode through a real published run: active Manifest, Gallery
   selection, Editor entry, export bundle, and restored History.
3. Add or verify AI-off, AI-failure, fallback, low-confidence, invalid-evidence,
   and missing-condition behavior across all modes.
4. Run restarted-GUI visual walkthrough and human scientific review for each
   Workbench and publication role.
5. Run the full boundary/release verifier and record the release decision.
