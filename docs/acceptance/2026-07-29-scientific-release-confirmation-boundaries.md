# Scientific release confirmation boundaries acceptance

Date: 2026-07-29
Task: `docs/agent/tasks/2026-07-29-scientific-release-confirmation-boundaries.md`

Status: conservative reviewer dispositions recorded; no production behavior
changed.

The approved design preserves the existing typed IR mapping contract,
assignment-limited NMR solid-C evidence, and Joint per-technique provenance.
It defines one auditable reviewer decision record that can travel through
Results Workbench, Figure/Manifest, Gallery, Editor, export, and History.

The fail-closed boundary is explicit: absent, malformed, stale, or
source-mismatched reviewer data cannot promote a result. Current diagnostic,
assignment-limited, and conditional states remain in force.

The project owner confirmed the following conservative dispositions on
2026-07-30:

- IR uses the documented Thermo/OMNIC Picta coordinate profile, but the current
  inputs do not authorize sample-specific ROI, flattening, or detector
  calibration. Mapping remains diagnostic-only.
- NMR solid-C has no approved assignment truth set in the supplied files;
  ambiguous peaks remain unassigned and Xc cannot leave `assignment_limited`.
- Joint grants no automatic scientific priority to one technique; operational
  `ERROR`/`WARN` handling remains fail-closed and unresolved conflicts remain
  diagnostic-only.
- The non-SAXS release decision is `conditional` with source-specific,
  restarted-GUI, and separate SAXS conditions retained.

This acceptance note records the confirmed boundary decisions. It is not a
claim that missing source payloads have been supplied, and it does not mark the
overall software goal complete.
