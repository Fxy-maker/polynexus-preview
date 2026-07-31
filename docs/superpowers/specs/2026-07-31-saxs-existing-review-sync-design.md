# SAXS Existing Review Evidence Synchronization Design

## Goal

When a SAXS Workbench scientific review is saved after a Figure run already
exists, refresh the review evidence in the existing Figure documents selected
by the persisted manifest.

## Scope and non-goals

In scope:

- keep the current review record on `AnalysisResult.metadata` and in SampleDB;
- use the existing `figure_manifest.json` as the authoritative list of ready
  Figure documents;
- update only `recipe.evidence.quality_provenance.scientific_review` in each
  existing SAXS Figure document;
- preserve the existing frame, metric, detector, AI, audit, data-source, role,
  revision, and asset fields;
- project `saxs.1d` and `saxs.2d` review scope using the existing fail-closed
  source and status decisions.

Out of scope:

- rebuilding a Figure run or changing its data sources;
- changing Figure IDs, publication roles, quality levels, physical gates, or
  AI/rescue behavior;
- adding scientific approval state to the structural manifest schema;
- updating non-SAXS or legacy-recovery documents;
- interpolating, repairing, or inferring any SAXS measurement.

## Design

`SAXSEngine.sync_scientific_review_to_figures()` will obtain the current result's
manifest path and current frame views, then delegate to a core evidence-sync
service. The service reads the manifest, resolves only its ready, run-relative
document paths, classifies 1D versus detector/orientation 2D figures using the
existing figure evidence boundary, and computes review evidence from the
current source-linked frames. It atomically rewrites each valid document after
changing only the review evidence field.

The manifest itself remains structural and is not rewritten. Its ready entries
continue to point to the same documents, so consumers that read the manifest
and then the linked document see one consistent review snapshot. Missing,
malformed, scope-mismatched, source-mismatched, cancelled, or non-accepted
reviews remain represented by the existing fail-closed evidence and never
promote a Figure.

The GUI result-review handler will call the SAXS engine service after updating
the in-memory result. A missing engine, manifest, document, or malformed
provenance is a diagnostic sync failure only; the already-persisted review and
analysis result remain intact.

## Testing and acceptance

RED tests must first show that an existing Figure document remains without the
new review after only the current in-memory update. GREEN tests must prove:

1. accepted source-matched 1D review reaches an existing Figure document;
2. 2D review uses the 2D scope boundary;
3. mismatch/missing/cancelled review remains disallowed;
4. the manifest's entry paths, Figure ID, role, revision, data sources, and
   unrelated provenance remain unchanged;
5. malformed or missing files do not raise through the Workbench save route;
6. a subsequent Export sees the same review evidence without changing the
   structural manifest.

No test treats evidence projection as human scientific approval.
