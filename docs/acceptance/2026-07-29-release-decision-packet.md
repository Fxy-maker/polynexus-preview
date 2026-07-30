# Release decision packet acceptance

Status: awaiting human input; the overall software goal remains active.

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
remain unverified. The repository therefore keeps IR mapping, NMR solid-C, and
unresolved Joint results diagnostic or assignment-limited until the remaining
fields are confirmed. No scientific conclusion or release approval is inferred
by this packet.

The unchecked criteria cannot be closed by pytest or `boundary_audit.py`; they
require an authorized scientific/release reviewer.

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
68-capture matrix, and the IR, NMR solid-C, Joint, and final release decisions
remain open below.

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
