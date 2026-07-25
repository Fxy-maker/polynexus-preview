# Joint Figure provider checkpoint

## Delivered

The Joint figure boundary now consumes the existing `JointBatchRow` and
`JointRunRecord` data contracts. It emits validated, Manifest-ready logical
IDs:

- `joint.series.crystallinity` — cross-technique Xc comparison (main)
- `joint.series.multiscale` — SAXS long period vs WAXS crystallite size (SI)
- `joint.series.coverage` — available-technique evidence coverage (diagnostic)

`JointCoordinator.publish_figure_definitions()` publishes these definitions
through the shared production pipeline. `JointCoordinator.publish_hub_report()`
attaches the Manifest run context to the report, and the GUI
`JointHubWorker` now calls that service so a real `joint.compare` run produces
the same Manifest-backed entries. The Results Workbench profile points to the
first two logical IDs.

## Verification evidence

- Joint provider, FigureDefinition validation, Manifest publication,
  Coordinator entrypoint, existing Coordinator tests, and Workbench profile:
  12 passed.
- Ruff and `git diff --check`: passed for the changed Joint/profile files.

## Remaining acceptance boundary

- The GUI still retains legacy BytesIO/PNG compatibility artifacts alongside
  the new Manifest run; the normal Gallery path should use the Manifest.
- MainWindow-level Gallery/Workbench visual routing, history linkage, and
  export-bundle inspection still need an end-to-end GUI regression.
- Joint evidence/conflict provenance, history linkage, export bundle, fallback,
  AI-off/failure behavior, real data, and restarted-GUI visual review remain
  open.
- This checkpoint is not a complete Joint vertical slice.

## MainWindow integration follow-up (2026-07-25)

- Joint completion now persists the report through the shared analysis-run
  history path after the worker publishes its Manifest context.
- History restore now rehydrates the persisted Joint report into the Joint
  workspace and custom Workbench profile instead of treating it as a generic
  parameter table.
- Joint reports now use the custom `joint` Results Workbench presentation,
  including typed primary/detail/diagnostic sections, summary metrics, and
  figure links for `joint.series.crystallinity` and
  `joint.series.multiscale`.
- Export bundles now preserve `runs/<run_id>/` under `metadata/runs/`, so the
  Figure Manifest remains available beside copied figures and data.
- Focused MainWindow, Workbench, worker, export-context, and contract matrix:
  37 passed. Structured verifier, quality gate (282 passed), and preprocessing
  gate (103 passed) also passed.

Remaining: Joint scientific conflict/provenance review, AI-off/failure and
fallback behavior, real-data and restarted-GUI visual acceptance, and release
boundary review. The legacy PNG/CSV compatibility path is intentionally kept.
