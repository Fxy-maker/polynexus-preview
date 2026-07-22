---
id: 2026-07-22-editor-workflow-convergence
title: Converge the PolyNexus data-to-editor workflow
status: in-progress
scope: architecture, GUI workflow, editor interaction, export, testing
---

## Goal

Deliver the approved complete workflow convergence described in
`docs/superpowers/specs/2026-07-22-editor-workflow-convergence-design.md`.
The result should feel like one product from data selection through figure
delivery, while preserving scientific and document contracts.

## Goal statement

Make the active context, current result, editor capability, run progress,
cancel state, export scope, and recovery path visible and consistent.

## Non-goals

- No scientific algorithm or physical-semantics changes.
- No renderer replacement, new annotation family, or second history system.
- No destructive data/document migration, push, merge, deploy, or external
  messaging.

## Affected boundaries

- `polynexus/gui` MainWindow workspace/navigation/run/results/gallery/editor
  surfaces and their focused services.
- Small GUI/core DTO/service boundaries for context, run state, capability,
  and export intent.
- Regression tests and durable project records.

## Milestones

1. Context safety and stale-result policy.
2. Editor capability header and strong-feedback completion.
3. Shared run stages and cooperative cancellation.
4. Current-run/project export intents and gallery management surface.
5. Diagnostics drawer, responsive shell, and recoverable errors.
6. Boundary cleanup after behavioral acceptance.

Each milestone is an atomic checkpoint with its own focused tests and explicit
changed-file allowlist. No milestone may silently change scientific semantics.

## Implementation plan

1. Introduce the workspace context DTO and stale-result policy, then bind the
   result, gallery, history, and export surfaces to its snapshot.
2. Add the editor capability descriptor and complete the existing strong
   feedback contract across static and generated canvas paths.
3. Add shared run-stage events and cooperative cancellation at safe worker
   boundaries without publishing partial results.
4. Split export intents, add preflight scope/provenance summaries, and make
   gallery management actions selection-activated.
5. Move diagnostics into a collapsible drawer, add narrow-window hierarchy,
   and replace user-action silent failures with recoverable status details.
6. Extract stable view-model/service boundaries after the behavioral matrix is
   green, then record durable memory and milestone evidence.

## Acceptance criteria

- [ ] Switching technique, submodule, source, or history never presents an
  unrelated result as current; context and stale state are visible.
- [ ] Editor mode and capabilities are permanently identifiable for generated,
  static, preview, and compatibility/fallback documents.
- [ ] Static and generated direct-canvas operations provide consistent
  selection, hover, drag, resize, cancel, undo/redo, and export feedback.
- [ ] Ordinary analysis exposes stage, progress where known, and cooperative
  cancellation without publishing partial results.
- [ ] Export clearly distinguishes current-run export from project export and
  shows a preflight scope/provenance summary.
- [ ] Gallery browsing remains simple while secondary batch/compare/revision
  actions appear only when selection makes them meaningful.
- [ ] Logs/diagnostics are collapsible, narrow windows preserve the primary
  task, and user-triggered failures offer copyable diagnostics and recovery.
- [ ] Existing editor, figure, export, Origin, and scientific regression
  suites remain green.

## Verification

Per milestone and final structured check:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-22-editor-workflow-convergence.md --changed --types
python scripts/verify.py --changed --types
```

## Progress checkpoint

- M1 workspace context contract, projection, and context-bound result gating are implemented.
- Focused context matrix: `13 passed` across workspace, navigation, results, run, history, and figure mixins.
- Known limitation: repository-wide `scripts/verify.py --changed --types` still reports pre-existing Ruff findings in the monolithic `main_window.py`; no unrelated cleanup was included.
- M2 editor capability header is implemented for object and static modes; direct selection/drag/cancel/save feedback remains on the existing shared editor session.
- M3 run lifecycle now exposes reading/processing/exporting stages and cooperative cancellation guards; cancelled runs are not published and failures expose retry.
- M4 export scope is split into current-run and project-package intents; gallery secondary actions are selection-activated.
- M5 diagnostics use a collapsible log drawer and the shell hides secondary metrics/actions on narrow windows.

Final desktop acceptance:

```powershell
python scripts/launch_gui.py --diagnose
```

Use the canonical launcher and record the branch/commit identity with the
visual acceptance notes. Do not claim a visual pass from offscreen tests alone.

## Evidence and handoff requirements

- Update this card at every milestone with focused test counts and known
  limitations.
- Update `docs/agent/memory/current-state.md` and `active-work.md` when the
  active boundary or next action changes.
- Preserve pre-existing untracked drafts and diagnostics.
- Create one local checkpoint commit per atomic milestone using the repository
  helper after verification.
