# Generated canvas drag regression

## Goal

Restore reliable direct manipulation for generated text and line objects when
the chart uses a logarithmic axis.

## Scope

- Use the rendered text bounding box for text-body hit testing.
- Preserve axis scales while rebuilding a generated canvas during a drag.
- Translate non-linear-axis geometry in display space using the active artist
  transform, while retaining exact data-coordinate deltas for linear axes.
- Track the current pointer position in pixels for preview updates.

## Affected boundaries

- Generated ChartEditor hit testing, geometry preview, drag execution, and
  viewport restoration.
- Generated-canvas workflow regression tests only; no core analysis boundary.

## Non-goals

- No changes to scientific data, document schema, or static-image editing.
- No changes to endpoint/handle semantics or drag history behavior.

## Acceptance criteria

- [x] A rendered text label can be selected and used as a body-drag target even
  when its data-coordinate fallback bounds do not contain the click.
- [x] A line body can be selected and dragged downward on a logarithmic Y axis without its
  preview becoming negative or disappearing.
- [x] Existing linear-axis text and rectangle body-drag expectations remain exact.
- [x] Focused workflow tests and the repository changed/type verifier pass.

## Implementation plan

1. Reproduce the rendered-text hit failure and logarithmic-axis line preview
   failure with focused regression tests.
2. Use rendered artist bounds for text hit testing and retain pointer pixels
   during generated drags.
3. Preserve axis scales during canvas replacement and use artist transforms
   for non-linear-axis display translations.
4. Run focused tests, the structured verifier, and the final diff checks.

## Verification

```text
python -m pytest tests/test_chart_editor_workflow.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-21-generated-canvas-drag-regression.md --changed --types
```
