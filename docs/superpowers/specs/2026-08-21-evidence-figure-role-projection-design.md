# Evidence Figure Role Projection Design

**Date:** 2026-08-21

## Problem

`ProjectEvidencePackager._canonical_figure_assets()` currently assigns every
indexed figure the literal values `diagnostic`, `review_only`, and the first
evidence item's technique.  It discards the existing ARS figure-selection
intent.  Consequently an evidence package can label FTIR, SAXS, and WAXS
figures as DSC and offers no useful candidate layer for review.

## Decision

The immutable evidence package will project figure role from its declared
source, without inferring scientific eligibility from a filename or image.

1. A path selected in `FigureCandidateSet.main_candidates` becomes a
   `manuscript_candidate` index entry.
2. A path selected in `supporting_candidates` becomes a `supporting_candidate`
   index entry.
3. Every other direct run-output figure remains `diagnostic`.
4. Candidate entries retain `writing_eligibility: review_only` and candidate
   status `review_required`.  This is an editorial review queue, not a
   promotion of any scientific result.
5. A figure's technique is determined by the producing run/output relationship;
   only an unresolvable legacy-derived figure uses `UNKNOWN`.

The package will also preserve candidate group IDs where a candidate supplies
them.  Direct run-output figures have no invented group value.

## Non-goals

- Do not change analysis algorithms, metrics, citations, or Results/Discussion
  eligibility.
- Do not automatically select ordinary run-output figures as manuscript
  candidates when ARS has not selected a group.
- Do not rewrite existing immutable packages or raw data.
- Do not make direct ARS Matplotlib SVGs object-editable.

## Data flow

```text
run output -> per-run asset descriptor -> diagnostic index entry
ARS selected candidate path -> candidate descriptor -> candidate index entry
both -> deduplicate same logical SVG -> figure-index.json -> GUI / CLI / ARS
```

Candidate metadata has precedence only for an exact source asset path.  If a
candidate declares PNG/SVG siblings of one logical figure, the canonical SVG
entry receives the candidate metadata once.  All index asset paths remain
package-relative and the package remains an immutable snapshot.

## Failure behavior

- Conflicting roles for the same source asset fail package construction rather
  than silently selecting a stronger role.
- A candidate whose selected SVG was not copied fails package construction.
- If technique provenance cannot be resolved for a new direct output, it is
  represented as `UNKNOWN`, never copied from another run.

## Test and acceptance strategy

Focused package tests will first demonstrate the current incorrect all-
diagnostic/index-first-technique behavior.  The repair must prove one selected
FTIR group SVG is indexed as `manuscript_candidate`, a supporting SVG is
`supporting_candidate`, an unselected DSC output stays `diagnostic`, and the
three entries retain their distinct techniques.  Existing package-view and ARS
candidate tests confirm every consumer continues to read the shared DTO.

A fresh read-only PA6 replay is then inspected for per-technique labeling and
candidate count.  It does not alter raw inputs or make scientific claims.
