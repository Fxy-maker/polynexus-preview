# SAXS real data and Workbench acceptance design

## Scope

This acceptance slice validates the already implemented SAXS quality and
export contracts against the repository's real static, temperature, and strain
fixtures. It is an evidence and release-boundary task, not a scientific
algorithm change.

## Contract

Each real mode must be runnable through the existing engine entry point and
must preserve its existing validation result. A successful export must contain
`quality_evidence.json`, and `bundle_manifest.files.quality_evidence` must point
to it. The evidence payload is mode-scoped and may omit fields that do not
apply; omission is preferable to manufacturing a positive result.

The Results Workbench remains a presentation consumer. Its mode-specific
narrative and figure links must resolve against manifest IDs and fallback
candidates without moving scientific branching into GUI event handlers.

## Safety and scientific boundary

The replay writes only to temporary diagnostic roots. It does not overwrite
the source EDF files or the checked-in/generated fixture outputs. Existing
validation errors remain visible. No missing frame, quality state, physical
parameter, AI candidate, or publication role is inferred by the acceptance
runner.

Automated tests establish software and provenance invariants. They cannot
decide whether a real SAXS transition, orientation change, or rescue candidate
is scientifically defensible. That decision remains an explicit human gate.

## Acceptance flow

1. Replay the three real SAXS modes through the shared lifecycle test.
2. Replay and export all three modes to an external temporary directory.
3. Assert the mode-scoped quality evidence and manifest registration.
4. Verify the SAXS Workbench profiles and figure-link fallbacks.
5. Verify the post-restart launcher resolves the intended worktree and package.
6. Pause for rendered-GUI and scientific sign-off before release claims.

## Failure policy

If a mode has a validation error, the run may remain analytically inspectable
and exportable for audit, but it cannot be silently promoted to a stronger
publication role. If provenance or manifest generation fails, the acceptance
slice fails even when numerical analysis completed.
