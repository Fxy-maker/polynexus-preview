# SAXS Rescue-Candidate Workbench Visibility Design

**Date:** 2026-07-28
**Status:** approved working design for the active SAXS quality goal

## Goal

Make existing deterministic temperature sequence-rescue candidates visible at
the Results Workbench boundary without changing their candidate-only status.

## Design

Reuse the existing `sequence_rescue_candidates` list on `TempSeriesResult`.
The existing quality-copy helper will deep-copy that field, and the temperature
parameters branch will expose it in the public payload; no candidate is
created, selected, applied, or rerun by this slice. Static and strain
parameter paths remain unchanged.

Add one presentation-only formatter that accepts the public payload and reads
only candidate mappings. For each valid mapping it reports the existing
candidate ID, frame index, axis/source values, `apply_mode`,
`requires_validation`, and bounded reason codes. It emits an advisory risk and
next-step message that explicitly requires deterministic re-analysis and the
existing physical/quality/sequence gates. Empty or malformed entries are
ignored without generating a pass or rescue claim; nested payload data remains
available to Diagnostics, History, and Export.

## Safety boundary

`candidate_only=true`, `original_preserved=true`, and
`requires_validation=true` are observations from the existing candidate
contract, not new acceptance decisions. The Workbench must never say that a
candidate was applied, accepted, physically valid, or publication-ready.

## Verification

Tests cover deep-copy transport, candidate details, empty/malformed inputs,
English/Chinese review text, source immutability, and regressions for existing
metric/Guinier/detector channels. The structured task verifier and exact SAXS
matrix remain required; full/boundary output is recorded only when a fresh run
completes with a final summary.
