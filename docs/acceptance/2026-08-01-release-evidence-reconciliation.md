# Current Release Evidence Reconciliation

Task: `docs/agent/tasks/2026-08-01-release-evidence-reconciliation.md`

## Current disposition

The engineering verification gate is current and passing, but the overall
PolyNexus release remains **conditional**. Automated coverage is not scientific
approval or owner release authorization.

## Current engineering evidence

- Formal current-head wrapper:
  `python scripts/verify.py --changed --types --full --boundary` completed
  with exit code `0`.
- Complete pytest summary: `3303 passed, 18 skipped, 12 warnings in 2244.54s
  (0:37:24)`.
- Focused quality gate: `297 passed`; preprocessing gate: `106 passed`.
- Boundary audit: exit code `0`.
- SAXS 2D bridge checkpoint: `edad9a9`; latest focused bridge regression:
  `26 passed`; latest complete SAXS matrix: `710 passed, 6 warnings in
  486.47s`.
- Storage report and clean were dry-run only: `142` artifacts,
  `15,743,185,346` eligible bytes, and `0` removed. No `--apply` was run.

## Scientific and release gates

- IR mapping is still `review_required` and diagnostic-only. The official
  vendor profile documents the axis convention, but sample-matched native
  coordinate/ROI/flattening/calibration evidence is absent.
- NMR solid-C is still assignment-limited. No approved assignment truth set or
  calibrated ppm axis is available, so Xc promotion remains prohibited.
- Joint unresolved scientific conflicts remain diagnostic-only. Operational
  severity does not assign scientific technique priority.
- Restarted normal-size GUI walkthrough and final owner scientific/release
  authorization remain open.

## Historical evidence handling

The earlier full/boundary `124` timeout with no pytest summary and child
manifest exit `3` is retained in its original task as historical incomplete
evidence. It is neither counted as a current product failure nor used in place
of the current complete exit-`0` result.

## Sources

- `docs/agent/tasks/2026-07-31-formal-pytest-temp-collection-boundary.md`
- `docs/agent/tasks/2026-07-31-saxs-2d-ai-context-bridge.md`
- `docs/agent/tasks/2026-07-31-full-goal-release-evidence-audit.md`
- `docs/agent/tasks/2026-07-29-release-decision-packet.md`

## Current-head amendment

The Joint `SKIP`/`INFO` compatibility update was verified on the current HEAD.
The authoritative full/boundary result is `3352 passed, 18 skipped, 12
warnings in 2157.07s (0:35:57)`, exit code `0`, with quality `297`,
preprocessing `106`, boundary audit exit `0`, and all structural checks passed.

An earlier rerun with two stale v4 severity assertions returned `3350 passed,
18 skipped, 12 warnings`, exit code `1`; after the assertion update it is
classified as a repaired compatibility failure, not as a current product
failure. This does not close the scientific or owner release gates listed
above.
