# Historical Test Storage Name Discovery Design

## Decision

Extend the legacy-directory classifier with bounded historical test naming
families used by PolyNexus's local verification runs. The classifier remains
name-based and conservative: protected words are rejected before any test
pattern is considered.

Recognized families are `full_boundary*`, `native_*_basetemp`, `gallery_*`,
`saxs_*_matrix`, and `Saxs*` diagnostic/test directories. Existing
`pytest_tmp`, `TempPolyNexus*`, malformed user-profile, `PN_*matrix`, and
`PolyNexus_*matrix/_pytest` families remain supported.

The exact directory `测试数据` and names containing `archive`, `review`,
`evidence`, or `baseline` remain protected. This classifier only discovers
candidate directories; existing age, process, Git, approved-root, symlink,
and manifest gates still decide whether cleanup is allowed.

## Rationale

The repository contains historical test output created before managed pytest
basetemps were introduced. Those directories are not covered by the original
small set of naming patterns, so report and clean inventories undercount them.
The new families are narrow enough to avoid treating arbitrary project data as
test output while covering the observed diagnostic naming convention.

## Non-goals

- No deletion, migration, or movement of real data or source files.
- No change to retention, emergency age, process, Git, or protected-path rules.
- No inference from test result text or directory contents.
