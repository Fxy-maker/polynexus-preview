# SAXS Static Figure Dirty Projection Acceptance

Status: accepted for this automated task boundary; scientific and release gates
remain separate.

The static Figure provider now converts q/intensity elements independently at
the existing `_numeric_pairs` boundary. Invalid elements become `NaN` in a
fresh projection and are removed by the pre-existing finite/positive filters;
all-invalid or undersized frames remain fail-closed. Caller-owned arrays,
analysis, quality gates, physical thresholds, AI/rescue behavior, evidence
levels, and publication roles are unchanged.

Evidence:

- RED: `1 failed, 2 deselected` from the dirty static projection regression.
- GREEN: `2 passed, 1 deselected`; full static panel file `3 passed`.
- Task verifier: exit `0`, quality `287 passed`, preprocessing `106 passed`,
  Ruff/compile/type/whitespace passed.
- Exact SAXS matrix: `535 passed, 6 warnings in 340.57s`, exit `0`.
- Storage: report/clean dry-run `292 artifacts, 40 eligible, 252 protected,
  0 removed`; no `--apply`, delete, move, or migration.
- Explicit allowlist checkpoint created after the above evidence; commit hash
  is reported in the handoff.

Known limitations: this is only the static Figure public boundary. Temperature
and strain Figure projections, scientific interpretation, restarted-GUI review,
instrument-level review, AI/rescue acceptance, publication authorization, and
human release approval remain open or separate.
