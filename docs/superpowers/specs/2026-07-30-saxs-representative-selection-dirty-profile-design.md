# SAXS representative selection dirty-profile design

## Decision

Make the representative-frame selector project q and intensity tokens
elementwise through the existing detached `_coerce_numeric_array()` helper.
The selector will then apply its current aligned-prefix, finite-pair,
sorting, integration, and maximum-intensity logic unchanged.

## Invariants

- A malformed q or intensity token affects only its aligned pair for the area
  feature; other finite pairs remain available.
- Maximum intensity keeps the existing intensity-only finite-value behavior.
- No q/I source array is mutated, sorted in place, interpolated, or repaired.
- Representative count, minimum separation, condition ordering, reasons,
  manual overrides, and frame indices remain unchanged.
- This is a Figure selection feature projection only; raw analysis outputs,
  quality levels, physical thresholds, publication roles, and AI/rescue
  decisions are untouched.
- Empty, malformed-shape, and all-invalid input remains fail-closed with
  missing selection features.

## Verification boundary

The task requires TDD RED/GREEN, focused selection tests, the structured
verifier, a fresh `test_saxs_*.py` matrix with an actual pytest summary,
`git diff --check`, and storage report/clean dry-runs. `test_storage.py --apply`
is prohibited.
