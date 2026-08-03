# SAXS Orientation AI Advisory Design

**Date:** 2026-08-03
**Status:** Approved for implementation planning
**Depends on:** stable Tasks 1-4 evidence contracts

## Goal

Let AI summarize and rank existing q-band orientation evidence for human review
without creating features, changing axes, applying masks or corrections,
overriding gates, rerunning analysis, or rewriting numeric results.

## Input boundary

Extend the existing sanitized SAXS 2D review context with a compact projection
of:

- candidate and track IDs;
- q bounds and neutral feature kind;
- final and diagnostic orientation summaries;
- stability and sensitivity summaries;
- correction-ledger statuses and digests;
- reference-axis kind and convention;
- reliability levels and reason codes;
- suspected-systematic metrics;
- existing scientific-review and publication gates.

Raw detector pixels, full q arrays, source paths, arbitrary unknown fields, and
calibration image contents remain excluded.

## Advisory output

Use a strict detached contract:

```text
OrientationAdvisoryReport
  schema_version
  ranked_candidate_ids
  candidate_observations
  comparison_summary_codes
  artifact_risk_codes
  recommended_review_action_codes
  limitation_codes
  source_evidence_digest
  status
  reason_codes
```

Every candidate ID must already exist in the sanitized context. Numeric q,
Herman, delta, stability, and sensitivity values are copied from source
evidence by deterministic code, not accepted from model output. Model output
contains only exact existing IDs plus allowlisted rationale and review-action
codes. Deterministic local code renders all explanations; free-form model text
is rejected.

## Authority boundary

The advisory has no apply path. It cannot produce `PreprocessCandidate`, call
the confirmed-rerun service, update config, edit a mask, supply a tensile axis,
activate calibration, change a quality level, or change publication state.
Existing SAXS AI rescue remains a separate candidate/confirmation workflow and
must reject orientation-advisory payloads.

Allowed review actions are non-mutating, such as inspect q band, verify tensile
axis, acquire background/standard data, inspect beam center, compare mask
sensitivity, or request scientific review.

## Failure behavior

- Missing or non-Trend evidence yields a limitations-first report, not a forced
  ranking.
- Unknown candidate IDs, invented numeric fields, unsupported actions, invalid
  schema versions, and digest mismatches are rejected.
- Model/network failure returns deterministic source-evidence summaries and an
  unavailable advisory status without changing analysis.
- AI disagreement with gates is recorded as text only and cannot promote data.

## Boundaries and tests

Extend sanitized review context and add a focused orientation advisory module.
Invoke it through a separate one-shot advisory worker and show it in the
existing Results review surface without an apply button or confirmed rerun
route. Persist only the detached report in the existing parameters JSON; do not
mark the run tuned, confirmed, reviewed, or publishable. Tests cover raw-data
exclusion, strict allowlists,
unknown-ID rejection, numeric source integrity, deterministic fallback,
prompt-injection strings, immutability, no candidate creation, no apply path,
GUI display, and persisted advisory audit records.

## Acceptance criteria

1. AI can rank only existing eligible candidate IDs.
2. All numbers in the report come from deterministic source evidence.
3. Advisory output has no mutation or rerun authority.
4. Missing/diagnostic evidence produces explicit limitations.
5. Existing rescue, review, quality, and publication gates are unchanged.

## Non-goals

- No AI parameter tuning for orientation calculations.
- No AI-generated tensile axis, mask, correction, q band, or physical label.
- No automatic acceptance, publication, or rerun.
