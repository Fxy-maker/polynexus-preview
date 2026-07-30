# SAXS Scientific Acceptance Physical Gate Projection Design

**Date:** 2026-07-30
**Status:** Approved working design for the active SAXS quality goal

## Problem

`build_saxs_scientific_acceptance_audit()` currently surfaces metric levels,
reason codes, and detector geometry/mask provenance, but it does not expose the
physical checks already present in `MetricEvidence.physical_checks`. A reader
can therefore see that a metric is diagnostic without being able to trace the
existing method gate that produced that evidence.

## Goal

Add a detached, strict-JSON audit projection of existing physical checks and
method-gate states. The projection is explanatory evidence only. It must not
become a second implementation of SAXS physics.

## Design

Keep `build_saxs_scientific_acceptance_audit()` as the single audit builder and
extend its existing recursive inspection path. For each mapping found under an
existing metric-evidence field, inspect `physical_checks` when it is a mapping.
Store a JSON-safe copy under:

```text
physical_gate_evidence[label] = [checks, ...]
method_gate_status[label] = [True|False|None, ...]
```

The label is the same stable label already used by `evidence_levels`, for
example `metric:guinier`. Repeated frame evidence remains repeated in order;
the audit does not collapse or reorder frames. The mapping copy uses the
repository's existing `_contract_dict`/`_jsonable` conversion path so enums,
NumPy scalars, tuples, and nested mappings retain strict JSON behavior.

If `physical_checks["method_gate_passed"]` is explicitly present, preserve its
boolean value in `method_gate_status`. A false value appends the existing-gate
reason `method_gate_failed`. If a metric reports `applicable=True` but its
physical checks omit `method_gate_passed`, append `method_gate_not_assessed`.
Missing checks on a non-applicable or legacy node do not create a new reason;
this keeps old payloads behaviorally compatible while ensuring a declared
applicable metric is never silently treated as passed.

The existing status logic remains authoritative. A false gate still exposes its
existing level/reason evidence, while an unknown gate is at least
`review_required` when no stronger existing blocker applies. No source
`level`, `applicable`, `physical_checks`, publication flag, validation flag, or
`publication_decision_changed` value is mutated.

## Error and compatibility behavior

- Non-mapping `physical_checks` is ignored as malformed legacy evidence; it is
  not coerced into a pass.
- A non-boolean gate value is recorded as `None` and contributes
  `method_gate_not_assessed` rather than being truth-tested.
- Nested audit traversal and existing reason-code de-duplication remain the
  source of ordering and repeat handling.
- Payloads with no metric evidence retain their current output shape except
  for the always-present empty `physical_gate_evidence` and
  `method_gate_status` fields, matching the audit's existing always-present
  evidence maps.

## Testing

The focused regression uses synthetic mappings to cover a passing gate, a false
gate, an applicable metric with an unknown gate, detached input behavior, and
strict JSON serialization. Existing audit lifecycle, real-fixture, static,
temperature, strain, and full SAXS tests provide compatibility coverage.
