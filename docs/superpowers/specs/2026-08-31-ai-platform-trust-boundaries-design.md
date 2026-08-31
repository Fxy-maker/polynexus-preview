# AI Platform Trust-Boundary Repair Design

## Objective

Close the fail-open paths identified in the review of `fc239090` without
changing deterministic provider algorithms. The repair makes planner admission
the execution boundary, centralizes strict shared-run parsing, and moves
scientific eligibility into machine-checkable descriptor contracts.

## Architecture

`CapabilityPlanner.inspect()` remains the only producer of an executable
admission. A plan item carries a signed-by-content admission payload containing
descriptor identity, selected DataBlock identity, gate result, required
calibration identities, and content-addressed bindings for every declared
dependency (dependency descriptor version/hash plus its admission hash).
`ExecutionGraph` accepts these admissions and rejects known descriptor nodes
without a matching successful admission. It resolves every declared dependency
through the same runtime registry and requires that dependency's own trusted
admission, preventing a target admission from being replayed with an omitted
or substituted dependency descriptor. The graph resolves each binding through
the target node's unique direct edge; an unrelated node with the same
capability ID cannot satisfy it, and multiple direct nodes for one declared
capability fail closed as ambiguous. It derives the post-execution state itself;
caller-provided promotion and cached promotion are never trusted.

`ComputeRun` consumers share one strict parser. If the `compute_run` key is
present at any projection layer, the parser requires a mapping, explicit
completed status, a valid complete four-axis `ComputationState`, and equality
among state/descriptor/provenance/uncertainty aliases when those aliases are
present. Only a completely absent key permits historical legacy extraction.

Descriptor input contracts gain explicit axis/unit/quantity/shape/metric-path
constraints. Planner evaluation and cache-key construction use the resolved
descriptor, including its calibration requirements and declared dependencies.
Legacy provider metric projections are represented by a validated
`ProviderResultInput`/metric-manifest DTO rather than an unsupported DataBlock
kind.

## State and failure policy

Discovery may report `executable`, but that means “admissible for execution,”
not “already computed.” Execution success is emitted as `computed`,
`not_assessed`, `diagnostic_only` unless trusted review metadata explicitly
permits a stronger state in a separate promotion step. `needs_input`, blocked,
failed and malformed cache entries never execute as completed results.

## Testing

Regression tests cover admission forgery/mismatch, descriptor-derived
calibration invalidation, cache promotion injection, strict projection
contradictions and legacy fallback, invalid units/axes/metric paths, and the
provider-result DTO. Existing producer and AI/CLI/GUI/evidence/Joint consumer
matrices remain part of verification.
