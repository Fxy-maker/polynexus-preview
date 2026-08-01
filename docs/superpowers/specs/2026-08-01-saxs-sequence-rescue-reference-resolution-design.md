# SAXS Sequence Rescue Reference Resolution Design

## Goal

Resolve an advisory AI candidate ID against the current deterministic
temperature result without allowing the summary boundary to fabricate or
execute a rescue candidate.

## Contract

`resolve_sequence_rescue_candidate(candidates, candidate_id, mode="temperature")`
returns a newly materialized `RescueCandidate` only when exactly one current
candidate has the requested ID and all existing candidate identity markers are
present:

- mode is `temperature`;
- `kind` is `deterministic`;
- `requires_validation` is true;
- `source` is `saxs_temperature.select_lc_sequence_path`;
- parameters identify the temperature axis, `lc_nm` metric,
  `apply_mode="candidate_only"`, and `preserve_missing_frames=true`.

Unknown IDs, empty IDs, non-temperature modes, malformed records, ambiguous
duplicate IDs, AI candidates, missing source provenance, and candidates with
changed candidate-only markers return `None`. The function performs no
analysis, mutation, interpolation, frame creation, or gate decision.

The resolver consumes the current result's full candidate records, not the
summary-only prompt projection. This is intentional: the prompt projection
does not carry source provenance and therefore cannot be promoted back into a
validation object by itself.

## Data Flow

1. Advisor returns an already allowlisted `saxs_candidate_references` ID.
2. A later deterministic caller supplies the current temperature result's
   `sequence_rescue_candidates` records and the referenced ID.
3. The resolver returns a detached candidate or `None`.
4. A separate caller must still run `validate_sequence_rescue_candidate` with
   explicit hard, physical, preservation, and sequence gate results.

## Failure and Degradation

- Any malformed or incomplete candidate is ignored.
- A missing or ambiguous match fails closed to `None`.
- Unsupported modes fail closed without inspecting candidate data.
- Returning a candidate never implies acceptance; `requires_validation` stays
  true and no `RescueValidationReport` is created by this resolver.

## Non-goals

- No new physical or quality thresholds, gate semantics, sequence policy,
  interpolation, frame repair, rerun, configuration mutation, or automatic
  acceptance.
- No AI prompt, Advisor, GUI, Workbench, Figure, Manifest, or Export change in
  this atomic task.
- No real datasets, memory, scratch, or storage change.
