# Editor Responsive Sidebar Design

## Goal

Ensure every ChartEditor inspector tab remains readable and actionable in a
narrow sidebar, without horizontal clipping or a horizontal scrollbar.

## Chosen interaction

- Treat 360 logical pixels as the compact-sidebar breakpoint.
- Keep the inspector vertically scrollable only; its content must not exceed
  the drawer viewport horizontally.
- At the compact breakpoint, style and annotation forms use a label-above,
  full-width control layout. Multi-action rows wrap into a compact grid rather
  than retaining desktop column counts.
- The object tree receives the available central height while object properties
  remain below it in the same vertical scroll flow.
- Font sizes, commands, object-edit behavior, and persisted document state do
  not change.

## Non-goals

- No removal of editor controls or translation strings.
- No canvas-width increase that compromises the figure workspace.
- No redesign of analysis or export behavior.

## Acceptance

- At a 280px inspector width, every tab has no horizontal scrollbar and no
  control extends beyond the viewport.
- Annotation action buttons and style preset/template actions remain legible
  and usable after reflow.
- Object tree and property controls remain reachable through vertical scrolling.
- Focused Qt layout regressions cover compact width plus the existing editor
  workflow matrix.
