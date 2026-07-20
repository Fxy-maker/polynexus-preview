# Chart Editor Visual Polish and Interaction Design

## Goal

Make the chart editor feel like a coherent professional desktop tool: the
canvas gets the available space, the left tool rail is legible and grouped,
the right inspector exposes high-frequency actions near the object tree, and
selection feedback is consistent.

## Scope

- Rebalance the editor shell and make the canvas/inspector responsive.
- Replace the icon-only narrow rail with a compact grouped tool rail using
  text-under-icon buttons, selected states, separators, and accessible tooltips.
- Keep all existing commands and shortcuts, but expose visibility, lock,
  alignment, distribution, grouping, and deletion next to the object list.
- Make all inspector tabs visible without horizontal tab scrolling.
- Apply the existing theme tokens to the editor-specific surfaces.

## Non-goals

- No changes to scientific rendering, data-source resolution, or figure-document
  semantics.
- No new editor commands; the new controls call the existing command/session
  routes.
- No changes to generated outputs or real regression datasets.

## Interaction design

The left rail is 72–84 px wide and divided into three groups: creation tools,
history, and export/view actions. Creation buttons show icon plus localized
short label; only one creation tool can be active. Undo/redo/export are
separated visually and preserve their current enabled state.

The right inspector is 360–400 px wide when space permits and collapses only
through the existing header toggle. Its tab bar does not use scroll arrows.
The Object tab places a compact selection action strip between the search field
and the layer tree. Menu buttons expose align/distribute/arrange actions while
single-object actions remain one click away. Existing context-menu and keyboard
routes remain the source of truth.

The canvas stack uses expanding size policies and a stretch layout so the
rendered figure fills the available vertical area. The contextual style bar
remains attached to the canvas bottom, but does not consume a large empty
region when hidden.

## Visual language

Use the existing `ThemeEngine` tokens: card background for the rail and
inspector, light border, primary text, muted secondary text, and the existing
accent for active/hovered controls. Avoid per-widget arbitrary colors. Selected
tool buttons have a clear accent background and pressed state; destructive
actions use the existing danger treatment only where applicable.

## Acceptance criteria

- The editor canvas expands vertically without the large unused lower blank
  region shown in the current screenshot.
- The left rail shows readable labels, grouped actions, active tool feedback,
  and accessible tooltips at both Chinese and English locales.
- The inspector shows all four tabs without arrow scrolling at normal window
  sizes, keeps a usable minimum width, and exposes common selection actions
  adjacent to the layer tree.
- Existing selection, undo/redo, shortcuts, context menus, and persistence
  behavior remain green.
- Focused layout/toolbar tests and `python scripts/verify.py --changed --types`
  pass before checkpoint.
