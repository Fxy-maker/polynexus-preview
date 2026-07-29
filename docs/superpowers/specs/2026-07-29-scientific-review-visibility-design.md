# Scientific Review Visibility Design

## Goal

Expose the existing scientific-review promotion decision consistently in the
Results Workbench, History, and Export surfaces without changing any scientific
analysis or promotion rule.

## Boundaries

The core review contract remains the source of truth. The GUI consumes the
already-persisted `scientific_review` decision snapshot from an analysis result,
analysis evidence, Joint report, or history record. A missing snapshot is shown
as review required only for `ir.mapping`, `nmr.solid_c`, and `joint`; other modes
show not applicable. Invalid, scope-mismatched, and source-mismatched snapshots
remain visibly non-promotable.

One pure presentation adapter will normalize all supported locations into an
immutable display DTO containing status, reason, scope, record id, source
reference, and localized text. Results Workbench appends the text to its
existing result summary. History adds a dedicated Scientific review column.
Export context includes both the structured DTO and the same display text; the
export README renders the text so an exported package remains auditable.

## Error handling

Malformed values never raise from a GUI display path. They become `invalid` and
retain the raw reason when available. No display fallback may turn a denied
review into an accepted or publication-ready state.

## Verification

Focused tests cover extraction/status mapping, ResultsTableModel routing,
History rows/export, and export README/context. Then run:

```powershell
python -m pytest -q tests/test_scientific_review_presentation.py tests/test_history_table_service.py tests/test_export_context_service.py tests/test_results_table_service.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-scientific-review-visibility.md --changed --types
```
