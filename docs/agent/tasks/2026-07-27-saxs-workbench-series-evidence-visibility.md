# SAXS Workbench series evidence visibility

## Goal

Expose existing temperature/strain series `metric_evidence` in the Results
Workbench review path so partial salvage and diagnostic-only frames are
visible without changing scientific calculations or publication roles.

## Non-goals

- No new SAXS numerical method, physical threshold, interpolation, or frame
  repair.
- No changes to static frame evidence, figure definitions, manifest IDs,
  Export quality provenance, AI execution policy, or tiered-auto behavior.
- No cleanup of the pre-existing GUI Ruff error or unrelated workspace files.

## Affected boundaries

- `polynexus/core/saxs.py`: transport existing series summaries in the
  temperature/strain parameter payload.
- `polynexus/gui/saxs_results_table_service.py`: localized presentation-only
  summary from existing contract fields.
- `polynexus/gui/results_table_service.py` and
  `polynexus/gui/result_table_models.py` are inspected but remain unchanged
  unless a focused test proves the existing model contract cannot propagate
  the presentation text.
- focused SAXS result/history tests.
- this task card, the design/spec, implementation plan, and durable memory.

## Acceptance criteria

- [ ] Temperature and strain `get_parameters()` include the exact existing
  series `metric_evidence` mapping when available.
- [ ] Complete multi-frame summaries are displayed as Trend evidence with
  coverage, without being promoted to Quantitative.
- [ ] Mixed/missing/diagnostic summaries display their level, counts, and
  reason codes in the Workbench review text.
- [ ] Diagnostics still contains the full nested `metric_evidence` payload,
  and frame rows remain unchanged.
- [ ] Persisted/history-restored parameters retain the series summary.
- [ ] Figure routing and Export provenance tests remain green and unchanged in
  publication role.
- [ ] Focused tests, `git diff --check`, and applicable type/quality checks
  have exact recorded results.

## Verification commands

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_workbench_series_evidence'
python -m pytest tests/test_saxs_series_metric_evidence.py tests/test_saxs_mode_evidence_propagation.py tests/test_saxs_workbench_figure_contracts.py tests/test_results_workbench_profiles.py -q
python -m pytest tests/test_analysis_run_service.py tests/test_history_gallery_restore.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-workbench-series-evidence-visibility.md --changed --types
git diff --check
```

## Changed-file allowlist

- `polynexus/core/saxs.py`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_workbench_series_evidence.py`
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-workbench-series-evidence-visibility-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-workbench-series-evidence-visibility.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
