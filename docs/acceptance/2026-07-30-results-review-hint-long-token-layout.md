# Results Review Hint long-token layout acceptance

Date: 2026-07-30

The Results Workbench now uses one shared display-only evidence label for the
Summary, Review, and Review Hint surfaces. It preserves source `.text()` values
and supplies invisible break opportunities; the review-hint detail/next labels
also ignore their long-content size hints horizontally.

Fresh evidence:

- The RED layout regression measured a `1188` px panel size hint before the
  follow-up size-policy bound.
- Focused ResultsTablePanel/SAXS evidence/MainWindow results tests passed `26`
  tests in `3.81s`.
- A real SAXS temperature restore probe returned exit code `0`: panel width
  `557`, review-hint detail/next widths `375`/`374`, and workspace content width
  `1188` versus a `1356` viewport.
- The native SAXS temperature route passed `1` test with `16` deselected in
  `17.09s`; its Results capture is in
  `D:\PolyNexus_native_saxs_temp_layout_fixed_20260730`.
- The structured verifier returned exit code `0`, including task/memory checks,
  Ruff, compile, type-baseline, quality (`287 passed`), preprocessing (`106
  passed`), and whitespace checks.

This closes the presentation regression only. Existing scientific and final
release review gates remain open.
