# SAXS empty temperature series fail-closed design

## Context

The frame-level SAXS boundary now turns an empty sanitized q/I profile into an
auditable `Unusable` result. The temperature-series boundary still assumes at
least one frame because it calculates the reference invariant and long period
from index zero. An empty acquisition should remain a valid, explicit empty
observation rather than aborting the caller.

## Design

`analyze_temperature_series()` will keep its current temperatures/q/I length
validation, then return before sorting when `n_points == 0`. The returned
`TempSeriesResult` will use empty NumPy arrays for all numeric frame tracks and
empty lists for frame/status/candidate tracks. Its `guinier_sequence_evidence`
will be built by `build_guinier_sequence_evidence([], [], source_indices=[],
source_ref="saxs_temperature.guinier_sequence")`, and its `metric_evidence`
will be built by `build_series_metric_evidence([], metric_names=("guinier",
"porod", "kratky", "invariant", "lamellar"), source_ref=
"saxs_temperature.metric_evidence", frame_source_indices=[],
condition_name="temperature_C", condition_values=[])`.

Those existing builders already define the required fail-closed reason codes,
levels, empty condition-axis state, and strict JSON representation. No frame,
temperature, Rg, transition temperature, or rescue candidate will be created.
The existing length mismatch `ValueError` remains before the empty branch.

## Invariants

- Empty sequence evidence is `Unusable`, never `Diagnostic` or `Trend`.
- `guinier_sequence_no_valid_frames` and `series_no_frames` remain the
  authoritative reasons for the empty state.
- Non-empty series sorting, source-index mapping, frame analysis, physical
  gates, and downstream consumers are unchanged.
- The result and evidence payloads are safe for `json.dumps(...,
  allow_nan=False)`; unavailable scalar transition values remain absent from
  evidence rather than fabricated.

## Verification evidence (2026-07-28)

- RED reproduced the `IndexError` at `q_sorted[0]`; the focused mismatch
  regression remained green.
- Focused GREEN passed `22` tests. The exact `test_saxs_*.py` matrix passed
  `415` tests with `6` existing warnings.
- Structured task verification and the explicit allowlist checkpoint are
  recorded by the task card after the final documentation update. Full/boundary
  repository verification remains a separate release gate.
