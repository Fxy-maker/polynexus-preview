# Origin Editor Phase 2 Unified Framework Design

**Date:** 2026-07-09

## Goal

Build a single editing framework that serves both generated object-mode figures and static background annotation-mode figures without asking the user to understand two different editors.

Phase 2 is not the phase that makes PolyNexus a full Origin replacement. It is the phase that makes the editor feel like one coherent system:

- one object list
- one property panel
- one edit transaction path
- one undo/redo entry point

## Design Summary

Phase 1 fixed the most visible failures:

- generated objects can be selected directly on the canvas
- supported generated-object edits redraw immediately
- static background mode no longer pretends to be a full object editor

Phase 2 now shifts the editor from "partly unified behavior" to "unified editing shell".

The recommended approach is:

1. keep `ChartEditor` as the top-level widget for now
2. extract a shared editing framework above both modes
3. let each mode provide its own object nodes, inspector state, and edit operations
4. route every user edit through one transaction controller

This keeps the delivery experience-first while stopping `ChartEditor` from absorbing more branching logic.

## Scope Boundary

### In scope

- a unified object list for object mode and static background mode
- a unified property panel contract for both modes
- a unified edit-session layer for selection, apply-change, and undo/redo
- `ChartEditor` refactoring to consume the new framework
- focused regression coverage for selection sync, property sync, redraw sync, and undo/redo sync

### Explicitly out of scope for this phase

- full axis inspector
- full legend/font/tick/export-style control surface
- multi-select, lasso, box select, alignment, snapping, or rotation handles
- tree drag-and-drop reordering
- cross-session undo/redo persistence
- imported `PNG/PDF/SVG/JPG` curve extraction
- a full layer/panel system

Phase 2 must improve coherence, not explode scope.

## User Outcomes

After this phase ships, the editor should feel consistent in both modes:

- users select from the same object list pattern whether they are editing generated objects or static annotations
- the right-side property panel always responds through the same interaction model
- property edits and geometry edits follow one commit path and one undo/redo path
- unsupported capabilities in static background mode are shown as clear boundaries, not as broken affordances
- generated-object editing and annotation editing stop feeling like two stitched-together tools

## Current Structural Problems

### 1. The object list is still a local projection, not a real editor component

`ChartEditor._refresh_object_list()` currently rebuilds a `QListWidget` by mixing:

- a synthetic background row
- generated figure objects
- annotation rows from `AnnotationCanvas`

Selection and visibility behavior are then reconstructed through `Qt.UserRole` and role branching. This works, but it means the list is still owned by widget-local logic instead of by a stable editor model.

### 2. Property controls are double-driven

`ChartEditor` currently has two separate sync paths:

- `_sync_generated_object_property_controls()`
- `_sync_annotation_property_controls()`

They update the same visible controls through different rule sets. This makes stale values, enable-state drift, and edit-path duplication increasingly likely as more object types are added.

### 3. Undo/redo is split by mode

`AnnotationCanvas` already owns its own undo/redo stacks for static annotations. Generated-object editing does not have an equivalent history owner; it relies on direct mutations, recent-delete recovery, and drag-time snapshots.

If this split remains, Phase 2 will produce a UI that looks unified while still behaving as two different editors underneath.

## Recommended Architecture

Phase 2 introduces a shared editing shell with three new framework units:

1. `FigureObjectTree`
2. `FigurePropertyPanel`
3. `FigureEditSession`

Two mode adapters sit beneath that shell:

- `GeneratedFigureEditingAdapter`
- `StaticBackgroundEditingAdapter`

`ChartEditor` remains the host widget, but it stops owning list synthesis, property binding rules, and edit-history branching directly.

## Component Design

### 1. `FigureObjectTree`

`FigureObjectTree` is the unified object browser. Even if its first visual version still looks list-like, it must internally work from stable node data instead of ad hoc widget reconstruction rules.

Its responsibilities are:

- render the current mode's object-node structure
- keep current selection in sync with canvas and property panel
- expose visibility toggles and basic object actions
- remain agnostic to whether a node came from generated-object mode or annotation mode

It must not directly mutate documents or annotation state.

### 2. `FigurePropertyPanel`

`FigurePropertyPanel` is the unified inspector shell. It owns how fields are shown, grouped, and committed, but it does not decide what a given node means.

Its responsibilities are:

- render an `InspectorState`
- keep a stable visual structure across object types
- emit normalized property-change requests
- enter a clear empty or read-only state when the current node has no editable properties

The first version should keep a fixed mental model for the user:

- `Identity`
- `Geometry`
- `Style`
- `Actions`

It should not become a fully generic, infinitely dynamic form engine in this phase.

### 3. `FigureEditSession`

`FigureEditSession` is the single owner of edit transactions and history. Every user edit must enter through this layer regardless of source.

Its responsibilities are:

- accept normalized edit requests
- apply changes through the active mode adapter
- decide whether a change is preview-only or commit-worthy
- own undo/redo stacks
- restore selection, list state, and inspector state after undo/redo

There must be one history owner for the whole editor shell.

### 4. Mode Adapters

The adapters provide the mode-specific implementation behind the shared shell.

`GeneratedFigureEditingAdapter` is responsible for:

- object nodes for generated figure objects
- generated-object inspector state
- generated-object mutation through `FigureObjectStore`
- generated-object redraw and persistence

`StaticBackgroundEditingAdapter` is responsible for:

- background and annotation nodes
- annotation/background inspector state
- annotation mutations through `AnnotationCanvas` and backing state
- static preview refresh and persistence

Adapters translate between shared UI contracts and mode-specific state. They are allowed to know mode details; the shared shell is not.

## Shared Contracts

### Object node contract

The object tree should consume a stable node shape such as:

```python
{
    "node_id": "generated:series-a",
    "node_kind": "figure_object",
    "label": "Plot Series: I(q)",
    "visible": True,
    "checkable": True,
    "selectable": True,
    "capabilities": {
        "rename": True,
        "delete": True,
        "reorder": True,
        "geometry": False,
    },
    "parent_id": "group:generated-objects",
}
```

Required properties:

- `node_id`
- `node_kind`
- `label`
- `visible`
- `checkable`
- `selectable`
- `capabilities`

Recommended namespaced node ids:

- `generated:<object_id>`
- `annotation:<annotation_id>`
- `background:source`
- `group:<group_id>`

This prevents collisions and makes the shell independent of mode-specific raw ids.

### Inspector contract

The property panel should consume a stable `InspectorState` shape such as:

```python
{
    "node_id": "annotation:ann-123",
    "title": "Text Annotation",
    "subtitle": "Static Background Mode",
    "mode_badge": "static",
    "sections": [
        {
            "id": "identity",
            "title": "Identity",
            "fields": [
                {"id": "text", "kind": "text", "label": "Text", "value": "Rg = 12.4 nm", "enabled": True},
            ],
        },
        {
            "id": "style",
            "title": "Style",
            "fields": [
                {"id": "color", "kind": "color", "label": "Color", "value": "#111111", "enabled": True},
                {"id": "font_size", "kind": "number", "label": "Font Size", "value": 12, "enabled": True},
            ],
        },
    ],
    "actions": [
        {"id": "delete", "label": "Delete", "enabled": True},
    ],
    "empty_message": "",
}
```

Field kinds should stay intentionally small in this phase:

- `text`
- `number`
- `select`
- `color`
- `toggle`
- `readonly`

The first shared field vocabulary should be limited to high-value editor fields:

- `name`
- `text`
- `visible`
- `x`, `y`, `w`, `h`
- `x1`, `y1`, `x2`, `y2`
- `color`
- `line_width`
- `alpha`
- `line_style`
- `marker`
- `marker_size`
- `font_size`

### Edit command contract

The edit session should normalize committed edits into a lightweight command shape such as:

```python
{
    "command_id": "rename-generated-series-a",
    "label": "Rename Object",
    "node_id": "generated:series-a",
    "selection_after": "generated:series-a",
    "merge_key": "generated:series-a:name",
}
```

Commands must support:

- `apply()`
- `revert()`
- optional merge/coalesce behavior for repeated edits

The goal is reliable, user-visible history behavior, not a maximal framework.

## Interaction Flows

### Selection flow

1. user clicks on canvas or object tree
2. active adapter resolves that interaction to a `node_id`
3. `FigureEditSession` updates the current selection
4. `FigureObjectTree` highlights the selected node
5. `FigurePropertyPanel` renders the returned `InspectorState`
6. canvas highlight and status text refresh from the same selected node

There must be one selected-node identity shared by list, canvas, and inspector.

### Property-edit flow

1. user edits a field in `FigurePropertyPanel`
2. panel emits `property_change_requested(node_id, field_id, value, commit_mode)`
3. `FigureEditSession` asks the active adapter to validate and apply
4. adapter mutates backing state and triggers redraw
5. session decides whether to record history
6. tree, canvas, and inspector refresh from the new state

### Visibility-toggle flow

1. user toggles visibility in `FigureObjectTree`
2. tree emits `visibility_change_requested(node_id, visible)`
3. session routes it through the active adapter
4. adapter applies the visibility change and redraws
5. session records one undoable command

### Geometry-edit flow

Geometry edits must separate preview from commit:

- dragging shows immediate visual feedback
- mouse release records one undoable command
- repeated numeric stepping may be coalesced into one command

This preserves WYSIWYG without turning undo into a stream of tiny steps.

## Undo/Redo Baseline

Phase 2 must establish one history entry point for both modes.

The first covered undoable operations should be:

- rename
- style patch
- geometry patch
- visibility toggle
- delete / restore
- reorder
- annotation create / paste

Not required yet:

- history branches
- persistent history across sessions
- per-keystroke history granularity
- multi-object transactional editing

Acceptance for undo/redo:

- `Ctrl+Z` and `Ctrl+Y` enter through one editor history owner
- object mode and static mode both participate
- undo restores tree selection, canvas view, and inspector state together
- drag operations undo as one semantic step

## ChartEditor Refactoring Boundary

`ChartEditor` should remain responsible for:

- top-level layout
- mode detection and adapter selection
- file open/save entry points
- toolbar wiring

`ChartEditor` should stop owning directly:

- object-tree data construction
- per-mode inspector population logic
- per-mode history branching
- direct edit-path branching for list versus canvas versus panel

Phase 2 is successful only if `ChartEditor` becomes a host, not the place where new edit-state complexity accumulates.

## Delivery Strategy

Ship in four batches:

1. `Batch A`: shared node model plus `FigureObjectTree`
2. `Batch B`: shared `InspectorState` plus `FigurePropertyPanel`
3. `Batch C`: `FigureEditSession` plus undo/redo baseline
4. `Batch D`: `ChartEditor` slimming, sync cleanup, and regression coverage

This order maximizes user-facing coherence early while keeping the architecture track moving in the same direction.

## Acceptance Criteria

Phase 2 is complete when all of the following are true:

- one object tree can stably display generated objects, background, and annotations through the same node contract
- switching between nodes never leaves stale values or invalid controls in the property panel
- property edits and geometry edits both use the same commit path and trigger immediate redraw
- undo/redo works through one shared entry point in both modes
- `ChartEditor` no longer grows with new `if generated else annotation` editing branches for the covered Phase 2 scope

## Risks And Controls

### Risk: the new framework becomes too abstract too early

Control:

- keep contracts small and concrete
- limit field kinds
- avoid building a fully generic form engine in Phase 2

### Risk: visual consistency improves, but state ownership stays split

Control:

- require `FigureEditSession` to own history
- require adapters to be the only mutation path beneath the shared shell

### Risk: Phase 2 scope expands into full Origin parity

Control:

- lock axis/legend/font/tick/export-depth features out of this phase
- treat them as later capabilities that will sit on the same framework

### Risk: ChartEditor remains the hidden owner of everything

Control:

- reject new editor behaviors that bypass the object tree, property panel, or edit session
- move new edit logic into adapters or framework units only

## Next Step

The next step after this spec is a detailed implementation plan for the first approved Phase 2 batch:

- unified object tree
- unified property panel
- unified edit session with undo/redo baseline

That plan should decompose the work so an implementation agent can execute it without rediscovering the architecture decisions above.
