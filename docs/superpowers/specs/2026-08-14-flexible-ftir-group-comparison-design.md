# Flexible FTIR Group Comparison Design

## Goal

Allow ARS to request a comparison of two selected FTIR candidate groups while
keeping the workflow low-friction: render usable figures whenever possible and
carry comparability warnings as evidence metadata instead of blocking the whole
request.

## Scope

This slice covers only the project-workflow FTIR figure candidate renderer.
It does not infer sample, batch, formulation, treatment effect, or publication
acceptance, and it does not add DSC/SAXS/WAXS/NMR comparison rendering.

## Behavior

- `compare_groups` remains a two-group, same-technique selection contract.
- Provider analysis runs for the selected artifacts before comparison rendering.
- A `group_comparison_overlay` is emitted when each selected group contributes
  at least one usable spectrum. Numeric condition axes do not need to match.
- Exact condition matches may produce a `group_difference` candidate. Missing
  or unmatched conditions suppress only that candidate and record
  `comparison_conditions_unmatched`.
- A comparison metric trend is emitted when each group has complete finite
  `Xc_pct` values. Different provider methods remain visible in candidate
  limitations and never become a scientific claim; the candidate stays
  `review_required`.
- The requested main figure limit still caps candidates at one or two. Omitted
  candidates retain explicit omission reason codes.
- Only unrecoverable input failures (no usable spectra in either group, invalid
  selection, or unsupported technique) block or omit work. Condition mismatch,
  method mismatch, and partial metrics are warnings for ARS/human review.

## Evidence

Each comparison candidate records both group IDs, source artifacts, condition
axis, output paths, status, and limitations. The evidence package copies only
selected candidate assets and rewrites paths to package-relative locations.

## Acceptance

- A valid two-group FTIR request executes selected providers and returns at
  least one comparison overlay when both groups contain usable spectra.
- Mismatched condition values do not prevent the overlay; difference output is
  omitted with a reason.
- Metric trends are omitted only for incomplete/non-finite metrics; differing
  methods are recorded as a limitation rather than silently merged.
- Invalid selections still block before provider execution.
