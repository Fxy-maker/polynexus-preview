# SAXS series metric evidence rollup

## Goal

Add a conservative, JSON-safe series-level summary for existing per-frame SAXS
metric evidence in temperature and strain results. Make partial salvage and
missing-frame downgrade explicit to Workbench and Export consumers.

## Non-goals

- No new Porod, Kratky, invariant, lamellar, or Guinier numerical algorithm.
- No new physical threshold, interpolation, frame fabrication, or curve repair.
- No change to static `SAXSResult.metric_evidence`, publication roles, AI
  candidate policy, or tiered-auto behavior.
- No scientific claim that a sequence is quantitatively calibrated; series
  summaries are capped at `Trend`.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/__init__.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- existing SAXS mode/export regression tests
- task/spec/plan and durable memory records

## Acceptance criteria

- [ ] `MetricEvidenceSummary` is immutable, round-trippable, strict JSON-safe,
  and contains counts, coverage, level, applicability, reasons, and source.
- [ ] Complete multi-frame evidence is summarized as `Trend`; all-Quantitative
  series remain capped at `Trend`.
- [ ] Missing, diagnostic, unusable, and invalid-level frames remain visible in
  counts/reason codes and force series `Diagnostic` or `Unusable`.
- [ ] Temperature and strain series attach summaries without changing any
  frame-level evidence, numeric arrays, DataFrame row count, or existing values.
- [ ] Existing Export quality provenance carries series and frame evidence
  read-only, without recomputation or publication-role changes.
- [ ] Task verifier, focused SAXS matrix, and `git diff --check` pass.

## Implementation plan

1. Add failing contract tests for complete, missing, diagnostic, invalid-level,
   and empty series evidence.
2. Implement and export the immutable `MetricEvidenceSummary` contract and
   deterministic builder without changing any frame payload.
3. Attach summaries to temperature and strain series after existing frame
   analysis, preserving all frame values and DataFrame shape.
4. Verify Export carries both series and frame evidence as read-only provenance.
5. Run focused/SAXS/task-scoped verification, record evidence, and checkpoint
   only the explicit changed-file allowlist.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_series_metric_rollup'
python -m pytest tests/test_saxs_series_metric_evidence.py tests/test_saxs_mode_evidence_propagation.py tests/test_saxs_export_bundle.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-series-metric-evidence-rollup.md --changed --types
git diff --check
```

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/__init__.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_series_metric_evidence.py`
- `tests/test_saxs_mode_evidence_propagation.py`
- `tests/test_saxs_export_bundle.py`
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-series-metric-evidence-rollup-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-series-metric-evidence-rollup.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
