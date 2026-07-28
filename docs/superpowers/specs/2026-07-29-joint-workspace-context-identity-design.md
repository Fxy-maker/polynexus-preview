# Joint workspace context identity design

## Decision

The compact workspace context line uses the same existing display-only Joint
identity resolver as the task card when the active context is `joint`. A
single report sample is shown directly; empty or multi-sample behavior remains
the resolver's existing behavior.

## Boundary

Only the Workbench context text changes. The immutable `WorkspaceContext`,
Joint report, persisted project identity, run provenance, diagnostics, and
scientific results are not modified.

## Verification

A focused regression builds a Joint workspace context with a `PA6-A` report
row and asserts that the rendered summary contains `PA6-A` and not the no-data
placeholder. The native Joint route is then rerun to inspect the real header.
