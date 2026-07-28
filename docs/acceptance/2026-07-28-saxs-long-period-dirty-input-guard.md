# SAXS long-period helper dirty-input guard acceptance

Date: 2026-07-28
Task: `docs/agent/tasks/2026-07-28-saxs-long-period-dirty-input-guard.md`
Status: automated acceptance complete; amended checkpoint hash is reported in final handoff

## Change

The public Bragg, Lorentz, and correlation long-period helper boundaries now
reuse the existing detached `sanitize_1d_profile()` survivors. Empty survivor
profiles return stable diagnostic shapes before any `q[-1]` access. Existing
windows, fits, extrapolation, and physical gates remain unchanged.

## Evidence so far

- TDD RED: `3 failed in 0.54s`; failures were the expected raw dirty-input
  type/indexing errors.
- Focused GREEN: `3 passed in 0.19s`, exit code `0`.
- Exact SAXS matrix: `490 passed, 6 warnings in 239.12s`, exit code `0`, using
  `D:\PolyNexus_saxs_long_period_dirty_matrix`.
- The warnings are the existing Arial glyph and missing-EDF-geometry warnings.

## Scientific boundary

This change only routes helper inputs through the existing deterministic
sanitizer. It adds no interpolation, aggregation, extrapolation, frame repair,
new threshold, rescue, AI action, publication-role change, or physical
interpretation. Empty or insufficient profiles remain diagnostic/NaN under the
existing contracts.

Structured verification exited `0`: task/memory checks, Ruff, compile, type
baseline selection, quality (`287 passed`), preprocessing (`106 passed`), and
whitespace all passed. `git diff --check` exited `0`. The explicit allowlist
checkpoint was created with the explicit allowlist and then closed with a
doc-only amend; its final hash is reported in the handoff.
