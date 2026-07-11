# Origin Editor Classified Gallery And Strict Entry Consistency Design

**Date:** 2026-07-10

## Goal

Simplify the PolyNexus result-gallery flow so every discovered figure appears in one gallery, grouped by clear categories, while preserving the existing Origin-style editor semantics and enforcing strict preview-to-editor consistency.

This design specifically defines:

- one gallery instead of summary/per-frame drill-down
- category-based figure organization
- figure-first card identity on top of existing export assets
- strict rules that guarantee the figure opened in `ChartEditor` matches the figure shown in the gallery
- safe downgrade rules from `object` editing to `static_background` editing when strict consistency cannot yet be guaranteed

This design does not replace the current editor core, renderer architecture, or the broader Phase 2 unified editor framework. It narrows the product surface so the current system behaves predictably.

## Why This Design Is Needed

The current product state has two user-facing failures at the same time.

First, the result gallery hides valid figures because the main window currently prefers the current result manifest over a complete `polynexus_output` scan. For temperature SAXS, that can collapse a multi-figure result set into a single root-level overview export even when multiple summary figures and per-frame figures already exist on disk.

Second, entering the editor does not always preserve figure identity or figure layout. A user can see one logical figure in the gallery, enter the editor, and then encounter either:

- a different figure
- the correct figure id but the wrong reconstructed layout
- a composite figure flattened into a single-axes rendering that no longer matches the preview

Those two failures are worse than a missing feature. They directly break trust:

- "Where did the other figures go?"
- "Why is the editor showing a different chart from the one I clicked?"

The system must first become predictable before it becomes more capable.

## User Outcomes

After this redesign:

- the user sees one gallery for the whole analysis result
- summary figures, per-frame figures, and fallback exports all remain visible
- the user can filter by category instead of navigating another hierarchy
- each card still represents one logical figure, not one raw file
- clicking a figure card never opens the wrong figure
- entering the editor never changes the figure layout unexpectedly
- figures that cannot yet satisfy strict object-mode consistency still remain accessible through static-background editing instead of pretending to support full object editing

## Scope Boundary

### In scope

- main result-gallery discovery rules
- gallery categories and category ordering
- figure-entry metadata required for strict editor entry
- editor-entry routing and consistency checks
- safe mode downgrade rules
- focused regression coverage for figure discovery, grouping, entry routing, and downgrade behavior

### Explicitly out of scope

- redesigning the entire result page
- replacing the current `ChartEditor` renderer
- full multi-panel object-mode editing support
- export preflight or batch re-export workflows
- richer asset-management workflows beyond the existing secondary asset panel
- deep repair of legacy figure-document relationships

This design is about predictable entry behavior, not full Origin parity.

## Design Principles

### 1. One gallery, not two navigation systems

Users should not have to understand summary versus per-frame navigation depth. All discovered figures should live in one gallery surface.

### 2. Figure-first identity still wins

Even when all figures share one gallery, each card still represents one logical figure. Exported files remain assets of that figure, not peer gallery items.

### 3. Strict consistency beats optimistic edit capability

If the system cannot prove that the editor will open the same figure with the same visible layout, it must not promise object-mode editing.

### 4. Simpler categorization beats clever hierarchy

The gallery should avoid nested trees, drill-down flows, and special-case navigation rules. A small category model is easier to understand and easier to keep stable.

### 5. Fallback is acceptable, false promise is not

Opening a figure in static-background mode is acceptable when object-mode parity is not yet ready. Opening the wrong figure in object mode is not acceptable.

## Current Failure Mode

### Failure 1: Result manifest can hide valid figures

The current main-window path uses current-result figure paths as a preferred source. When those preferred paths are non-empty, complete gallery discovery is short-circuited. In temperature SAXS this can surface only one root-level overview figure even though:

- `summary/` contains multiple logical series figures
- `per_frame/` contains many frame-level figures

### Failure 2: Editor entry is too path-driven

The editor is still frequently opened from a resolved path rather than a stable figure-entry contract. That makes it too easy to:

- pick the wrong sibling asset
- pick the wrong figure document
- treat a preview asset as if it were the editing truth

### Failure 3: Object-mode rendering over-promises on composite figures

Some figures have a valid object-mode document but cannot yet be reconstructed with layout fidelity inside the current object-mode editor shell. Composite overview figures are the clearest example. In those cases, `mode == object` is not enough to justify an `Object Editing` promise.

## Considered Approaches

### Option A: Keep current gallery flow and only widen the manifest

Pros:

- smallest implementation diff
- can surface more figures quickly

Cons:

- still path-first at the editor boundary
- does not solve preview-to-editor mismatch
- does not create a durable category model

### Option B: Full drill-down navigation between summary and per-frame

Pros:

- cleaner information architecture in theory
- avoids a large flat gallery

Cons:

- more UI complexity
- more state to synchronize
- higher bug risk in the current product state

### Option C: One gallery with categories plus strict entry consistency

Pros:

- simplest user mental model
- preserves figure-first cards
- keeps all figures visible without another navigation layer
- directly solves the "clicked one figure, saw another" problem
- can be implemented without waiting for deeper editor architecture work

Cons:

- requires a stronger entry contract than the current path-based flow
- requires a compatibility gate for object-mode claims

### Recommended Option

Adopt Option C.

This delivers the simplest gallery behavior while protecting the editor from over-promising capabilities it cannot yet support reliably.

## Top-Level Information Model

### Primary unit

The primary gallery unit remains:

- one figure card per logical figure

Not:

- one card per exported file
- one separate gallery for summary and per-frame

### Visible gallery categories

The gallery exposes four categories:

1. `All`
2. `Series Overview`
3. `Per-Frame Results`
4. `Other Exports`

This category list should stay intentionally small in the first delivery slice.

### Category meanings

#### `Series Overview`

Contains series-level figures that summarize the full condition sweep, typically discovered under `summary/`.

Examples for temperature SAXS:

- overview
- waterfall
- structure parameters
- heatmap
- invariant

#### `Per-Frame Results`

Contains figures derived from individual frames or individual condition directories, typically discovered under `per_frame/`.

Examples:

- scattering profile
- correlation
- IDF
- Porod
- Guinier
- Kratky

#### `Other Exports`

Contains exports that are valid assets but should not compete with the primary summary flow because they are:

- root-level compatibility outputs
- duplicated semantic outputs
- unclassified figures
- legacy exports whose editor relationship is not yet stable

#### `All`

Contains the full union of all categories while preserving category-aware sorting.

## Discovery And Grouping Rules

### Rule 1: Full discovery is the default

The gallery must discover all figure assets under `polynexus_output` instead of treating the current result manifest as a hard filter.

The current result manifest may still be used as:

- a recency hint
- a selection hint
- a ranking hint

It must not be allowed to hide other valid figures.

### Rule 2: Existing figure-first grouping still applies

Sibling `pdf/png/svg` assets that belong to the same logical figure remain grouped into one gallery entry using the existing figure-first rules:

- one logical figure identity
- one preview path
- one primary path
- zero or one editable source relationship
- zero or more secondary asset rows

### Rule 3: Category is an entry attribute, not a separate storage tree

Each grouped figure entry receives a category classification based on deterministic discovery rules. Categories are view-model metadata, not a second filesystem model.

### Rule 4: Root-level duplicate-style exports do not outrank series-summary figures

If a root-level figure and a `summary/` figure compete semantically, the `summary/` figure should remain the primary `Series Overview` entry and the root-level variant should move to `Other Exports` unless and until a stronger canonicalization rule is introduced.

## Gallery Entry Contract

The gallery entry must become the only supported editor-entry contract. Opening the editor from a bare path should become a compatibility fallback, not the primary behavior.

The required entry shape is:

```python
{
    "figure_id": "Fig_2_waterfall",
    "title": "Waterfall",
    "category": "series_overview",
    "state": "object_editing",
    "preview_path": ".../summary/Fig_2_waterfall.pdf",
    "primary_path": ".../summary/Fig_2_waterfall.pdf",
    "editable_path": ".../summary/Fig_2_waterfall.pdf",
    "document_mode": "object",
    "asset_paths": ("...pdf",),
    "assets": (...),
}
```

Required fields for strict entry behavior:

- `figure_id`
- `title`
- `category`
- `preview_path`
- `primary_path`
- `editable_path`
- `document_mode`
- `asset_paths`

Optional but useful future fields:

- `semantic_rank`
- `condition_value`
- `frame_label`
- `consistency_state`

## Gallery Interaction Model

### One gallery surface

The result area shows one gallery surface with category filters instead of a nested result browser.

### Default category

The default visible category should be:

- `Series Overview`

This gives the user a concise first screen while keeping every other figure one filter click away.

### Sorting rules

#### `Series Overview`

Must use semantic ordering rather than raw filename ordering.

Recommended first-pass order:

1. Overview
2. Waterfall
3. Structure Parameters
4. Heatmap
5. Invariant

#### `Per-Frame Results`

Sort first by condition value or frame order, then by figure type order within each frame.

#### `Other Exports`

Sort last and keep them visually de-emphasized relative to the main figure flow.

### Asset panel

The existing deferred asset exposure model remains valid:

- cards stay figure-first
- `pdf/png/svg` remain secondary asset rows for the selected figure
- assets do not re-enter the gallery as competing top-level cards

## Strict Preview-To-Editor Consistency Rule

This is the central rule of the design:

> The figure shown in the gallery card and the figure first shown in the editor must represent the same logical figure, the same layout structure, and the same visible chart identity.

This rule has two parts:

### 1. Identity consistency

The editor must open the same logical figure that the user selected.

Required checks:

- `entry.figure_id` must match the loaded figure document `figure_id`
- the chosen preview asset must belong to the same entry asset set
- the entry must not silently redirect to a sibling figure because the path looks similar

### 2. Layout consistency

The editor first screen must preserve the visible figure structure seen outside the editor.

Examples:

- a waterfall figure must still open as a waterfall figure
- a structure-parameter composite must not open as a flattened single-axis overlay
- a 2x2 overview must not open as one merged axis with unrelated series piled together

Strict consistency is required for the first visible editor state, not merely the internal document id.

## Editor Entry Routing

### Primary rule

The main window should open `ChartEditor` from a `FigureGalleryEntry`, not from a bare file path.

### Compatibility fallback

Path-only editor open may remain temporarily for legacy internal call sites, but those paths must first be resolved back to an entry whenever the gallery context exists.

### Entry-resolution requirements

When the user clicks a gallery card:

1. resolve the selected `FigureGalleryEntry`
2. validate entry/document identity
3. run strict consistency gating
4. choose editor mode from the gated result
5. open the editor with the resolved entry metadata

## Compatibility Gate For Object Editing

`document_mode == object` is no longer sufficient by itself to show `Object Editing`.

The system must promote a figure to `Object Editing` only when all of the following are true:

1. **Editable source is discoverable**
   - a stable figure document can be resolved
   - the figure id matches the entry figure id

2. **Entry identity is stable**
   - preview, primary, and editable targets all belong to the same grouped entry

3. **Renderer parity is currently supported**
   - the current editor can reconstruct the visible figure structure without changing its layout identity

4. **First-screen consistency passes**
   - the editor's initial visible figure is materially the same chart the user clicked

If any of these checks fail, the figure must downgrade to `Static Background`.

## First Delivery Capability Policy

### Promote to `Object Editing` first

Figures most likely to satisfy strict consistency in the first delivery include:

- single-axis multi-series line charts
- single-axis scatter charts
- single-axis bar or barh charts
- single-axis heatmaps where current preview and object redraw can be kept aligned

### Force `Static Background` first

Figures should remain `Static Background` in the first delivery when they are:

- multi-panel composite figures
- twin-axis or complex layout figures
- figures whose current object renderer changes the visible layout
- legacy or duplicate exports with unstable source relationships

This is a product promise decision, not a statement that the figure document is useless. A valid object document may still exist and still be saved. The UI simply must not advertise object editing until strict consistency is real.

## Temperature SAXS First-Pass Examples

For the current temperature SAXS flow, the first-pass behavior should be:

- `Fig_1_overview`: `Static Background`
- `Fig_2_waterfall`: candidate for `Object Editing` if strict parity passes
- `Fig_3_structure_parameters`: `Static Background`
- `Fig_4_heatmap`: candidate for `Object Editing` if strict parity passes
- `Fig_S1_invariant`: `Static Background` by default, promote later only if parity is proven
- root-level `temperature_overview`: classify as `Other Exports`, default to `Static Background`

These are first-delivery policy examples, not permanent capability limits.

## Error Handling And Fallback Rules

### Missing document

If no valid figure document exists:

- keep the card visible
- classify it normally if possible
- route to `Static Background` or preview-only behavior
- do not imply object editing

### Figure-id mismatch

If entry figure id and resolved document figure id differ:

- block object-mode entry
- log the mismatch
- fall back to `Static Background`

### Asset mismatch

If the chosen preview asset is not part of the resolved entry asset set:

- block object-mode entry
- treat the figure as inconsistent
- fall back to `Static Background`

### Unsupported layout parity

If the current object renderer cannot preserve the visible figure layout:

- keep the figure accessible
- open it in `Static Background`
- surface clear mode messaging inside the editor

The fallback path must preserve access without making a false editing promise.

## Data Flow Summary

### Gallery discovery flow

1. scan all figures under `polynexus_output`
2. group sibling assets into figure-first entries
3. classify each entry into one gallery category
4. compute entry ranking and semantic order
5. render the filtered gallery

### Editor open flow

1. user selects a gallery card
2. main window resolves the full `FigureGalleryEntry`
3. system validates figure/document/asset identity
4. system checks whether strict first-screen parity is currently supported
5. if yes, open in `Object Editing`
6. if no, open in `Static Background`
7. editor header shows figure title, mode, and capability boundary

## Acceptance Criteria

- the result gallery no longer hides valid summary or per-frame figures when the current result manifest is incomplete
- the product shows one gallery surface with category filtering instead of a summary/per-frame drill-down flow
- every gallery card still represents one logical figure rather than one exported file
- clicking a gallery card opens the same logical figure in the editor
- figures that cannot preserve first-screen parity do not advertise `Object Editing`
- composite figures no longer enter object mode when the current renderer would flatten or distort their layout
- root-level compatibility exports remain accessible without displacing the primary summary flow
- the editor continues to use the existing mode banner and capability messaging semantics

## Testing Strategy

### Gallery discovery tests

Add or update tests that verify:

- full `polynexus_output` scanning still discovers figures under `summary/` and `per_frame/`
- current-result preferred paths no longer hide other valid figures
- figure entries receive the expected category classification
- semantic ordering is stable for `Series Overview`

### Entry consistency tests

Add or update tests that verify:

- clicking a figure entry passes the full entry context into editor open logic
- figure-id mismatch blocks object-mode entry
- preview asset mismatch blocks object-mode entry
- unsupported layout parity triggers static-background downgrade

### Temperature SAXS regression tests

Add focused tests using the existing `pa6变温`-style fixture pattern to verify:

- summary figures all appear in the gallery
- per-frame figures appear under the correct category
- root-level compatibility exports land in `Other Exports`
- waterfall and heatmap only advertise object editing when parity gates pass
- overview and structure composite figures default to static mode in the first delivery

### UI behavior tests

Add or update GUI tests that verify:

- category filters change visible entries without changing figure grouping rules
- selecting a card keeps the secondary asset panel scoped to that figure
- editor titles and mode headers stay aligned with the selected gallery entry

## Risks And Controls

### Risk: category rules become brittle

Control:

- keep the first category model small
- classify primarily from directory role plus figure semantics
- route uncertain cases into `Other Exports` instead of inventing more categories

### Risk: object-mode gating feels conservative

Control:

- conservatism is intentional in the first delivery
- promote figures into `Object Editing` only after parity is proven by tests

### Risk: legacy path-based call sites keep bypassing the entry contract

Control:

- treat path-only editor open as a compatibility fallback
- route all gallery-originated editor opens through entry-based resolution

## First Delivery Slice

The first delivery slice must include:

- full gallery discovery
- category metadata on figure entries
- one gallery with category filtering
- strict entry-based editor open
- object-mode compatibility gating
- static-background downgrade for unsupported parity cases
- regression coverage for figure discovery and entry consistency

The first delivery slice must not include:

- new drill-down navigation
- new multi-panel object renderer architecture
- broad editor UI redesign outside the existing mode-banner semantics

## Next Step

Once this design is approved, the implementation plan should focus on:

- widening figure discovery without breaking figure-first grouping
- adding category-aware gallery entries
- passing full entry context into editor open
- implementing strict consistency gates and downgrade behavior
- covering the flow with focused regression tests before any deeper editor-expansion work
