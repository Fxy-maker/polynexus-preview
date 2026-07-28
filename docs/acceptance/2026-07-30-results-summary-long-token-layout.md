# Results Summary long-token layout acceptance

Date: 2026-07-30

The Results Workbench now gives long diagnostic tokens invisible break
opportunities for display while preserving the exact source string returned by
the evidence labels. This addresses clipping such as comma-delimited reason
codes in SAXS temperature Results without changing scientific content.

Evidence:

- The regression first failed because the label minimum width was `14664` px;
  after the fix, the focused layout/semantic matrix passed `12` tests.
- Review service passed `28` tests and the Results/Persistence summary slice
  passed `52` tests.
- The structured verifier returned exit code `0`, including task/memory checks,
  Ruff, compile, type-baseline, quality (`287 passed`), preprocessing (`106
  passed`), and whitespace checks.
- Fresh native Windows Qt validation passed `17` tests with `15` warnings in
  `307.72s` (exit code `0`). The run produced 68 Results/Gallery/History/Editor
  captures under
  `D:\PolyNexus_native_all_routes_long_token_wrap_20260730` and exercised the
  no-Origin PackageExporter fallback.

This is a presentation regression acceptance, not scientific sign-off. The
existing IR mapping, NMR solid-C, Joint, SAXS diagnostic, and final release
review gates remain open.
