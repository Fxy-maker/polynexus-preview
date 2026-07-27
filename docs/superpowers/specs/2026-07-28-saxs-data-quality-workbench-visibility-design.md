# SAXS Data-Quality Workbench Visibility Design

**Date:** 2026-07-28
**Status:** approved for implementation in the active SAXS quality goal
**Related task:** `docs/agent/tasks/2026-07-28-saxs-data-quality-workbench-visibility.md`

## Goal

Make existing q/I data-quality evidence visible in the Results Workbench while
keeping the GUI a consumer of emitted DTO/report mappings.

## Contract

Add `_data_quality_review_text(payload, language)` to
`polynexus/gui/saxs_results_table_service.py`. It reads only
`data_quality_report` and `_batch_data[*].data_quality_report` mappings.

For a top-level report, display existing `level`, `source_id`, data refs,
point counts, `reason_codes`, and `actions`. For batch rows, display only
reported-frame coverage, deterministic level counts, and unique emitted reason
codes/actions in source row order. A malformed top-level value is treated as
missing; it cannot promote a batch row into top-level detail. A missing report
is not replaced by a neighbor report and does not generate a pass claim.

The formatter returns the existing `(risk_text, next_text)` shape, uses the
existing `RESULTS_REVIEW_RISK` and `RESULTS_REVIEW_NEXT` message wrappers, and
is composed with metric/axis/Guinier/detector review text. It never mutates the
payload or recomputes report levels.

## Scientific boundary

The review context is provenance and audit visibility, not a new quality
language. A report level, reason, or count remains an emitted observation;
human scientific review and existing physical gates remain authoritative.

## Verification

Tests cover top-level and batch reports, missing reports, deterministic output,
English/Chinese text, and input immutability. Existing Workbench/metric/detector
regressions, exact SAXS tests, and the structured task verifier are required.
