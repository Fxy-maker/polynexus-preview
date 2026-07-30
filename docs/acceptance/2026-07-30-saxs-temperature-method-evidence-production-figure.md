# SAXS Temperature Method Evidence Production Figure Acceptance

## Scope

The production temperature SAXS Figure provider now emits
`saxs.series.temperature.method_evidence` when existing per-frame Porod,
Kratky, invariant, or lamellar evidence is present. It binds evidence through
unique `source_index` values, preserves nullable audit rows, and sends only
finite existing pairs to renderer sources. The Figure remains diagnostic-only.

## Evidence

- TDD RED: `2 failed, 8 deselected`.
- Focused GREEN: `2 passed, 8 deselected`.
- Production temperature/evidence/provenance matrix: `48 passed`.
- Production matrix including the portable provider regression: `66 passed`.
- Exact SAXS matrix: `653 passed, 6 warnings` in `541.39s`, exit code `0`.
- Structured verifier passed quality `296`, preprocessing `106`, Ruff,
  compile, type baseline, memory/task, and whitespace checks.
- Storage report/clean dry-run found `71` artifacts and
  `16,473,416,178` bytes, with `eligible_bytes=0`, no emergency pressure, and
  `removed=0`. No test-storage apply was run.
- `git diff --check` passed.

## Boundaries

The change does not recalculate method values, interpolate or fabricate
frames, repair source mappings positionally, alter quality levels, physical
gates, rescue, AI, publication roles, the evolution Main Figure, or time-axis
behavior. Static/strain/2D consumers, Workbench presentation, human scientific
review, restarted-GUI review, and full/boundary release gates remain separate.

The explicit allowlist checkpoint is `929da91`; no push or merge was
performed.
