# SAXS AI 1D method evidence context design

## Contract

The existing SAXS engine emits compact `metric_evidence` for Guinier, Porod,
Kratky, invariant, and lamellar methods. The AI summary context must transport
those already-computed fields as detached JSON-safe evidence for Static,
Temperature, and Strain modes.

The context is diagnostic input only. It remains `candidate_only=True` and
`physical_validation_required=True`; it cannot authorize a candidate, rescue,
configuration mutation, or publication role.

## Verification boundary

The regression checks the method keys, evidence level, value, and physical
checks after summary projection. It also runs the existing prompt sanitizer and
raw-field exclusions through the adjacent regression suite. No new scientific
threshold is introduced, and no production code is required if the existing
generic projection satisfies the contract.

## Failure behavior

Missing or malformed evidence continues to be omitted or represented by the
existing unavailable/fail-closed context. Non-finite values remain normalized
by the existing JSON-safe boundary. Raw q/I, detector pixels, and source paths
remain excluded.
