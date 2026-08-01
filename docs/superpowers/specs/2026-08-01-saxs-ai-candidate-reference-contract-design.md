# SAXS AI Candidate Reference Contract Design

## Goal

Allow the SAXS Advisor to point at an existing deterministic temperature
sequence-rescue candidate without turning that reference into an executable
request.

## Contract

The Advisor may return an optional `saxs_candidate_references` array. Each
entry is a candidate ID string copied exactly from the current summary
context's `series.sequence_rescue_candidates` list. The normalizer
deduplicates entries and drops every ID that is not present in the current
context. No candidate payload, numeric value, raw profile, detector data, or
source path can be returned through this field.

The field is available only when the current case is SAXS with temperature
summary candidates. For static, strain, unsupported, non-SAXS, missing, or
malformed context, the normalized field is an empty list (or absent for the
legacy direct normalizer call that has no SAXS context). A provider response
containing only references still has empty `changes` and cannot create a
preprocess intent or candidate plan.

References are diagnostic evidence only. They do not select, execute, rerun,
interpolate, repair, mutate configuration, or change any existing SAXS
physical, quality, sequence, or availability gate. The existing deterministic
candidate validator and shared preprocessing decision remain the only routes
that can assess a candidate, and the existing application gate remains the
authority for any later transaction.

## Data Flow

1. `build_saxs_ai_summary_context` supplies detached temperature candidates.
2. `PromptBuilder` tells the provider that only exact current candidate IDs may
   be referenced and that the field is advisory-only.
3. `Advisor` derives the allowed ID set from the current summary context and
   normalizes the provider response against that set.
4. The normalized advice is retained in the existing `llm_advice` audit record;
   orchestrator dispatch continues to inspect only existing `changes`,
   `recommended_actions`, and `preprocess_intent` fields.

## Failure and Degradation

- Invalid JSON or provider failure uses the existing mock fallback, with no
  candidate references.
- An unknown, duplicate, non-string, or context-incompatible reference is
  dropped without raising or inventing a candidate.
- Missing or malformed summary context produces no allowed IDs and therefore
  no references.
- The existing raw-field exclusion, strict JSON serialization,
  `candidate_only`, and `physical_validation_required` safeguards remain
  unchanged.

## Non-goals

- No new rescue algorithm, threshold, quality level, physical gate, sequence
  rule, or candidate execution path.
- No interpolation, missing-frame fabrication, automatic acceptance, rerun,
  configuration mutation, or GUI selection control.
- No changes to the existing `PreprocessIntent` schema or shared decision
  policy.
- No Figure, Manifest, Export, real dataset, memory, scratch, or storage
  changes.

## Verification Boundary

- `tests/test_advisor.py` covers ID allowlisting, deduplication, fail-closed
  modes, and reference-only advice remaining non-executable.
- `tests/test_saxs_prompt_builder.py` covers the prompt contract and
  diagnostic-only wording.
- Existing SAXS summary/context and orchestrator regression suites protect the
  unchanged candidate/gate paths.
