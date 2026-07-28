# SAXS Acceptance Audit Surface Binding Design

**Date:** 2026-07-28
**Status:** approved working design for the active SAXS quality goal

## Problem

SAXS parameters now expose the existing read-only
`scientific_acceptance_audit`, while downstream review and export surfaces
still expose only selected quality records. A consumer can therefore lose the
explicit distinction between software validation, existing publication gates,
and human scientific review.

## Design

Use the audit snapshot already present in `result.parameters` as the only input
to three consumer bindings:

1. Workbench adds a presentation-only risk/next section derived from the
   existing `status` and `reason_codes`. It keeps the full mapping in the
   diagnostics payload and never changes `params`.
2. Figure providers pass the existing snapshot to
   `attach_saxs_figure_evidence()`, which stores a detached strict-JSON copy at
   `recipe.evidence.quality_provenance.scientific_acceptance_audit`. Existing
   quality provenance, roles, figure IDs, and source-frame mappings remain
   unchanged.
3. Export adds the same detached snapshot as
   `quality_evidence.json.scientific_acceptance_audit`, next to the existing
   static/temperature/strain records. The bundle-level quality file remains
   authoritative; figures retain only a compact reference/snapshot.

If the snapshot is missing or malformed, consumers omit the new field and keep
the legacy surface available. They never call a new analysis routine or infer
a positive gate. Strict JSON conversion remains the existing `_json_safe` or
`_jsonable` boundary.

## Data flow

```text
SAXS result.parameters.audit
        |----------------> Workbench advisory risk/next text
        |----------------> Figure recipe quality_provenance.audit
        `----------------> Export quality_evidence.json.audit
```

The audit remains explicitly `existing_gates_only`; it is not a publication
approval and does not alter existing physical or quality gates.

## Failure and compatibility

All three consumers are additive. Existing callers without an audit continue
to receive their prior payloads and figure definitions. The new mapping is
detached before serialization so later source mutation cannot change an
already-built figure or export payload.

## Testing boundary

Focused tests cover Workbench text and input immutability, Figure/Manifest
strict JSON and role preservation, Export strict JSON and manifest registration,
and absent-audit fail-closed behavior. The complete SAXS matrix, structured
verifier, diff check, and test-storage report are required before checkpoint.
