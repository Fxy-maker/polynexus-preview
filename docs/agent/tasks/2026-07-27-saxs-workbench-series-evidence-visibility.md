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

- [x] Temperature and strain `get_parameters()` include the exact existing
  series `metric_evidence` mapping when available.
- [x] Complete multi-frame summaries are displayed as Trend evidence with
  coverage, without being promoted to Quantitative.
- [x] Mixed/missing/diagnostic summaries display their level, counts, and
  reason codes in the Workbench review text.
- [x] Diagnostics still contains the full nested `metric_evidence` payload,
  and frame rows remain unchanged.
- [x] Persisted/history-restored parameters retain the series summary.
- [x] Figure routing and Export provenance tests remain green and unchanged in
  publication role.
- [x] Focused tests, `git diff --check`, and applicable type/quality checks
  have exact recorded results.

## Implementation plan

1. Add failing transport, presentation, model-propagation, and persistence
   tests for complete and downgraded series evidence.
2. Transport the existing temperature/strain series summary through the SAXS
   parameter payload without recalculating or mutating evidence.
3. Format the existing summary in the SAXS Workbench review channels while
   keeping full nested evidence in Diagnostics.
4. Run the Workbench/History/Figure/Export and full SAXS regression matrices.
5. Record exact verification results and create a checkpoint with the
   explicit changed-file allowlist.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_workbench_series_evidence'
python -m pytest tests/test_saxs_series_metric_evidence.py tests/test_saxs_mode_evidence_propagation.py tests/test_saxs_workbench_figure_contracts.py tests/test_results_workbench_profiles.py -q
python -m pytest tests/test_analysis_run_service.py tests/test_history_gallery_restore.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-workbench-series-evidence-visibility.md --changed --types
git diff --check
```

## Verification result

- TDD RED was observed: the initial seven-test slice produced six expected
  failures for missing parameter transport and missing Workbench review text;
  the pre-existing History persistence path already passed its assertion.
- Workbench/History/Figure/Export focused matrix: `24 passed`.
- Complete SAXS matrix: `282 passed, 4 existing font warnings`.
- The task-scoped verifier passed task-card validation, memory validation,
  changed-file Ruff, compile, quality gate `282`, preprocessing gate `106`,
  whitespace, and the final selected-checks status. No changed file was in
  the current Pyright baseline.
- `git diff --check` passed.

The touched legacy SAXS wrapper retains its public imports and single-letter
intensity names; a module-scoped Ruff compatibility annotation covers only
the pre-existing `F401`, `E741`, and `F841` baseline categories.

The post-checkpoint code review reported no Critical or Important findings. A
Minor finding about malformed non-dictionary evidence being dropped was fixed
by preserving every existing evidence value through the transport payload; a
new regression test covers that downgrade-safe behavior.

## Changed-file allowlist

- `polynexus/core/saxs.py`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_workbench_series_evidence.py`
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-workbench-series-evidence-visibility-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-workbench-series-evidence-visibility.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
