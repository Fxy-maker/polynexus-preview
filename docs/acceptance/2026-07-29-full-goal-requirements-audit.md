# Full-software goal requirements audit

The current evidence audit maps the full task as follows:

- Shared Workbench/Figure contracts: `57 passed`.
- Real published lifecycle: `15 passed, 11 warnings`, exit `0`.
- Golden preprocessing: `3 passed`, exit `0`.
- AI-off/failure/fallback: `25 passed`, exit `0`.
- Full repository/boundary: `2986 passed, 17 skipped, 12 warnings`; direct
  boundary exit `0`.
- Mode coverage: SAXS `3`, DSC `3`, WAXS `3` including strain/2D, IR `2`
  plus synthetic mapping, NMR `4`, and Joint transport/synthetic lifecycle.

The official Thermo/OMNIC Picta mapping profile is now documented for IR;
sample-level ROI, flattening order, detector calibration, and source-matched
review remain open. NMR JEOL axis calibration remains explicitly unconfirmed,
and solid-C assignment/Xc stays assignment-limited. Joint AI fallback
provenance and source/conflict preservation are covered, while conflict
precedence remains reviewer-owned.

The overall goal is not complete: current native route captures and an unlocked
canonical shell inspection provide route evidence, but they do not replace
complete human all-mode visual review. IR sample-level mapping/ROI calibration,
NMR solid-C assignment policy, Joint conflict interpretation, and final release
approval remain human decisions. No test data was deleted or migrated.
