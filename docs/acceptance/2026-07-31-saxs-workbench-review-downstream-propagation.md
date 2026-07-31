# SAXS Workbench Review Downstream Propagation Acceptance

## Scope

This acceptance note covers only transport of an existing, reviewer-owned SAXS
scientific-review record from the current `AnalysisResult` into newly built
Figure/Manifest and Export evidence. It does not approve the underlying
scientific interpretation or publication release.

## Required evidence

- TDD RED: Figure/Manifest and Export regressions fail against the config-only
  reader before the adapter change.
- TDD GREEN: the same focused tests pass after the result-first resolver is
  added.
- Structured verifier and SAXS consumer matrix have complete summaries and
  exit code `0`, or their exact limitation is recorded.
- Storage report and clean are dry-run only; no `--apply`.
- The final checkpoint contains only the explicit task allowlist.

## Scientific boundary

The review record is provenance/evidence. Existing scope, source, status, and
physical-quality contracts remain authoritative. An accepted
`saxs.1d`/`saxs.2d` review is not a publication approval and does not alter
quality levels, physical gates, AI/rescue, or figure roles.

## Verification record

- RED: Figure `2 failed, 31 deselected`; Export `1 failed, 13 deselected`.
- GREEN/focused final slice: `71 passed in 9.95s`, exit code `0`.
- Structured verifier with C: external cache/temp overrides: exit code `0`,
  quality `297 passed`, preprocessing `106 passed`, Ruff/compile/type/
  whitespace/task checks passed.
- Full SAXS matrix: `4 failed, 652 passed, 6 warnings in 444.43s`; it was
  not a pass because two explicit empty-review compatibility tests were fixed
  after that run, and two GUI confirmation routes failed to open the default
  D: SampleDB with `sqlite3.OperationalError: disk I/O error` while D: had no
  free space.
- Storage report/clean: exit code `0`, `dry-run`; final inventory `50`
  artifacts, `1,368,544,565` bytes, `12` emergency-eligible entries and no
  removal. No `--apply` was used.
- The explicit seven-file allowlist checkpoint was created without push. The
  D: capacity limitation and human scientific/publication gates remain open.
