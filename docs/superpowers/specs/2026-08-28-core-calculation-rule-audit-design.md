# Core calculation rule-tier audit design

## Purpose

Audit whether each rule in the shared analysis path is correctly classified as
one of: a structural calculation blocker, a calculable-result warning, or a
publication/evidence restriction. The purpose is to remove unjustified
scientific rigidity without inventing measurements or weakening requirements
that make a numerical result indeterminate.

## Scope

The audit covers DSC, FTIR, SAXS, WAXS, and NMR through this shared path:

```text
raw artifact -> canonical converter -> provider/Core -> ComputeRun
             -> evidence/writing metrics -> CLI/Agent/GUI presentation
```

It is read-only for source data and does not change algorithms, thresholds,
templates, output status, or publication eligibility in this phase.

## Rule tiers

| Tier | Meaning | Result behavior |
| --- | --- | --- |
| `structural_block` | A deterministic quantity cannot be formed: unreadable data, ambiguous axes/units, missing required coordinate, invalid array shape, or mathematically undefined denominator. | Stop that computation with a precise reason. |
| `calculation_warning` | A quantity can be calculated, but a quality, preprocessing, calibration, fit, or context limitation affects confidence or interpretation. | Keep the result, method, source, and warning. |
| `evidence_restriction` | A quantity is calculated and traceable, but cannot support an asserted Results claim without a missing scientific condition such as phase assignment, replicate support, or literature-backed attribution. | Keep it diagnostic/review-only in evidence and ARS input. |

The same rule may have a strict structural precondition and a later evidence
restriction. The audit must not collapse them into a single generic “blocked”
label.

## Audit record

Each discovered rule receives one ledger row with:

- technique and owning module/symbol;
- trigger and input domain;
- current Core/ComputeRun/evidence/GUI behavior;
- whether a finite deterministic result exists before the rule applies;
- current tier and recommended tier;
- rationale, including the mathematical or scientific dependency;
- source test, fixture, or replay evidence;
- follow-up action: retain, reclassify, split the rule, or investigate.

Rules are grouped by technique and then ordered with all potential
`structural_block -> calculation_warning` candidates first.

## Audit procedure

1. Map public canonical converters, provider entry points, `ComputeRun` result
   status, and writing-metric eligibility for each technique.
2. Search for fail/raise/block/gate/quality conditions in only those modules and
   trace each condition to its public result projection.
3. Compare the condition to a focused synthetic test or an existing real-data
   acceptance/replay record. Do not infer a condition from its name alone.
4. Identify whether the condition prevents a numerical calculation, only
   changes evidence eligibility, or is currently conflating both roles.
5. Check CLI/Agent and GUI consumers for disappearance or relabeling of warned
   values. They may not implement private technique policy.
6. Publish the ledger and a prioritized change proposal. No row changes tier
   automatically in this audit phase.

## Expected findings and boundaries

- DSC is the reference pattern: a calculable curve should produce values plus
  warnings; malformed arrays and undefined integrations remain hard blocks.
- FTIR material/assignment knowledge, SAXS/WAXS calibration/background/phase
  evidence, and NMR assignment/phase support require careful separation between
  calculation and manuscript promotion.
- Ambiguous input mapping remains a structural blocker until an explicit
  mapping is supplied; AI must not guess columns, units, or scientific values.
- Existing historical GUI, fixture, or ChartGallery failures are recorded as
  separate engineering issues unless they hide or misclassify a core result.

## Acceptance for the audit phase

- Every supported technique has a concise ledger section with observed rules
  and their current/resulting tier.
- Every recommended reclassification cites a code path and a test/replay
  observation; speculative recommendations are explicitly marked for further
  investigation.
- The report distinguishes “calculation was stopped” from “calculation exists
  but is diagnostic-only”.
- No raw artifact, numerical algorithm, quality threshold, material database,
  or evidence eligibility is changed by this audit.

## Follow-up decision

After human review, each approved candidate becomes a separate atomic change
with a regression test proving that the result is retained with warnings and
that the evidence layer does not silently promote it to a Results claim.
