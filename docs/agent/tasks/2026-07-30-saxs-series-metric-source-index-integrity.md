---
task_id: 2026-07-30-saxs-series-metric-source-index-integrity
kind: scientific-cross-module
status: completed
date: 2026-07-30
title: Add source-index integrity to SAXS series metric evidence
---

# SAXS series metric source-index integrity

## Goal

Make series-level Porod, Kratky, invariant, and lamellar evidence explicitly
fail closed when the supplied frame identity mapping is invalid, reusing the
conservative boundary already established for temperature Guinier evidence.

## Non-goals

- No q/I, Porod, Kratky, invariant, or lamellar recalculation.
- No sorting, interpolation, frame fabrication, source-index repair, new
  physical threshold, AI call, automatic rescue, or publication-role change.
- No changes to condition-axis validation or to Static/Strain behavior when no
  source mapping is supplied.
- No GUI, real-data, generated-output, test-storage, or `current-state.md`
  changes.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`: immutable summary
  fields and source-index validation.
- `tests/test_saxs_series_metric_source_integrity.py`: focused regression
  coverage.
- Existing `MetricEvidenceSummary` JSON and series consumers through the same
  public contract.

## Acceptance criteria

- [x] Valid reordered indices are preserved, explicitly marked, and do not
      lower the existing metric summary level.
- [x] Duplicate, invalid, and length-mismatched mappings expose position facts,
      trusted indices are empty, and usable summaries are `Diagnostic`.
- [x] Omitted mappings remain unchanged and do not create source-index reasons.
- [x] New payloads are strict JSON-safe and round-trip through
      `MetricEvidenceSummary.from_dict()`.
- [x] TDD RED/GREEN, task verification, SAXS matrix, storage dry-run, diff,
      and allowlist checkpoint evidence are recorded.

## Implementation plan

1. Add focused source-index RED tests.
2. Extend the immutable summary contract and aggregation boundary minimally.
3. Run focused GREEN, existing series regressions, task-scoped verification,
   SAXS matrix, diff, and storage dry-run.
4. Update acceptance/memory and create one explicit allowlist checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_saxs_series_metric_source_integrity.py -o addopts= --basetemp=D:\PolyNexus_saxs_series_metric_source_integrity_red
python -m pytest -q tests/test_saxs_series_metric_source_integrity.py tests/test_saxs_series_metric_evidence.py -o addopts= --basetemp=D:\PolyNexus_saxs_series_metric_source_integrity_green
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-series-metric-source-index-integrity.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix is counted as passed only with a complete pytest summary
and exit code `0`. Full/boundary output is reported only when it completes with
both a pytest summary and boundary result. `test_storage.py --apply` is not
part of this task.

## Evidence

- Initial TDD RED: `8 failed, 2 warnings`; failures were the expected missing
  fields, missing reason codes, and missing source-index downgrade.
- Boundary RED after adding non-finite/non-coercible values: `1 failed, 6
  passed, 4 deselected, 2 warnings`; `inf` reproduced the old conversion
  crash before the implementation was corrected.
- Focused GREEN: `21 passed, 1 warning`.
- Consumer matrix covering series, method, Figure, Export, Temperature, and
  Strain evidence: `110 passed, 1 warning`.
- Fresh SAXS matrix with offscreen Qt: `605 passed, 8 warnings in 424.90s`,
  exit code `0`.
- Task verifier completed task-card, memory, Ruff, compile, and type-baseline
  checks. Its focused quality gate returned `288 passed, 2 failed, 3
  warnings`, exit code `1`; both failures are pre-existing locale expectation
  mismatches in `tests/test_history_table_service.py` (`Scientific review` is
  expected while the current locale emits `科学复核`). This limitation is
  unrelated to the SAXS source-index change.
- `git diff --check` passed. Storage report/clean remained dry-run only:
  `54` artifacts, `eligible_bytes=13390550`, `eligible=6`, `removed=0`.
  `test_storage.py --apply` was not run.

## Known limitations

The task-scoped quality gate is not green because of the pre-existing history
locale assertions above. The broader full/boundary gate is not claimed for
this atomic task; its prior current-head Qt crash/abort remains documented in
the separate verification recheck. Human scientific and release review remain
unchanged.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `tests/test_saxs_series_metric_source_integrity.py`
- `docs/superpowers/specs/2026-07-30-saxs-series-metric-source-index-integrity-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-series-metric-source-index-integrity.md`
- `docs/agent/tasks/2026-07-30-saxs-series-metric-source-index-integrity.md`
- `docs/acceptance/2026-07-30-saxs-series-metric-source-index-integrity.md`
- `docs/agent/memory/active-work.md`
