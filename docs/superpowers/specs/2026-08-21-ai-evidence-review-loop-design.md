# AI Evidence Review Loop Design

**Date:** 2026-08-21

## Problem

An evidence package can contain many technically valid logical figures but no
durable answer to four editorial questions: which figures answer the active
research question, which are supporting or diagnostic, which metrics are safe
for Results versus Discussion, and which evidence has a human reviewer
actually accepted.  Sending every figure directly to ARS risks an oversized,
unreviewable writing context and lets an agent mistake diagnostic evidence for
a paper claim.

The prior figure-index repair distinguishes explicit FTIR group candidates from
ordinary diagnostic figures.  It does not yet provide quality reports,
cross-technique candidate generation, reviewer decisions, or an ARS input
limited to confirmed evidence.

## Goal

Create a shared AI-first review loop for DSC, FTIR, SAXS, and WAXS:

```text
immutable evidence package
  -> deterministic review proposal
  -> Codex/ARS presents small review cards
  -> human review decision
  -> approved ARS writing input
```

The first complete vertical slice is FTIR. DSC, WAXS, and SAXS use the same
contracts and follow with technique-specific group-candidate providers.

## Non-goals

- Do not alter raw input, deterministic result values, completed runs, or an
  immutable evidence package.
- Do not auto-accept a figure, metric, scientific interpretation, or manuscript
  placement.
- Do not let an LLM replace canonical validation, figure provenance, or
  technique-specific science gates.
- Do not require a new GUI workflow for v1; Codex conversation is the primary
  human confirmation route.
- Do not create a universal scientific rule that every generated figure must
  become a paper candidate.

## Boundaries and objects

| Object | Ownership | Mutability | Purpose |
| --- | --- | --- | --- |
| Evidence package | Existing packager | Immutable | Raw evidence, limits, metrics, figure index, package hash |
| Review proposal | Review service | Immutable snapshot | Deterministic checks and AI-ready candidate queue for one exact package hash |
| Review decision | Human/Codex action service | Append-only revisions | Human placements, allowed/disallowed claims, notes, and rework requests |
| Approved writing input | Review service | Derived snapshot | Exact ARS context filtered by a review decision revision |

Review artifacts live under `.polynexus/reviews/`, not inside the evidence
package. Every review artifact stores `package_id`, `package_version`, and
`package_hash`. A package hash mismatch blocks decision application and ARS
handoff. Thus a changed analysis requires a fresh review rather than silently
reusing an old approval.

## Shared contracts

### `review-proposal.json`

Generated from `figure-index.json`, `writing-evidence.json`,
`citation-metrics.json`, `limitations.json`, and candidate manifests. It is
fully deterministic except for optional AI wording in `ai_rationale`; that
wording may not introduce a candidate, score, claim, or source link absent
from the deterministic proposal.

```json
{
  "version": 1,
  "package": {"id": "pa6", "version": 3, "hash": "..."},
  "question": "How does PA6 JW evolve with temperature?",
  "checks": {"policy_version": "review-checks.v1"},
  "candidates": [
    {
      "candidate_id": "review-figure-ftir_group_overlay",
      "figure_id": "ftir_group_overlay",
      "technique": "IR",
      "group_ids": ["ir:pa6-jw:temperature_C"],
      "suggested_placement": "results_candidate",
      "priority": 1,
      "quality": {"status": "review_required", "checks": []},
      "trace": {"svg": "figures/ftir_group_overlay.svg", "run_ids": [], "source_artifacts": []},
      "allowed_claims": [],
      "prohibited_claims": [],
      "reason_codes": []
    }
  ],
  "omissions": []
}
```

Allowed placements are `results_candidate`, `supporting_candidate`, and
`diagnostic`. They are proposals, not publication roles. A figure without an
explicit group candidate remains diagnostic unless a future technique provider
declares a bounded candidate. The proposal contains no `approved` state.

### `review-decision.json`

One review document may contain multiple append-only decision revisions for one
package hash. Its latest valid revision is authoritative. A Codex action or
future GUI action receives a compact decision, validates all IDs and package
hashes, then writes the revision atomically.

```json
{
  "version": 1,
  "package": {"id": "pa6", "version": 3, "hash": "..."},
  "revision": 2,
  "decisions": [
    {
      "candidate_id": "review-figure-ftir_group_overlay",
      "decision": "approved_results",
      "allowed_claim_ids": ["claim-..."],
      "note": "Curve labels and temperature grouping checked.",
      "reviewed_by": "human",
      "reviewed_at": "2026-08-21T...Z"
    }
  ]
}
```

Legal decisions are `approved_results`, `approved_supporting`, `diagnostic`,
`rework_requested`, and `not_used`. The service rejects unknown candidates,
duplicate latest decisions, unknown claim IDs, an automated reviewer identity,
and package-hash mismatch. Decisions cannot delete prohibited claims or turn a
`review_required` metric into a paper-ready result.

### `ars-approved-writing-input.json`

This is a derived, read-only handoff. It includes only `approved_results` and
`approved_supporting` decisions, their linked figure paths, citable metrics,
allowed claims, inherited prohibited claims, and reviewer notes. It retains
the original review state; ARS must phrase all review-bound conclusions
conditionally or ask for more evidence. It cannot include a figure or metric
merely because it ranked highly in the proposal.

## Automated checks and ranking

The review service records each check as `pass`, `warning`, `blocked`, or
`not_available`; `not_available` is never silently treated as pass.

1. **Asset integrity:** package-relative SVG and metadata exist, paths remain
   inside the package, and SVG is nonempty/parseable.
2. **Figure semantics:** axes, units, legends, and curve labels are read from
   structured figure metadata when available. Direct static group SVGs can
   report only what their generator declares; missing metadata is a warning.
3. **Duplication:** logical-figure index identity is authoritative. Near-visual
   or same-source duplicates are reported for review, not deleted or guessed.
4. **Traceability:** every proposed figure must map to its source run, raw
   artifacts, method/parameters, and relevant evidence/metric IDs. Missing
   links block Results/Supporting recommendation.
5. **Scientific boundary:** existing technique limits, disallowed conclusions,
   metric writing eligibility, and review-required state propagate unchanged.

Priority is a transparent ordered policy, not a black-box scientific score:

1. explicitly selected group candidate;
2. directly answers the active question and condition axis;
3. complete trace and no blocked quality check;
4. distinct from a higher-ranked candidate;
5. existing provider role (`main`, then `si`, then `diagnostic`) only as a
   tie-breaker.

The proposal records every reason code. An optional AI explanation may convert
these codes to natural language for Codex, but cannot alter their order.

## Codex-first human interaction

Codex reads the proposal and presents one technique/group card at a time, not
an unfiltered gallery. A card contains the suggested placement, one primary
figure and at most two supporting alternatives, check summary, trace links,
allowed/prohibited claim list, and a compact choice:

```text
Results / Supporting / Diagnostic / Do not use / Rework: <short note>
```

Codex turns the answer into a validated review-decision revision. It asks a
follow-up only for rework or an unrecognized response. A future GUI review tab
uses the same proposal/decision APIs and must not introduce private state.

## Technique candidate protocols

All candidates require an explicit selected group and a shared condition axis.
If the group lacks enough compatible data, the provider writes an omission
reason instead of fabricating a trend.

| Technique | Main candidate protocol | Supporting protocol | Mandatory limits |
| --- | --- | --- | --- |
| FTIR (first slice) | selected spectra overlay; metric trend only with finite same-method provider metric | local region/difference when explicit comparison is valid | uncalibrated IR crystallinity remains an index; assignment limits inherit evidence |
| DSC | same-program thermogram overlay; thermal-event or Avrami trend only for compatible canonical segments | per-hold fit and event table | scan direction, mass/baseline, canonical segment and fit limits |
| WAXS | selected profile overlay; one compatible peak/structure trend | full series and fit detail | background, peak assignment, calibration, and orientation limits |
| SAXS | selected I(q) overlay or condition trend only from quality-gated structural metric | Kratky/IDF/2D evidence | q calibration, background, geometry/mask, SNR, orientation and frame quality limits |

No new provider can promote metrics: it only exposes existing canonical values
and their existing safety status through the shared candidate contract.

## Phased delivery

1. **Shared review foundation:** DTOs, proposal builder, asset/trace checks,
   review decision validation, approved ARS input, CLI/Codex operations, and
   backward-compatible package reading.
2. **FTIR vertical slice:** adapt existing selected-group candidates, produce a
   review proposal, accept decisions, build approved writing input, and replay
   real PA6 JW data.
3. **DSC protocol:** canonical multi-program/isothermal group overlays and
   kinetics/thermal-event candidates with explicit compatibility gates.
4. **WAXS protocol:** profile/trend candidates and provenance-aware checks.
5. **SAXS protocol:** quality-gated group candidates, retaining all detector
   and structural diagnostics as non-promotable evidence.
6. **Four-technique acceptance:** one real PA6 package, bounded proposal queue,
   human decisions, ARS approved writing handoff, and no raw-data modification.

## Failure behavior

- Invalid/missing package index or package-hash mismatch blocks proposal,
  decision, and ARS handoff.
- A missing figure, metadata, or trace link yields a visible `blocked` check;
  it cannot be proposed for Results/Supporting.
- A technique provider without a group protocol supplies diagnostic entries and
  an omission reason only.
- Stale decisions are retained as audit history but are ignored for a new
  package hash.
- ARS handoff with no approved decisions succeeds only as an empty,
  explicitly `human_review_required` input; it produces no Results claims.

## Test strategy and acceptance

Focused tests precede each implementation change. The shared slice proves
package hash binding, path containment, no automatic approval, status
propagation, invalid-decision rejection, and ARS filtering. FTIR proves one
selected PA6 group moves through proposal, a human decision, and approved
writing input; an uncalibrated IR index stays discussion/diagnostic bound.
Each later technique proves group compatibility, candidate omission on unsafe
data, provenance, and unchanged algorithm outputs.

The final real PA6 acceptance must prove DSC/FTIR/SAXS/WAXS candidate queues,
diagnostic preservation, decision history, ARS approved-input filtering, and
read-only raw inputs. A full repository release-green claim remains separate
from this scoped evidence-loop acceptance.
