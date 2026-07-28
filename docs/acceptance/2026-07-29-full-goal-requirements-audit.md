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

The overall goal is not complete: restarted-GUI content was not visible because
the Windows session was locked, and IR mapping/ROI semantics, NMR solid-C
assignment policy, Joint conflict interpretation, and final release approval
remain human decisions. No test data was deleted or migrated.
