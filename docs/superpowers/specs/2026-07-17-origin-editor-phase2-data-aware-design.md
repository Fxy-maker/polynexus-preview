# Origin Editor Phase 2: Data-Aware Re-rendering Design

Phase 1 establishes a stable publication-editing core. Phase 2 may add data
editing, fitting, and recipe-driven re-rendering only through the contracts
below.

## Stable Phase 1 contracts

- `FigureDocument` remains the JSON boundary. Objects have canonical `id`,
  `type`, `layer_id`, `bounds` or endpoint geometry, `style`, visibility, and
  lock state. Unknown fields survive normalization and round trips.
- `EditSession` owns the private canonical document, one selection state, dirty
  state, and command history. UI code must use `EditCommand` instead of
  mutating a `FigureObjectStore` or annotation widget directly.
- `EditCommand` implementations must validate capabilities before mutation,
  return an `EditResult`, and provide an isolated snapshot for undo/redo.
- `EditCapabilities` drives Inspector availability. Unsupported fields are
  disabled or hidden with a reason; renderer errors never report a successful
  edit.
- `AnnotationRenderAdapter` and Matplotlib rendering are projections of the
  canonical document. Projection must not create history entries.
- `figure_edit_persistence` writes the target asset, `.pnfig.json`, and legacy
  compatibility sidecar as one save bundle. Legacy sidecars remain readable
  but are not the editing authority.

## Phase 2 seam

Generated documents may add:

```json
{
  "data_sources": [{"id": "source-1", "kind": "csv", "path": "data/x.csv"}],
  "recipe": {"module": "...", "function": "...", "inputs": {}, "parameters": {}}
}
```

`data_sources` and `recipe` are inputs to a renderer, not UI-owned mutable
state. A re-render produces a proposed document revision. The session applies
that revision through an explicit command so undo/redo and save semantics stay
consistent.

## Preservation rule

Re-rendering may update generated objects and their `source_ref`/`data_ref`,
but it must preserve user-created annotations (`text`, `line`, `arrow`,
`rectangle`, and `highlight`) by object id. If an annotation can no longer be
placed, the editor must show a conflict and require explicit user confirmation
before removing it. No implicit annotation deletion is allowed.

## Out of scope for Phase 2 preparation

The Phase 1 UI must not silently expose data-table mutation, fitting controls,
or new chart recipes. Those features require separate commands, validation,
tests, and a migration story for existing documents.
