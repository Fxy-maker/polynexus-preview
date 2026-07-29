# Scientific release confirmation boundaries acceptance

Date: 2026-07-29
Task: `docs/agent/tasks/2026-07-29-scientific-release-confirmation-boundaries.md`

Status: design recorded; reviewer values not supplied; no production behavior
changed.

The approved design preserves the existing typed IR mapping contract,
assignment-limited NMR solid-C evidence, and Joint per-technique provenance.
It defines one auditable reviewer decision record that can travel through
Results Workbench, Figure/Manifest, Gallery, Editor, export, and History.

The fail-closed boundary is explicit: absent, malformed, stale, or
source-mismatched reviewer data cannot promote a result. Current diagnostic,
assignment-limited, and conditional states remain in force.

The remaining user-owned inputs are:

1. IR vendor coordinate convention, ROI inclusion, invalid-pixel handling, and
   Main/SI/diagnostic promotion rule.
2. NMR solid-C assignment source, ambiguity labels, and Xc promotion
   conditions.
3. Joint conflict precedence, minimum evidence class, and unresolved-conflict
   conclusion rule.
4. Final release decision, reviewer identity/date, and conditional follow-ups.

This acceptance note records the design boundary only. It is not scientific
sign-off and does not mark the overall software goal complete.
