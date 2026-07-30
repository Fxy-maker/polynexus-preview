# Joint AI Boundary

## Goal

Make the Joint report's deterministic AI-off/fallback boundary explicit in the
existing `ai_context` payload while preserving source evidence and diagnostic
conflicts.

## Non-goals

- No AI provider call or prompt construction.
- No change to Joint formulas, conflict thresholds, evidence weights, or
  scientific review decisions.
- No conversion of warnings/errors into accepted conclusions.

## Affected boundaries

- `polynexus/core/joint/dataset.py`: attach a JSON-safe execution boundary to
  the report-level AI context.
- `tests/test_joint_hub_dataset.py`: assert the boundary for both clean and
  conflicted reports.
- Docs: record the deterministic fallback policy and verification evidence.

## Acceptance criteria

- [x] Every Joint report declares AI mode `off`, provider status `not_configured`,
  and deterministic fallback `rule_based_report`.
- [x] The report declares that provider failure preserves source evidence and
  diagnostic conflict status.
- [x] Existing Joint real-data, conflict, lifecycle, and provenance tests stay
  green.

## Implementation plan

1. Add a failing report assertion for the explicit AI boundary.
2. Add the smallest static boundary payload to `_build_joint_ai_context()`.
3. Run focused Joint tests, real-data lifecycle, structured verification, and
   create one explicit allowlist checkpoint.

## Verification

```powershell
$env:POLYNEXUS_TEST_RETENTION='review'; python -m pytest tests/test_joint_hub_dataset.py tests/test_joint_real_data_lifecycle.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-30-joint-ai-boundary.md --changed --types
```

Focused result: `9 passed in 17.12s`, exit code `0`; the broader Joint conflict,
lifecycle, figure, coordinator, analysis-hub, and NMR provenance matrix passed
`27 passed in 28.92s`, exit code `0`. Structured verification passed with
quality `290` and preprocessing `106`, exit code `0`. An earlier ephemeral
rerun reached `2 passed` in the test body but exited with `WinError 32` while
pytest tried to remove a SQLite file; the review-retention rerun avoided that
tool-level cleanup failure.

## Explicit changed-file allowlist

- `polynexus/core/joint/dataset.py`
- `tests/test_joint_hub_dataset.py`
- `docs/agent/tasks/2026-07-30-joint-ai-boundary.md`
- `docs/superpowers/specs/2026-07-30-joint-ai-boundary-design.md`
- `docs/superpowers/plans/2026-07-30-joint-ai-boundary.md`
- `docs/acceptance/2026-07-30-joint-ai-boundary.md`
- `docs/agent/memory/active-work.md`
