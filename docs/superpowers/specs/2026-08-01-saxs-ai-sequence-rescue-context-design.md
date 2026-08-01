# SAXS AI Sequence Rescue Context Design

## Goal

Expose existing deterministic temperature sequence-rescue candidates to the
summary-only SAXS AI context so Advisor diagnosis can reason about recoverable
alternatives without receiving raw profiles or applying a candidate.

## Contract

`sequence_rescue_candidates` is copied only from the existing temperature
series result. The AI context may contain a detached list of candidates with
the fields `candidate_id`, `kind`, `parameters`, `reason_codes`, and
`requires_validation`. Within `parameters`, only frame/axis/metric values,
path status, proposed source, missing-frame preservation, and candidate-only
application mode are allowed. Unknown fields, raw q/I, detector pixels,
source paths, and arbitrary nested payloads are dropped.

The candidates remain advisory evidence. `candidate_only=True`,
`physical_validation_required=True`, `preserve_missing_frames=True`, and
`requires_validation=True` remain explicit. No candidate is executed,
selected, interpolated, or promoted by this change.

## Boundaries

- `polynexus/core/saxs_engine/saxs_ai_rescue.py` owns the strict projection.
- `tests/test_saxs_ai_summary_context.py` locks source, field, detachment, and
  raw-field exclusion behavior.
- `tests/test_advisor.py` verifies the existing prompt receives the projected
  candidate evidence after prompt sanitization.

## Non-goals

- No new rescue algorithm, threshold, quality level, physical gate, or
  publication decision.
- No changes to temperature analysis, Workbench, Figure, Manifest, Export, or
  sequence candidate generation.
- No automatic acceptance, rerun, configuration mutation, or storage cleanup.
