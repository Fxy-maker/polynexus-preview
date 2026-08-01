---
title: SAXS AI candidate-reference evidence transport
date: 2026-08-01
status: approved
---

# SAXS AI Candidate-Reference Evidence Transport

## Goal

Make the existing diagnostic `saxs_candidate_reference_resolution` visible
through the current SAXS result-consumer chain: Workbench parameters, Figure
provenance, Manifest-backed figure documents, and the Export quality bundle.

## Scope

The orchestrator already resolves an AI candidate reference and stores the
detached record in each `RoundRecord.llm_advice`. This task also copies the
latest resolution onto the active SAXS engine and result consumer DTO through
the existing `copy_saxs_ai_rescue_evidence` channel. Per-round history remains
the authoritative history; the engine field is the latest-state projection
used by current-result consumers.

The shared record retains `mode`, `status`, `resolved`, `unresolved_ids`, and
`reason_codes`. Figure provenance projects only `mode`, `status`, resolved
candidate IDs, unresolved IDs, and reason codes. Workbench text exposes the
same diagnostic identity and a validation reminder, never proposed candidate
values. Export quality evidence retains the detached JSON-safe record under
`ai_rescue.candidate_reference_resolution`.

## Non-goals

- no new SAXS metric, threshold, quality level, physical gate, or rescue rule;
- no candidate execution, validation, interpolation, missing-frame repair, or
  configuration mutation;
- no change to AI normalization, Advisor prompt, RoundRecord schema, Figure
  publication roles, Manifest lifecycle, or scientific promotion policy;
- no raw q/I, detector pixels, source paths, or unbounded prompt payloads in
  Figure or Workbench projections;
- no real-data, generated-output, memory, scratch, or test-storage cleanup
  changes, and no `scripts/test_storage.py --apply`.

## Data flow

```text
Advisor advice
    -> existing deterministic resolver
    -> RoundRecord.llm_advice[saxs_candidate_reference_resolution]
    -> engine/result latest-state field
    -> SAXS get_parameters / Workbench
    -> Figure quality_provenance / Manifest figure document
    -> Export quality_evidence.json
```

The resolver remains the only identity authority. Every consumer treats the
record as diagnostic evidence and keeps `validation_required` semantics.
Malformed or absent records remain invisible to optional consumer text and do
not create a new gate.

## Acceptance criteria

- A valid existing resolution survives the shared engine/result copy path.
- Figure and Manifest provenance retain a strict JSON-safe compact projection
  without proposed parameter values or publication-role changes.
- Workbench renders resolved/unresolved IDs and reason codes as advisory review
  text with a deterministic validation instruction.
- Export writes the full detached resolution under the existing `ai_rescue`
  quality-evidence section.
- Static, temperature, strain, malformed, empty, and non-SAXS behavior remains
  unchanged; all existing physical and quality gates remain authoritative.
