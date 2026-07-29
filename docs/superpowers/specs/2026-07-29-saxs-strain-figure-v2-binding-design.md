# SAXS strain Figure V2 binding design

## Decision

The strain provider will set `recipe["v2_adapter"]` to the existing
`"saxs_strain"` key at its final per-definition normalization boundary.  The
provider already sends every emitted Figure through `_ensure_display_order()`;
placing a default there covers main, sequence, excluded-frame, invariant,
correlation, IDF, azimuthal, phase, and low-q definitions without duplicating
adapter knowledge across optional recipe builders.

## Rationale

`polynexus.core.figures.v2_capabilities` already supports `saxs_strain` and
will construct a sidecar only after the shared V2 adapter and layout resolver
succeed.  The strain provider currently omits the adapter key, so otherwise
valid definitions report `not_configured` rather than entering that existing
fail-closed gate.  Binding the key repairs a lifecycle integration gap; it does
not create scientific data, approve a failed layout, or change publication
semantics.

## Boundaries

- Preserve each original recipe's inputs, parameters, source paths, evidence,
  publication role, display order, and data objects.
- Use `setdefault` so a future strain recipe that deliberately provides an
  explicit adapter is not overwritten.
- Preserve the existing capability behavior: malformed/unsupported definitions
  still return `static_fallback`, never a synthetic ready result.
- Do not touch analysis, quality, detector, orientation, AI/rescue, GUI, or
  test-storage code.

## Evidence design

Focused regression tests will:

1. build all definitions emitted by the existing strain fixture and assert the
   explicit adapter plus a `ready` V2 capability result;
2. run a representative definition through `FigurePipeline` and assert that
   the Manifest entry is ready and references a real V2 sidecar; and
3. leave the existing dirty detector/trace and Figure document coverage in the
   consumer matrix to verify the binding did not change their behavior.

The task additionally runs the structured verifier, the PowerShell-expanded
complete SAXS matrix, non-destructive storage audit, and a changed-file
allowlist checkpoint.  Scientific and human publication review remain outside
this integration-only task.
