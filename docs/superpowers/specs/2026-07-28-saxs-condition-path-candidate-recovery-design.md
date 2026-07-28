# SAXS Condition Path-Candidate Recovery Design

## Problem

Path-based condition patterns currently stop after the first regex match in a
path. A match can still be unusable because conversion or the pattern
validator rejects it. Temporary/test directory names commonly contain tokens
such as `basetemp_20260730`, which can shadow a valid later directory such as
`temperature_180`.

## Decision

Treat each path component as an independent candidate for a path-search
pattern. Continue to the next component whenever the candidate has no match,
cannot be converted, or fails its validator. Return the first candidate that
passes the existing conversion and validation policy. Filename patterns keep
their existing single-stem behavior.

## Consequences

Valid condition directories are recoverable under arbitrary parent paths while
the existing pattern precedence, confidence, source labels, and scientific
condition semantics remain unchanged. No value is inferred from a rejected
candidate; the existing unresolved result still applies when no candidate is
valid.
