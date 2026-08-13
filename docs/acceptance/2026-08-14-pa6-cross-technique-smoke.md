# PA6 Cross-Technique Smoke Acceptance

Date: 2026-08-14

## Scope

Read-only replay through the existing PA6 junctions selected three FTIR files
(`PA6-JW-100.csv`, `PA6-JW-110.csv`, `PA6-JW-120.csv`) and one WAXS file
(`PA6.raw`) into one temporary project:

`D:\PolyNexus-pa6-cross-technique-smoke-20260814`

No raw bytes were copied or modified. The project workflow executed three IR
steps and one WAXS step, then created one `review_required` evidence package.

## Result

The package contains:

- `relations.json` with explicit `cross_technique_evidence_set` membership;
- `techniques.json` indexing `ir` and `waxs` run IDs, statuses, evidence counts,
  and limitations;
- source hashes and derived provider assets under the immutable package.

The actual provider evidence remains review-bound. IR reported uncalibrated
diagnostic Xc indices and weak band-support warnings. WAXS reported Xc and
Scherrer size with low physical-support confidence. No cross-technique
scientific conclusion was generated.

## Verification

- Real replay: three IR provider steps plus one WAXS provider step, package
  status `review_required`.
- Focused entrypoint/package regression: `15 passed`.
- Structured quality/preprocessing gates: `303` / `157` passed.
