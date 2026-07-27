# SAXS Condition-Axis Workbench Visibility Design

Date: 2026-07-27
Status: approved working design

## Goal

Expose defective temperature-series condition-axis provenance in the existing
SAXS Workbench review channels without creating a second scientific decision
system.

## Contract

`build_saxs_results_presentation()` will consume the existing
`metric_evidence[*].condition_axis` mapping. It will not inspect frame values,
re-sort arrays, infer defects, or consult technique-specific algorithm state.

Only `status=diagnostic` and `status=empty` produce a risk hint. The hint names
the metric and `condition_name`, reports the counts of invalid, duplicate, and
non-monotonic positions, and shows a bounded representative position list.
The full `condition_values` and position arrays remain in the existing nested
Diagnostics serialization. `status=ordered` produces no additional risk text.

The hint is advisory: it says to review the axis before interpreting sequence
trends and never says that a transition, physical pass, rescue, or publication
decision has been established. The same formatter handles any condition name;
it does not apply an ascending-axis rule to strain or invent strain semantics.

## Data flow

```text
metric_evidence[*].condition_axis
        -> presentation-only formatter
        -> existing risk_text / next_text
        -> Diagnostics keeps original nested JSON
```

The formatter is defensive about malformed mappings and position arrays. It
skips an absent/empty mapping and treats an unknown status as non-actionable;
the existing Diagnostics path remains the fallback for unexpected payloads.

## Localization

Use the existing Workbench language switch and the same inline localized style
as `_series_metric_review_text()`. English and Chinese wording must retain the
terms “diagnostic”/“诊断”, the axis name, and the instruction to review before
trend interpretation.

## Verification boundary

Focused tests cover defective and clean axes, representative positions,
Chinese text, and unchanged nested Diagnostics payload. The complete SAXS
matrix and task-scoped verifier remain required. No real-data scientific
acceptance is claimed by this presentation-only task.
