# Definition of Done

An atomic PolyNexus task is complete only when all applicable statements hold.

- The requested behavior and explicit non-goals are documented in the task or
  prompt.
- A focused regression test was written first for a behavior change and was
  observed failing for the expected reason before the implementation.
- The implementation uses the existing project, run, chart, evidence, and
  export contracts rather than creating an entry-point-specific copy.
- Scientific values come from deterministic analysis with source, method, and
  run provenance. Diagnostics remain diagnostics unless their existing policy
  explicitly permits a stronger claim.
- Every affected entry point is named. A shared-object change has focused
  producer and consumer verification for AI/CLI and/or GUI as applicable.
- The exact verification commands were run successfully and their outcomes are
  reported. Full/boundary verification is required only for release,
  integration, or explicitly broad work.
- Durable project state, decisions, limitations, or lessons were updated when
  they changed.
- Investigation, test selection, and reporting stayed scoped to the changed
  boundary. Any broader context or log collection has a stated reason.
- A local allowlisted checkpoint was created after verification. It has not
  pushed, merged, deployed, deleted data, or bypassed required human review.

Architecture, schema, security, performance, and scientific-semantics work
remain review-required before merge even when the local checkpoint succeeds.
