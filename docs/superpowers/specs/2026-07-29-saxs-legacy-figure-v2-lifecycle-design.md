# Legacy SAXS Figure V2 lifecycle acceptance design

## Decision

Add a consumer-level acceptance regression to the existing lightweight SAXS
Figure provider test module.  It will build legacy static, strain, and
temperature definitions from the existing in-memory fixtures, assert their
mode-specific adapter keys and ready V2 capability, and run one definition per
mode through `FigurePipeline` to verify the Manifest sidecar.

## Rationale

The runtime audit found no missing adapter or capability failure in the legacy
routes, but the existing tests do not assert the complete three-mode lifecycle
as one contract.  The test makes the already-approved behavior durable without
adding another adapter or changing the shared capability resolver.

## Boundaries and safety

- Static uses `saxs_static`, strain uses `saxs_strain`, and temperature uses
  `temperature_saxs`, exactly as the existing recipes declare them.
- The test checks only capability and sidecar state; it does not promote a
  publication role or inspect scientific values.
- The sidecar is written under pytest's temporary directory and contains only
  the in-memory fixture definitions.
- Unsupported objects remain covered by the existing V2 capability tests and
  continue to fail closed.

## TDD/acceptance evidence

This is a verification-only task because the audited runtime behavior already
exists.  The regression is expected to be existing GREEN; a production RED
would be treated as a real integration gap and would require a separate design
before implementation.  The task still runs focused, structured, complete SAXS,
storage dry-run, diff, and explicit allowlist checks.
