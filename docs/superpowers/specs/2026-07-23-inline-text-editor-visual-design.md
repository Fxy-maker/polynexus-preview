# Inline Text Editor Visual Design

## Goal

Make direct canvas text entry feel like editing text on the figure, rather
than placing a native desktop input control on top of it.

## Chosen interaction

- Keep the existing single-line canvas input, keyboard focus, blinking caret,
  Enter-to-commit, Escape-to-cancel, and double-click-to-edit behavior.
- Make the input surface transparent and remove the native focused QLineEdit
  border and empty-state placeholder from the canvas.
- Retain a subtle dashed outline around the user-drawn text region so an empty
  insertion point remains discoverable without resembling a full-width form
  field.
- Preserve the drawn region's geometry; only its editing chrome changes.

## Non-goals

- No multiline rich-text editor.
- No change to persisted text geometry, text rendering, or edit commands.
- No new toolbar or modal dialog.

## Acceptance

- New and existing canvas text editing show a visible caret without the native
  blue rounded input border or the `Annotation text` placeholder.
- The editor remains keyboard-focusable and keeps its existing commit/cancel
  semantics.
- Existing direct-text workflow tests continue to pass, with focused coverage
  for the visual properties of the inline editor.
