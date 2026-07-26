# Joint lifecycle closure design

## Goal

Prove that a Joint hub publication remains one traceable figure run across the
active Gallery, ChartEditor working/published revisions, export provenance,
and History restore.

## Boundaries

The test consumes the existing `JointCoordinator.publish_hub_report()`,
`RunFigureManifest`, `FigureProjectService`, export-context helpers, and
`MainWindow._restore_history_record()`. It does not introduce a new Joint
calculation, tolerance, database schema, or GUI route.

## Data flow

`JointBatchRow` records are published once with a fixed run ID. The manifest
must expose crystallinity (main), multiscale (SI), and evidence coverage
(diagnostic) entries. The main document is saved and published through the
existing project service. Export copies the run manifest and active-run pointer
under `metadata/`. History restore receives the same output root and must
rehydrate the custom Joint Workbench and the same three Gallery entries.

## Safety and acceptance

- Run IDs and figure IDs are asserted at every boundary.
- Diagnostic coverage remains diagnostic; it is never promoted to Main.
- Only pytest temporary directories are written.
- Scientific conflict provenance and assignment/low-confidence semantics stay
  in their existing contracts.
- AI preprocessing is not attached to Joint: Joint is report-level review and
  is explicitly outside the single-technique preprocessing matrix.
