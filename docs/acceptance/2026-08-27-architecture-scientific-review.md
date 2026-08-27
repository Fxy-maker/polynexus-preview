# Architecture and scientific review — 2026-08-27

## Scope

Read-only review of the shared `CanonicalTemplate → CapabilityItems →
ComputeRun` migration and the six-sample v003 evidence package. This review
does not modify raw data, relax quality gates, or authorize publication.

## Architecture findings

### A1 — High: directory hash contract drift

The canonical converter registry computes directory `source_sha256` from the
JSON array of entries alone, while Agent inspection, `RawArtifact`, and package
validation include the envelope `{"kind":"directory_manifest","entries":...}`.
The same directory therefore has different identities depending on the entry
point. This can make a directory template and its `ComputeRun` provenance
disagree. Required fix: one shared directory-manifest hashing helper used by
Registry, Agent, ComputeRun, and package validation, with a cross-entry test.

### A2 — Medium: package portability and self-containment

`manifest.json` records absolute external run-manifest paths. The package view
validates local package references but does not independently verify the
package hash/artifact hashes or load those external manifests. A moved package
is therefore not fully self-contained. Required decision: either copy validated
run manifests into a package-relative `runs/` area or explicitly define the
package as host-bound and make the portability limitation visible.

### A3 — Medium: GUI batch persistence is incomplete

Batch rows carry `compute_run` in memory, but the existing persistence path
stores only the selected single-run projection. Each batch row should persist
its shared run reference before legacy display fields are written.

### A4 — Capability coverage is intentionally incomplete

The v003 package has capability items for generic FTIR curves, but opaque SAXS,
WAXS, and DSC thermal-program templates have zero generic capability items.
This is a declared capability gap, not evidence of a failed provider run. Do
not fabricate capabilities from opaque bytes; add typed capability adapters in
a later task.

### A5 — Status semantics need documentation

Agent steps with a canonical template are projected as `review_required` even
when provider validation passes. This is conservative, but the distinction
between computation completion and scientific review must remain explicit in
CLI, GUI, and ARS contracts.

### A6 — High: package validation does not require the shared run projection

The packager validates `AnalysisRun`, evidence, and source hashes, but does not
require every step to contain a `compute_run` whose artifact, template, and
hashes agree with the recipe. A future manifest could therefore claim canonical
template hashes without carrying the shared `ComputeRun` object that produced
them. The migration contract should make that projection mandatory for migrated
entry points and validate it at package time.

### A7 — Medium: GUI still consumes legacy result objects

The GUI executes through `ComputeRunService` but immediately projects the run
back to the legacy provider result for plotting and tables. This is acceptable
as a compatibility bridge, but it means the GUI is not yet a pure
`ComputeRun` consumer. Legacy deletion is unsafe until the chart/table path
reads the shared result DTO directly.

## Scientific findings

### S1 — Critical: DSC Results projection is too permissive

The v003 package exposes 78 DSC Avrami metrics as `results_candidate`. The
projection includes `event_starts_at_segment_boundary` segments and a low-fit
PA12 segment (`Avrami_R2 ≈ 0.754`), and duplicates `best_avrami` with the same
segment values. Finite numeric values alone are not sufficient publication
criteria. Required fix: deterministic quality-aware filtering and explicit
deduplication; boundary-start or low-fit segments must remain review-only or
diagnostic until a scientific rule is approved.

### S2 — FTIR values remain diagnostic

The package provides traceable peak positions, widths, and counts, but they are
all marked `diagnostic_only` pending preprocessing/normalization confirmation
and reliable peak assignment evidence. This is appropriate for the current
data and should not be promoted automatically.

### S3 — SAXS/WAXS are auxiliary evidence in this replay

SAXS metrics remain diagnostic because background/q-star applicability is not
resolved. WAXS crystallinity and Scherrer size remain diagnostic because peak
support and amorphous partition constraints are not satisfied. These values
can inform Discussion hypotheses but should not be presented as primary Results
claims without a separate scientific decision.

### S4 — Package status is correctly review-required

All 261 evidence items require human scientific review. The package is a
deterministic evidence handoff, not an automatically approved manuscript data
set. ARS must consume the partitions and limitations, while a human decides
which candidate figures/metrics enter a paper.

### S5 — Important: confirmed cross-sample context is not in the package

The replay summary contains user-confirmed PA6/PA11/PA12 pairing and
JW/SW/hold semantics, but `ars-writing-input.json` does not carry that context.
Therefore ARS must not assume that files from different techniques represent
the same sample, batch, or treatment. Either include the approved context as a
provenance section or require ARS to request confirmation before cross-technique
claims.

### S6 — Presentation layer is not manuscript-ready

The package indexes 730 logical SVG figures, largely one per FTIR file, and all
are `diagnostic`/`review_only`. This is not duplicated provider execution, but
the gallery still needs candidate ranking and group-level filtering before it is
usable for human review or paper figure selection.

## Review disposition

Status: **blocked for architecture/scientific merge approval**.

Before merge or release claim:

1. Fix A1 and add the cross-entry directory identity regression.
2. Make A6 explicit by requiring and validating `ComputeRun` projections.
3. Fix S1 with an approved deterministic DSC eligibility rule and deduplication.
4. Decide A2 package portability, repair A3 batch persistence, and plan A7's
   legacy-result retirement.
5. Carry the approved cross-sample context into ARS (S5), then rebuild v003
   and rerun the evidence-view/readback checks.

The full repository boundary suite remains non-green due to known historical
GUI/chart/SAXS failures; no release-green claim is made.
