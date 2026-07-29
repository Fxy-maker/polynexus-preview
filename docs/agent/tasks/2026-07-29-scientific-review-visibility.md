# Scientific Review Visibility

## Goal

Make the existing IR mapping, NMR solid-C, and Joint scientific-review decision
visible and consistent in Results Workbench, History, and Export.

## Non-goals

- Do not choose or invent IR coordinates/ROI semantics, NMR assignments/Xc
  policy, Joint precedence, or final release approval.
- Do not alter analysis, evidence generation, figure publication roles, or
  promotion gates.
- Do not delete or migrate test data, modify generated outputs, or touch the
  unrelated SAXS worktree changes.

## Affected boundaries

- Shared GUI presentation adapter for persisted review snapshots.
- Results table model and current-result display routing.
- History table and history export rows.
- Export context and package README provenance.
- Focused unit/regression tests and bilingual labels.

## Acceptance criteria

- [x] The same review snapshot renders the same status/reason in Results
    Workbench, History, and Export.
- [x] Missing review is visibly required for `ir.mapping`, `nmr.solid_c`, and
    `joint`; unrelated modes show not applicable.
- [x] Invalid, pending, conditional, rejected, stale, scope-mismatch, and
    source-mismatch states are never displayed as accepted.
- [x] Export context retains structured review provenance and README text.
- [x] Existing scientific behavior and unrelated working-tree changes are
    unchanged.

## Implementation plan

1. Add a pure adapter for nested review snapshots, status mapping, localization,
   and fail-closed malformed values.
2. Thread the adapter through the ResultsTableModel and current-result summary,
   then add the History column and retranslation headers.
3. Add structured review fields to export context and render the same text in
   the package README.
4. Run focused unit/Qt regressions, task verification, and create an explicit
   allowlist checkpoint while leaving existing SAXS and storage changes alone.

## Verification

```powershell
python -m pytest -q tests/test_scientific_review_presentation.py tests/test_history_table_service.py tests/test_export_context_service.py tests/test_results_table_service.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-scientific-review-visibility.md --changed --types
```

## Explicit file allowlist

- `docs/superpowers/specs/2026-07-29-scientific-review-visibility-design.md`
- `docs/superpowers/plans/2026-07-29-scientific-review-visibility.md`
- `docs/agent/tasks/2026-07-29-scientific-review-visibility.md`
- `polynexus/gui/scientific_review_presentation.py`
- `polynexus/gui/result_table_models.py`
- `polynexus/gui/results_table_service.py`
- `polynexus/gui/main_window_output_mixin.py`
- `polynexus/gui/history_table_service.py`
- `polynexus/gui/main_window_history_mixin.py`
- `polynexus/gui/main_window_retranslate_mixin.py`
- `polynexus/gui/analysis_history_service.py`
- `polynexus/gui/export_context_service.py`
- `polynexus/gui/i18n.py`
- `tests/test_scientific_review_presentation.py`
- `tests/test_history_table_service.py`
- `tests/test_export_context_service.py`
- `tests/test_results_table_service.py`
- `tests/test_main_window_persistence.py`
- `docs/agent/memory/active-work.md`
