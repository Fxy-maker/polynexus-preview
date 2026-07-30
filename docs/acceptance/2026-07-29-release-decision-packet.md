# Release decision packet acceptance

Status: conditional decision recorded; the overall software goal remains
active.

The packet separates the remaining release gates into four decisions:

1. unlocked canonical-GUI visual review;
2. IR sample-level coordinate/ROI/calibration acceptance;
3. NMR solid-C assignment and Xc promotion policy;
4. Joint conflict precedence and conclusion policy.

Current automated evidence is recorded in the full-goal audit and native route
acceptance records. The official Thermo/OMNIC Picta rule profile is recorded in
`docs/acceptance/2026-07-30-ir-thermo-mapping-semantics.md`: X is the map-column
Stage-X axis, Y is the map-row Stage-Y axis, both use `um`, the stage-home
origin is `(0, 0)`, and ROI bounds follow the vendor step-size grid. Because
the workspace has no native 2D map or coordinate export, sample-specific ROI,
flattening order, detector calibration, and source-matched reviewer acceptance
remain unavailable. The project owner confirmed the conservative disposition:
IR mapping remains diagnostic-only; NMR solid-C remains assignment-limited and
cannot promote Xc; and unresolved Joint conflicts remain diagnostic-only. No
scientific conclusion beyond those boundaries is inferred by this packet.

The remaining conditional criteria cannot be closed by pytest or
`boundary_audit.py`; they require the source-specific evidence, restarted-GUI
review, and separate SAXS decision listed below.

## Unlocked canonical GUI recheck

The canonical GUI was inspected live from `D:\PolyNexus` after the user
confirmed that the desktop was already unlocked. The window was responsive and
loaded the read-only `C:\Users\Fan Xuyi\Desktop\DSC\PA6.txt` fixture.

- Results displayed the Results Workbench, Work memory (`174 samples | 181
  batches`), Key results, and the existing review surface.
- Plots displayed the manifest-only Figure Gallery with `0 figures` for the
  unrun session and the explicit `Historical figure recovery` action.
- History displayed the populated history table and the available `Restore`,
  `Rerun`, `Confirm result`, and `Compare` controls.

This records a live shell/workbench visual check, not an all-mode publication
approval. The all-mode native route evidence remains the automated 17-case /
68-capture matrix; the three scientific dispositions below are recorded, while
the final release remains conditional.

## Current-checkout evidence recheck

- Joint real-data transport plus the shared synthetic lifecycle passed as
  `2 passed in 26.08s`, exit code `0`, with an external D: basetemp.
- The cross-technique AI-off/failure/fallback matrix passed as `25 passed in
  0.42s`, exit code `0`, with an external D: basetemp. This verifies safety
  decisions only; it does not add Joint to the single-technique preprocessing
  contract or establish scientific quality.
- A Qt window capture showed the live Results Workbench, manifest-only
  Plots/Gallery empty state, and History table/actions. The OS-level screenshot
  helper captured desktop wallpaper instead of the application window, so the
  visual result remains supplementary and the full restarted-GUI gate stays
  open.
- The current-checkout Joint recheck expanded the automated evidence without
  changing any scientific policy: real transport, synthetic lifecycle, and
  report dataset checks passed `10` tests in `28.10s`; legacy History fallback
  checks passed `4` tests in `0.45s`; and the Joint consumer/coordinator,
  provider, diagnostics, and NMR provenance matrix passed `18` tests in
  `12.99s`. All commands exited `0` with D:-isolated basetemps.
- These results confirm provenance and route behavior only. They do not choose
  conflict precedence, define the minimum evidence for a Joint conclusion, or
  promote unresolved conflicts beyond diagnostic status.
- No reviewer record, scientific role, or release state changed during this
  recheck.

## Reviewer decision (2026-07-30)

The project owner confirmed the following fail-closed decisions in the current
task:

- IR uses the official Thermo/OMNIC Picta coordinate profile, but the current
  1D/temperature inputs do not authorize sample-specific ROI, flattening, or
  detector calibration. Mapping stays diagnostic-only.
- NMR solid-C has no approved assignment truth set in the supplied files.
  Ambiguous peaks remain unassigned, the axis remains explicitly uncalibrated,
  and Xc cannot leave `assignment_limited`.
- Joint assigns no automatic scientific priority to one technique. Operational
  severity remains `ERROR` -> blocked and `WARN` -> conditional; unresolved
  scientific conflicts stay diagnostic-only.

The non-SAXS release decision is therefore `conditional`, with the remaining
conditions being source-specific evidence, restarted-GUI all-mode review, and
the separate SAXS release decision. This is a reviewer decision record, not a
claim that those missing inputs or gates have been supplied.

## Raw fixture inventory recheck (2026-07-30)

The supplied real-data directories were inspected read-only before treating
the remaining scientific fields as unavailable:

- `D:\PolyNexus\测试数据\IR` contains only `普通红外` and `原位变温红外`.
  The former contains SPA plus 1D `TXT_results`; the latter contains
  temperature CSV files and generated temperature-analysis output. No native
  2D mapping payload, coordinate export, ROI definition, or detector
  calibration file was found. The generated temperature heatmap is not a
  native mapping source.
- `D:\PolyNexus\测试数据\NMR\固体nmr碳谱` contains seven JDF/bin files. The
  reader exposes `SCANS`, `TOTAL_SCANS`, `X_OFFSET`, `X_FREQ`, `X_SWEEP`, and
  related raw fields, but every file is classified as
  `ppm_axis_source=default_range`, `ppm_axis_reason=jeol_metadata_units_unconfirmed`,
  `ppm_axis_calibrated=false`, with display range `240.0..-20.0 ppm`.
  The files do not provide an explicit assignment truth set or a
  crystalline/amorphous phase-assignment record usable for Xc promotion.

This confirms that `review_missing` for IR mapping and NMR solid-C is a
source-evidence boundary, not an omitted parser step. No real input or
generated dataset was changed.
