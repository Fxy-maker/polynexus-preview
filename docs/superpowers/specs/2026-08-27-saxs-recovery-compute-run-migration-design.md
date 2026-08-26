# SAXS recovery ComputeRun migration design

## Context

Most file-backed orchestration now uses the shared `CanonicalTemplate →
CapabilityItems → ComputeRun` producer. The SAXS condition-recovery candidate is
the remaining real-source exception: it mutates the controlled engine context
and calls `engine.run_pipeline()` directly.

## Design

During `rerun_condition_recovery`, after merging the proposed condition context,
the orchestrator calls `ComputeRunService.run_direct` with the existing engine
and the baseline run's canonical template. This preserves source identity,
avoids a second conversion, and makes provider execution and capability
projection use the same producer as the initial run. The returned run is held
locally until candidate scoring accepts it. On acceptance it replaces
`self._compute_run`; on rejection or rollback the previous run remains the
authoritative report object.

When the winning candidate is replayed after restoring the baseline engine
configuration, its selected recovery context is merged again before analysis.
This keeps the final engine state aligned with the accepted shared run.

If the session has no shared run (the established missing/synthetic compatibility
case), the current provider-only call remains unchanged. Service failures are
reported as rejected candidate reasons and never fall through to a second
provider invocation.

## Safety and compatibility

No condition precedence, quality guard, candidate ranking, or provider algorithm
changes. No raw input is copied or modified. Existing synthetic tests and legacy
readers remain supported. The final report continues to expose one JSON-safe
`ComputeRun` projection.

## Verification

The regression test spies on the service call, verifies canonical-template
identity reuse, asserts accepted-run replacement, and verifies the synthetic
fallback still calls the provider directly. The focused SAXS/orchestrator
matrix and structured verifier are required before checkpointing.
