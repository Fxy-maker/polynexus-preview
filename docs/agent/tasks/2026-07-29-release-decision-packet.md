---
task_id: 2026-07-29-release-decision-packet
kind: release-readiness
status: conditionally-accepted
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
4. Keep the packet conditional until the remaining GUI, SAXS, and
   source-specific evidence gates are recorded.

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

- Vendor/data source and coordinate convention: use the official
  `thermo_omnic_picta_official` profile; X is the area-map column/Stage-X axis
  and Y is the row/Stage-Y axis.
- Coordinate order/origin and physical-unit mapping: X/Y are stage positions
  in `um`, with stage-home origin `(0, 0)`; ROI bounds follow the vendor
  step-size grid.
- ROI inclusion and invalid-pixel policy: because no native 2D map, coordinate
  export, sample ROI, or detector calibration is available, do not infer
  sample-specific bounds or calibration; invalid or unverified mapping stays
  review-required.
- Promotion rule for `ir.mapping.roi` Main/SI/diagnostic roles: diagnostic-only
  until a source-matched native map/ROI/calibration record is supplied and
  reviewed.

### 3. NMR solid-C

- Approved assignment source/truth set: none is available in the supplied
  seven JEOL files; the result remains `assignment_limited`.
- Label policy for ambiguous or unassigned peaks: preserve the raw peak and
  axis provenance, but leave the label unassigned/ambiguous; do not infer a
  crystalline or amorphous assignment.
- Conditions under which Xc may leave `assignment_limited`: only an explicit
  source-linked assignment truth set, confirmed/calibrated ppm axis, and a
  subsequent reviewer decision; the current files cannot promote Xc.

### 4. Joint

- Conflict precedence when technique evidence disagrees: no technique is
  granted automatic scientific priority. Operational severity remains
  fail-closed (`ERROR` blocks, `WARN` is conditional), while an unresolved
  scientific conflict remains unresolved.
- Required evidence level for a Joint conclusion: source-linked contributing
  results, valid review provenance, and no unresolved conflict; otherwise the
  result is not a formal Joint conclusion.
- Whether unresolved conflicts remain diagnostic-only: yes.

### 5. Final release decision

- Decision: `conditional`
- Reviewer and date: project owner confirmation in the current task,
  `2026-07-30`
- Conditions or follow-up task IDs: native IR map/ROI/calibration evidence,
  NMR solid-C assignment truth and ppm calibration, conflict-free Joint
  evidence, restarted-GUI all-mode review, and the separate SAXS release
  decision.

## Acceptance criteria

- [x] Every remaining non-automatable gate has a named decision field.
- [x] Existing automated evidence and its limitations are linked without
      relabeling structural evidence as scientific approval.
- [x] An unlocked desktop review is recorded for the canonical DSC shell,
      Results/Result Review, Plots, and History surfaces.
- [x] The reviewer confirmed the conservative IR mapping disposition: use the
      official vendor profile, but keep sample-specific mapping diagnostic-only
      while the native payload is absent.
- [x] The reviewer confirmed the NMR solid-C disposition: keep assignment
      limited and prohibit Xc promotion without an assignment truth set and
      calibrated axis.
- [x] The reviewer confirmed the Joint disposition: no automatic technique
      priority; unresolved conflicts remain diagnostic-only.
- [x] A conditional non-SAXS release decision is recorded; final project
      release remains conditional on the listed GUI, source, and SAXS gates.

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
