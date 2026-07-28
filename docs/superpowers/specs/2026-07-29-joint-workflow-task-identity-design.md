# Joint workflow task identity design

## Decision

When the active technique is `joint`, the Workbench task card should use the
display-only sample identity already present in the in-memory Joint report.
The existing `resolve_joint_history_project_label()` helper remains the single
identity projection rule: one report sample is shown directly, multiple
samples use the translated Joint workspace label, and an empty report keeps
the existing no-data fallback.

## Boundary

This changes only the task-card source text. It does not mutate the Joint
report, persisted project identity, source runs, diagnostics, metrics,
conflict severity, scientific interpretation, or export provenance.

## Verification

The regression exercises the real `MainWindowWorkspaceMixin` method with a
Joint report row and asserts that its source is `PA6-A`; the existing Joint
history, dataset, context, and persistence tests protect the empty, multiple,
and persisted-identity cases.
