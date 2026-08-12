# Project Technique Adapters V2 Acceptance

Date: 2026-08-13

V2 routes one indexed IR, WAXS, or SAXS input through the existing engines and
creates a project-local ARS evidence package. The external PA6 sources were
read through separate project `raw` junctions; no source data was copied or
modified.

## Real replay

- FTIR: `insu-FTIR/PA6/PA6-JW-180.csv`, run and package `review_required`.
- WAXS: `waxs/PA6.raw`, run and package `review_required`; provider reported
  four peaks, `Xc=58.1%`, and `D=9.1 nm` as review-bound output.
- SAXS: `saxs/PA6.edf`, run and package `review_required`; inventory retained
  `background_unknown` because absolute scattering background metadata is not
  established.

Each package contains source hashes, validated run manifests, derived figures
and tables, limitations, and `writing-input.md`. Same-named derived figures
are disambiguated by stable source identity and are never overwritten.

## Verification

- V2 project matrix: `25 passed`.
- Structured verifier: quality gate `303 passed`, preprocessing gate `157
  passed`, Ruff/compile/type baseline/diff checks passed.

## Boundaries

V2 deliberately supports one file or one existing directory input per route.
Multi-file sequence grouping, replicate semantics, and cross-technique package
relations are the V3 boundary. Results remain `review_required` evidence and
do not authorize manuscript conclusions automatically.
