# Capability Execution Design

## Goal

Give every canonical one-dimensional measurement a finite, deterministic set
of compute items. A single item failure must not hide successful items from the
same measurement or source file.

## Scope

This slice adds a technique-neutral capability registry and executor and
attaches its item results to the shared `ComputeRun` contract. It does not
replace any existing DSC, IR, SAXS, WAXS, or NMR provider algorithm, and it does
not change GUI, CLI, Batch, or Codex entry points yet.

## Public model

`CapabilitySpec` declares one stable capability id, the canonical measurement
families it accepts, and a deterministic callable. `CapabilityRegistry` is a
closed registry; callers may request a finite subset by id, while the default
registry exposes the supported set explicitly. `CapabilityExecutor` iterates
measurements and capabilities and emits immutable `CapabilityItemResult`
values. Each item has a stable id derived from the canonical template hash,
measurement id, and capability id.

The first capabilities are intentionally low-risk, useful for every 1-D curve:

- `curve.summary.v1`: point count, x/intensity bounds, and intensity range.
- `curve.extrema.v1`: positions and values of the minimum and maximum intensity.

These are compute outputs, not manuscript classifications or scientific
conclusions.

## Failure semantics

- Unsupported family: `not_applicable` with `capability_family_unsupported`.
- Missing or malformed measurement data: `failed` with a stable reason code.
- Successful calculation: `completed` with finite JSON-safe values.
- Unknown requested capability: the request is rejected before execution.

One exception is isolated to its item. The executor never fabricates values or
uses a material label to select a capability.

## Shared run contract

`ComputeRun` gains an optional tuple of capability items. Existing constructors
remain valid. Completed runs may carry item results; non-completed runs may not.
Serialization includes `capability_items` and preserves the existing compute
boundary (no evidence or writing fields).

## Verification

Focused tests cover registry closure, deterministic results and ids, failure
isolation, JSON round-trip, and the unchanged legacy direct-run path.
