# SAXS strain-axis fail-closed design

## Context

Temperature-series input already converts malformed axis values to `NaN` and
records an existing condition-axis diagnostic. The strain path still performs
`np.array(strains, dtype=float)`, which raises for a malformed label, and it
indexes the first sanitized profile even when the series is empty. A single
bad label can therefore prevent all profile evidence from being returned.

## Design

Normalize each supplied strain value independently with a small finite-float
coercion helper. Numeric strings remain numeric; malformed and non-finite
values become `NaN`. The original list length and order are retained. Pass the
normalized values to `build_series_metric_evidence()` as `condition_values`
with `condition_name="strain_pct"`, reusing its existing invalid-index,
status, and reason-code contract.

When no frames are supplied, skip reference-profile invariant calculation and
let the existing empty series evidence builders produce `Unusable` summaries.
When a frame has an invalid strain label, retain its profile analysis but do
not use `NaN` as a phase-boundary coordinate. No new physical interpretation
or threshold is introduced.

## Testing and safety

Tests use a small fake frame result only to isolate the axis boundary. They
assert exact frame count/order, `NaN` retention, condition-axis diagnostics,
empty-series evidence, and unchanged clean-path behavior. No raw data,
published output, GUI code, or rescue contract is touched.

The focused regression and downstream consumer matrix passed (`22` and `147`
tests respectively). The complete `458`-test SAXS collection hit the bounded
tool timeout without a pytest summary, so this task deliberately does not
claim a full SAXS pass.
