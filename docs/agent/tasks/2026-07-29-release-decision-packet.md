---
task_id: 2026-07-29-release-decision-packet
kind: release-readiness
status: awaiting-human-input
date: 2026-07-29
title: Convert remaining release gates into explicit decisions
---

# Release decision packet

## Goal

Turn the remaining non-automatable release gates into explicit, reviewable
decisions with evidence links, while preserving diagnostic-only behavior until
the responsible reviewer confirms the semantics.

## Non-goals

- Do not infer instrument-vendor coordinate conventions, ROI meaning, NMR peak
  assignments, or Joint conflict precedence.
- Do not promote diagnostic or assignment-limited results to publication-ready
  status.
- Do not bypass the locked desktop, alter real datasets, or change release
  state without a human decision.

## Affected boundaries

- Restarted-GUI visual acceptance for the shared Results/Gallery/History/
  Editor/Export routes.
- IR mapping coordinate/ROI semantics and vendor-data acceptance.
- NMR solid-C assignment policy and Xc promotion boundary.
- Joint conflict interpretation and promotion policy.
- Final scientific and release authorization records.

## Implementation plan

1. Inventory the current automated evidence and preserve each limitation as a
   separate release boundary.
2. Define the exact reviewer fields for GUI, IR, NMR, Joint, and final release
   authorization without filling in scientific values.
3. Run the repository boundary and task verifiers to check the packet's
   structure and evidence links.
4. Keep the packet open until the responsible reviewer supplies the missing
   decisions and an unlocked GUI review is recorded.

## Current evidence

- The full software requirement audit maps all named modes and shared
  lifecycle evidence in `docs/agent/tasks/2026-07-29-full-goal-requirements-audit.md`.
- Fresh automated recheck on the current checkout passed the Joint real-data
  and synthetic lifecycle pair: `2 passed in 26.08s`, exit code `0`, using
  `D:\PolyNexus_joint_real_data_audit_20260729` as the external basetemp.
- Fresh cross-technique AI safety recheck passed the AI-off, failed-run, and
  fallback matrix: `25 passed in 0.42s`, exit code `0`, using
  `D:\PolyNexus_ai_safety_audit_20260729` as the external basetemp. Joint is
  intentionally outside the single-technique preprocessing matrix because it
  has report-level AI context rather than an independent preprocessing engine.
- The fresh native route covers 17 cases and 68 captures. A live, unlocked
  canonical `D:\PolyNexus` session was subsequently inspected: Results and
  Result Review were visible, and Plots/History were selected through Windows
  UI Automation. This closes only the observed shell/workbench slice; it does
  not replace the all-mode visual review or scientific decisions below.
- IR mapping now has an official Thermo Scientific OMNIC Picta semantics
  profile: area-map X is the column/Stage-X axis, Y is the row/Stage-Y axis,
  both are stage positions in `um`, the stage-home origin is `(0, 0)`, and
  area-map ROI bounds follow the vendor step-size grid. The current workspace
  still has no vendor-native 2D map or coordinate export, so sample-specific
  ROI bounds, flattened scan order, detector/pixel calibration, and reviewer
  acceptance remain open. See
  `docs/acceptance/2026-07-30-ir-thermo-mapping-semantics.md`.
- NMR solid-C preserves complete labels and explicitly reports
  `assignment_limited`; no assignment truth set has been approved.
- Joint preserves source/run provenance and reports conflicts; no scientific
  conflict precedence has been approved.
- The current Qt window grab additionally showed Results Workbench, the
  manifest-only Plots/Gallery empty state, and populated History controls.
  The OS screenshot helper returned desktop wallpaper rather than the window,
  so this is supplementary visual evidence and not a complete OS-level
  restarted-GUI pass.

## Decision fields

### 1. Restarted GUI

- Reviewer unlocks the canonical `D:\PolyNexus` desktop session.
- Reviewer confirms all required mode routes at normal display size:
  Results, Gallery, History, Editor, and fallback Export.
- Reviewer records visual defects or accepts the route; screenshots alone do
  not constitute scientific approval.

### 2. IR mapping

- Vendor/data source and coordinate convention:
  `______________________________`
- Coordinate order/origin and physical-unit mapping:
  `______________________________`
- ROI inclusion and invalid-pixel policy:
  `______________________________`
- Promotion rule for `ir.mapping.roi` Main/SI/diagnostic roles:
  `______________________________`

### 3. NMR solid-C

- Approved assignment source/truth set:
  `______________________________`
- Label policy for ambiguous or unassigned peaks:
  `______________________________`
- Conditions under which Xc may leave `assignment_limited`:
  `______________________________`

### 4. Joint

- Conflict precedence when technique evidence disagrees:
  `______________________________`
- Required evidence level for a Joint conclusion:
  `______________________________`
- Whether unresolved conflicts remain diagnostic-only:
  `______________________________`

### 5. Final release decision

- Decision: `approve` / `conditional` / `reject`
- Reviewer and date: `______________________________`
- Conditions or follow-up task IDs:
  `______________________________`

## Acceptance criteria

- [x] Every remaining non-automatable gate has a named decision field.
- [x] Existing automated evidence and its limitations are linked without
      relabeling structural evidence as scientific approval.
- [x] An unlocked desktop review is recorded for the canonical DSC shell,
      Results/Result Review, Plots, and History surfaces.
- [ ] IR sample-specific mapping payload, ROI/calibration, and promotion
      semantics are confirmed by the responsible reviewer; the official
      vendor-rule profile itself is documented separately.
- [ ] NMR solid-C assignment policy is confirmed by the responsible reviewer.
- [ ] Joint conflict interpretation is confirmed by the responsible reviewer.
- [ ] Final scientific/release authorization is recorded.

## Verification

```powershell
python scripts/boundary_audit.py --root D:\PolyNexus --json
python scripts/verify.py --task docs/agent/tasks/2026-07-29-release-decision-packet.md --changed --types
git diff --check
```

The boundary audit and task verifier validate repository structure and evidence
consistency only; they cannot satisfy the unchecked human criteria.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-29-release-decision-packet.md`
- `docs/acceptance/2026-07-29-release-decision-packet.md`
- `docs/agent/memory/active-work.md`
