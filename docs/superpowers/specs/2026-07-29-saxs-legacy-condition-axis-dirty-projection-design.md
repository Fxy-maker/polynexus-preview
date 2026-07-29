# SAXS Legacy Condition-Axis Dirty Projection Design

## Problem

The compatibility SAXS Figure provider uses `_frame_condition_values()` for
legacy strain/static frame labels. Its whole-array `np.asarray(...,
dtype=float)` conversion raises when one condition token is malformed, even
though the frame q/I projection and the modern Figure provider can safely keep
the remaining evidence. This is a projection failure, not a scientific reason
to invent a condition.

## Proposed behavior

Reuse the existing detached `_coerce_numeric_array()` helper at the condition
projection boundary. Numeric values retain their existing order and labels;
malformed or non-finite values become `NaN`. The existing `_frame_label()` then
uses its already-defined `Frame <index>` fallback. The source engine's
condition container is never modified.

## Compatibility rules

- Keep the existing source-selection order: strain result values first, then
  engine conditions.
- Keep the existing length check and all-`NaN` fallback for a mismatched axis.
- Do not sort, interpolate, infer, or discard any frame.
- The change affects only legacy Figure labels; analysis outputs and quality or
  publication decisions remain untouched.

## Testing

The RED test creates a legacy strain state with valid q/I arrays and a dirty
condition sequence `("0", "bad-strain", "25")`. It asserts the three frame
definitions remain in source order, numeric labels survive, and the middle
frame falls back to `Frame 2`. It also asserts the caller-owned condition list
is unchanged. Before the change, the provider fails at the whole-array float
conversion.
