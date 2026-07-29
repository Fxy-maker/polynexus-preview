# SAXS Legacy Temperature Figure Partial-Frame Design

## Problem

Core temperature analysis already retains every source frame and degrades a
fully invalid q/I profile to existing `Unusable` evidence. The compatibility
Figure provider still calls `_clean_frame()` for every frame and propagates its
no-plottable-data `ValueError`, so one unusable frame can remove the entire
temperature Figure set. That is a presentation-boundary failure, not a reason
to recalculate or repair the scientific data.

## Proposed behavior

The legacy temperature provider will keep a slot for every source frame while
projecting q/I. Successful slots contain the existing cleaned arrays. Failed
slots contain no curve plus a stable omission reason. Per-frame definitions,
waterfall sources, and summary/heatmap selections operate only on successful
slots, but all indices continue to refer to the original source sequence.

The existing evidence plan remains the authority for publication roles. The
provider adds the unavailable-frame reason to the recipe evidence; it does not
promote a frame, downgrade a metric, or create a replacement observation.
When no frame is plottable, the provider returns the existing empty-definition
result rather than raising from this presentation boundary.

## Data flow

```text
source q/I slots
    -> detached existing numeric cleaner
    -> valid curve | unavailable slot + reason
    -> original-index evidence plan
    -> valid per-frame / waterfall / summary Figure definitions
```

Structural sequence-count validation stays before this flow. Existing
same-length dirty arrays with some valid positive pairs keep their current
behavior. Only a slot that cannot produce a valid curve is omitted.

## Error and compatibility rules

- Keep `temperature frame counts differ` unchanged.
- Treat the existing cleaner's frame-level `ValueError` as an unavailable
  presentation slot, with `figure_profile_unavailable` in recipe evidence.
- Do not catch errors from summary construction when valid slots exist; a
  malformed result-array shape remains an explicit provider contract failure.
- Keep current Figure ids for valid source frames, including gaps such as
  `.001` and `.003` when source frame 2 is unavailable.
- Ensure all new recipe values are detached JSON-safe primitives.

## Testing strategy

The RED test calls `build_saxs_temperature_definitions()` with two aligned
frames and makes only the second q/I pair set nonnumeric. It asserts the
desired valid-frame Figure, omitted-frame evidence, and unchanged source-index
semantics. Before the production change it must fail at the current
`no plottable data` exception. Existing clean, dirty-valid-pair, V2 lifecycle,
and strict recipe validation tests provide compatibility coverage.
