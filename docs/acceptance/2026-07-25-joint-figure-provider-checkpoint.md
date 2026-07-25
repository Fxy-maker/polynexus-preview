# Joint Figure provider checkpoint

## Delivered

The Joint figure boundary now consumes the existing `JointBatchRow` and
`JointRunRecord` data contracts. It emits validated, Manifest-ready logical
IDs:

- `joint.series.crystallinity` — cross-technique Xc comparison (main)
- `joint.series.multiscale` — SAXS long period vs WAXS crystallite size (SI)
- `joint.series.coverage` — available-technique evidence coverage (diagnostic)

`JointCoordinator.publish_figure_definitions()` publishes these definitions
through the shared production pipeline. The Results Workbench profile now
points to the first two logical IDs.

## Verification evidence

- Joint provider, FigureDefinition validation, Manifest publication,
  Coordinator entrypoint, existing Coordinator tests, and Workbench profile:
  12 passed.
- Ruff and `git diff --check`: passed for the changed Joint/profile files.

## Remaining acceptance boundary

- The existing `joint.compare` GUI flow still builds legacy report/BytesIO
  figures and does not yet call the new publication entrypoint.
- Joint evidence/conflict provenance, history linkage, export bundle, fallback,
  AI-off/failure behavior, real data, and restarted-GUI visual review remain
  open.
- This checkpoint is not a complete Joint vertical slice.
