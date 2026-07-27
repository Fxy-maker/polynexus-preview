# SAXS condition-axis Export/History boundary audit

## Goal

Lock the existing SAXS `metric_evidence[*].condition_axis` provenance across
the two persistence boundaries that were not covered by the Figure/Workbench
tasks: `quality_evidence.json` in the SAXS export bundle and SampleDB History
parameters/results.

## Non-goals

- Do not change SAXS algorithms, physical thresholds, quality levels, or rescue
  behavior.
- Do not interpolate, repair, reorder, or infer condition values.
- Do not change Figure roles, Workbench wording, database schema, or real data.
- Do not promote diagnostic sequence evidence to a physical conclusion.

## Affected boundaries

- `polynexus/core/saxs_export_bundle.py` (audit only unless RED proves a gap)
- `polynexus/gui/analysis_run_service.py` (audit only unless RED proves a gap)
- `tests/test_saxs_export_bundle.py`
- `tests/test_saxs_workbench_series_evidence.py`
- `tests/test_analysis_run_service.py`
- this task card, spec/plan, and durable memory

## Implementation plan

1. Add RED regressions for Export axis provenance and History DTO persistence.
2. Add the smallest `to_dict()`-aware History normalization branch exposed by
   RED; leave the SAXS engine and quality contracts unchanged.
3. Run focused GREEN tests, the complete SAXS matrix, and the structured task
   verifier with an isolated Windows basetemp.
4. Review the exact diff/allowlist, update durable memory, and create one local
   `auto_commit.py` checkpoint.

## Acceptance criteria

- [x] Export preserves the existing series `condition_axis`, including
  position-preserving defects and JSON-safe `null` values.
- [x] History preserves the same axis in both the top-level parameters payload
  and nested results summary without mutating the input.
- [x] If public quality DTO objects reach History directly, the boundary keeps
  their `to_dict()` contract instead of stringifying them.
- [x] No new scientific rule, threshold, interpolation, repair, or AI action
  is introduced.
- [x] TDD RED/GREEN, focused SAXS/History tests, task verifier, diff audit,
  and one explicit allowlist checkpoint are recorded.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_axis_persistence'
python -m pytest tests/test_saxs_export_bundle.py tests/test_saxs_workbench_series_evidence.py tests/test_analysis_run_service.py -q
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-condition-axis-export-history-audit.md --changed --types
git diff --check
```

## Known limitations

This task proves transport/persistence only. It does not provide restarted-GUI
visual review, real-data scientific sign-off, AI calibration, or publication
authorization.

## Verification evidence (2026-07-27)

- TDD RED: `1 failed, 1 passed`; the History DTO case showed that
  `MetricEvidenceSummary` was stringified and its `condition_axis` was lost.
- Focused GREEN Export/History/SAXS Workbench matrix: `29 passed`.
- Complete isolated SAXS matrix returned `362 passed, 4 warnings` in `22.73s`;
  warnings are the existing Arial CJK glyph warnings.
- The only production change is a `to_dict()`-aware branch in the generic
  History JSON normalizer; no engine, quality gate, or database schema changed.
- Structured task verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-condition-axis-export-history-audit.md --changed --types`
  passed task/memory checks, Ruff, compile, type baseline, quality `283`,
  preprocessing `106`, and whitespace.
- `git diff --check` passed before checkpoint review.
- Explicit allowlist checkpoint: `fac9c8d`; no push was performed and no
  parallel GUI/scratch files were included.

## Changed-file allowlist

- `polynexus/gui/analysis_run_service.py`
- `tests/test_saxs_export_bundle.py`
- `tests/test_analysis_run_service.py`
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-condition-axis-export-history-audit-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-condition-axis-export-history-audit.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
