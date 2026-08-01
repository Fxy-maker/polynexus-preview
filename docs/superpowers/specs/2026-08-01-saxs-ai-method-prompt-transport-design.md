# SAXS AI 1D method prompt transport design

## Contract

The Advisor receives only the sanitized SAXS summary context. The actual
prompt must retain the existing compact evidence keys for Guinier, Porod,
Kratky, invariant, and lamellar methods, together with the candidate-only and
physical-validation safeguards.

## Authority boundary

This is a transport-only contract. Prompt visibility does not authorize model
decisions, candidate execution, rescue, configuration mutation, or publication.
Existing deterministic validators and physical gates remain authoritative.

## Security boundary

The regression runs through the real `Advisor.advise()` path and checks the
captured prompt. Existing sanitizer behavior continues to exclude raw profile,
detector, and source-path fields. No new prompt fields are allowlisted.
