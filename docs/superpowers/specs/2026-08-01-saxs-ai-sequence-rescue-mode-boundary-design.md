# SAXS AI Sequence Rescue Mode Boundary Design

## Goal

Make the SAXS prompt sanitizer fail closed when sequence-rescue candidates
appear in a non-temperature context.

## Contract

`sequence_rescue_candidates` may cross the summary/prompt boundary only when
the normalized context mode is `temperature`. Static, strain, unsupported, and
missing modes retain all existing summary evidence but omit this field. The
builder's existing temperature-only behavior remains unchanged.

## Non-goals

- no rescue calculation, candidate execution, interpolation, threshold, gate,
  quality-level, publication, or mode-selection change;
- no raw q/I, detector, source-path, real-data, GUI, export, or storage change.
