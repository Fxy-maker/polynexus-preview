# PolyNexus editor workflow convergence

## Status

Approved by the user on 2026-07-22. This is a structured, multi-milestone
product and architecture task. Implementation is intentionally split into
independently verifiable checkpoints.

## Goal

Make the complete user journey feel like one coherent scientific workspace:

```text
select data -> configure -> run -> judge result -> edit figure -> export
```

The workflow must make context, capability, progress, provenance, and export
scope visible without requiring the user to memorize internal GUI modes.

## User-facing principles

1. **Context before controls.** The active technique, submodule, data source,
   input mode, run id, and result state are always identifiable.
2. **One action, one meaning.** Run, edit, save, compare, and export actions
   describe their actual scope before mutating state.
3. **The canvas is the primary editor surface.** Inspector controls remain
   available, but direct manipulation, feedback, cancellation, undo, and
   export use one visible contract.
4. **No silent stale state.** A result from another run remains recoverable but
   is never presented as the active result.
5. **Failure is recoverable.** User-triggered failures produce a visible
   explanation, a copyable diagnostic, and a safe next action.

## Scope and boundaries

### In scope

- Main-window workspace context and stale-result labeling.
- Unified run stage/status DTOs for single, batch, joint, and AI workflows.
- Safe cancellation boundaries for ordinary analysis where the worker supports
  cooperative cancellation.
- Chart-editor mode/capability presentation and strong direct-canvas feedback.
- Explicit current-run versus project export intents and preflight summaries.
- Chart-gallery management affordances that remain secondary to browsing.
- Collapsible diagnostics/log presentation and narrow-window layout behavior.
- Focused GUI/core services, tests, task evidence, and durable memory updates.

### Out of scope

- Scientific algorithms, physical semantics, or analysis-result schemas.
- Replacing Qt, Matplotlib, or Origin rendering adapters.
- New annotation types or a second editor history system.
- Destructive migration of legacy figure documents on open.
- Editing real regression data, generated outputs, secrets, or runtime files.
- Push, merge, deployment, or external messaging.

## Proposed architecture

### 1. Workspace context

Add a small GUI-facing `WorkspaceContext` value object containing:

- technique and submodule;
- source path and input mode;
- persisted run id and run root;
- result status (`empty`, `running`, `complete`, `failed`, `stale`);
- current result origin and revision metadata.

The MainWindow owns the current context and emits a context-change event. The
results panel, chart gallery, history restore route, and export route consume a
snapshot/DTO instead of reconstructing identity from scattered fields.

Context changes are explicit transitions:

```text
no source -> source selected -> configured -> running
running -> complete | failed | cancelled
complete -> editing | exporting | stale-after-context-switch
```

### 2. Editor mode and capability presentation

Introduce a renderer-neutral editor capability descriptor consumed by
`ChartEditor`. It describes the current source mode, edit authority, save
support, Origin support, provenance quality, and compatibility/fallback notes.

The descriptor is rendered in the editor header and status area. Existing
static, generated, and preview adapters remain in place; this change makes
their differences explicit rather than implicit.

### 3. Run state and cooperative cancellation

Define a shared run-state vocabulary and stage events. Workers report stage,
current item, completed/total when known, and a stable run token. The GUI uses
these events for the progress surface and keeps result publication behind a
single completion boundary.

Cancellation is cooperative: a worker checks a cancellation token at safe
boundaries, emits `cancelled`, and does not publish partial results. Existing
AI tuning cancellation remains compatible with the shared vocabulary.

### 4. Export intents

Split the current ambiguous export action into explicit intents:

- **Current run export:** the active run's report, figures, tables, and
  provenance bundle;
- **Project export:** the existing multi-technique project bundle.

Both routes produce a preflight summary before writing and use the same
provenance/context DTO. Existing file formats remain compatible.

### 5. Editor feedback and shell presentation

Complete the current editor strong-feedback contract: active tool, selection,
hover, body/handle operation, cancellation, layer-tree synchronization, and
export exclusion of transient overlays.

The main shell moves logs and diagnostics into a collapsible bottom drawer.
The header uses a responsive hierarchy: task/context and run state remain
visible; secondary metrics collapse into a details surface at narrow widths.

### 6. Error and localization boundary

Replace user-action silent catches with a small presentation helper that maps
an exception/result to visible status, technical details, and a suggested next
action. Retranslation remains safe for deleted/optional Qt children but should
not hide a whole group of failed updates behind one broad catch.

## Milestone decomposition

### M1 — Context safety

WorkspaceContext, context labels, stale-result policy, history/gallery binding,
and focused context regression tests.

### M2 — Editor capability and feedback

Mode/capability header, strong-feedback completion, static/generated parity,
and export-overlay tests.

### M3 — Run state and cancellation

Shared stage events, ordinary worker cancellation where safe, publication guard,
and single/batch/joint/AI state tests.

### M4 — Export and gallery intent

Current-run/project export split, preflight summary, provenance display, and
selection-activated gallery management actions.

### M5 — Shell decluttering and recoverable errors

Diagnostics drawer, responsive header behavior, empty-state next actions, and
visible/copyable error presentation.

### M6 — Boundary cleanup

Extract stable view-model/services and explicit event contracts only after the
behavioral milestones are green. Remove duplicate implicit state incrementally.

## Error handling

- Invalid or missing context cancels the transition and keeps the last valid
  view with a visible explanation.
- Cancelled runs never replace the last complete result and never claim success.
- Export preflight refuses ambiguous scope and names the missing context.
- Editor capability failures keep the preview usable and state the fallback.
- Localization failures are logged per widget group and surfaced through a
  diagnostic status when user-visible text is incomplete.

## Verification and acceptance

Each milestone must add focused regression coverage and pass:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-22-editor-workflow-convergence.md --changed --types
python scripts/verify.py --changed --types
```

The final acceptance matrix must demonstrate:

- context-safe switching across techniques, submodules, sources, runs, and
  history restore;
- visible editor mode/capability state and consistent direct-canvas feedback;
- stage-aware, cancellable ordinary runs without partial publication;
- explicit export scope and provenance summary;
- usable gallery browsing with secondary management actions;
- collapsible diagnostics, narrow-window layout behavior, and recoverable
  user-action errors;
- existing editor, figure, export, Origin, and scientific regression suites
  remain green.

## Known limitations

- A full desktop visual pass is required after the offscreen test matrices;
  the canonical launcher from `D:\PolyNexus\scripts\launch_gui.py` must be
  used so the inspected process matches the active branch.
- Some workers may require a separate cancellation adapter because their
  underlying scientific library does not expose interruption points.
- Revision comparison remains document/resource based unless a later approved
  task explicitly adds pixel-level diffing.
