# Curve body hit regression

## Goal

Make generated curve bodies directly selectable and movable on logarithmic
axes, where Matplotlib's default `PathPatch.contains` can miss the visible
stroke.

## Affected boundaries

- Generated ChartEditor curve hit testing and body-drag routing.
- Generated workflow regression coverage; no analysis or document-schema
  changes.

## Non-goals

- No change to curve control-point semantics, default bend calculation, or
  static-image annotation behavior.
- No automatic axis-range expansion when a curve is dragged outside the
  visible plot area.

## Acceptance criteria

- [x] A visible generated curve stroke is a body-drag target on a logarithmic
  Y axis.
- [x] Moving that body updates the curve endpoints and control point through
  the existing preview transaction.
- [x] Existing generated workflow and curve tests remain green.

## Implementation plan

1. Reproduce curve body miss with a rendered-path test on a logarithmic axis.
2. Sample the quadratic curve in data space, transform samples to display
   space, and reuse the existing pixel segment hit tolerance.
3. Verify curve movement, generated workflow regressions, and the structured
   changed/type verifier.

## Verification

```text
python -m pytest tests/test_chart_editor_workflow.py tests/test_chart_editor_curve.py tests/test_chart_editor_generated_hit_testing_mixin.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-21-curve-body-hit-regression.md --changed --types
```
