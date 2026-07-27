# SAXS AI Rescue Figure/Manifest Provenance Design

## Goal

Bind the existing SAXS AI rescue audit to every generated SAXS
`FigureDefinition` as compact, detached provenance so a Manifest-backed figure
document can be traced back to candidate/decision/replay state.

## Scope

The existing engine attributes are passed through the existing figure-provider
boundary into `figure_evidence`. The evidence projector adds an optional
`ai_rescue` record under `recipe.evidence.quality_provenance` and preserves the
existing `quality_evidence_file` link. The record is a compact projection:

- plan: policy/automation flags, candidate IDs/count, and reason codes;
- decision: decision names, confidence/guard results, preservation flags, and
  `apply_allowed` as a raw decision field;
- replay: candidate ID, mode, run status, decision, and apply status;
- confirmed rerun: candidate/mode/phase, existing gate statuses, apply status,
  rollback reason, and identity hashes when present.

Raw q/I curves, detector arrays, full candidate configurations, and full result
objects are excluded. Non-finite values become JSON `null` and malformed
sections are omitted.

## Non-goals

- No AI call, candidate application, rerun, interpolation, or frame repair.
- No new physical/quality threshold or publication-role calculation.
- No replacement of authoritative Export `quality_evidence.json`.
- No Workbench or History logic change; those consume their already-public
  paths from the previous task.

## Invariants

- Existing FigureDefinition roles and frame selection are byte-for-byte
  unaffected except for the additive provenance mapping.
- An absent or malformed audit leaves the legacy figure definitions valid and
  produces no positive rescue claim.
- `apply_allowed` is never translated to accepted/applied/physically valid.
- Figure documents remain strict JSON-safe and detached from engine state.

## Verification boundary

Tests cover the provider-to-projection route, strict detached serialization,
malformed/absent audit handling, and FigurePipeline Manifest document
retention. Export's full audit remains covered by its existing tests.
