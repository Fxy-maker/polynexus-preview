# Joint workspace context identity acceptance

## Result

The compact Joint workspace context line now reuses the existing display-only
identity resolver. A populated single-sample report renders `PA6-A` instead of
the no-data placeholder.

## Boundary

The Joint report, persisted project identity, source-run provenance, metrics,
diagnostics, conflict severity, and scientific interpretation are unchanged.

## Evidence

- TDD RED: `1 failed`; the rendered summary used the translated no-data text.
- Focused regression GREEN: `1 passed in 0.63s`, exit code `0`.
- Focused matrix: `42 passed, 177 deselected in 38.36s`, exit code `0`.
- Structured verifier: exit `0`; quality `287 passed`, preprocessing `106
  passed`, Ruff, compile, type baseline, memory/task, and whitespace checks
  passed. `git diff --check` passed.
- Native Windows Qt Joint route: `1 passed, 16 deselected in 9.20s`, exit code
  `0`. The fresh Results capture shows `PA6-A` in both the task-card source and
  compact workspace context line.
- The explicit allowlist checkpoint is the only commit action for this slice.

## Remaining release boundary

This is a display-state correction. NMR solid-C assignment semantics, Joint
conflict interpretation, restarted-GUI review beyond this route, and final
scientific/release approval remain open.
