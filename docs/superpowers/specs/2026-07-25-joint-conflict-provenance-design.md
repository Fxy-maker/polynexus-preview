# Joint Conflict Provenance Design

## Goal

Make Joint disagreements auditable from the hub validation row and the
Manifest-backed figure recipe back to the exact technique runs that supplied
the values.

## Design

The existing `JointRunRecord` is already the authoritative run-relative
source. A small serializer will expose `run_id`, `technique`, `submodule`,
`created_at`, evidence status, evidence weight, and evidence reasons. The
dataset validation adapter will attach a `provenance.sources` mapping to every
validation row using the relevant technique set for each check: DSC/WAXS/SAXS
for crystallinity checks, DSC/SAXS for Tm-vs-structure, and SAXS for L
consistency. Missing runs are represented with `available: false`.

The figure provider will attach the same batch-row source mapping to every
figure recipe. This makes Main, SI, and diagnostic figures traceable without
recomputing validation or modifying figure values. No conflict is suppressed,
corrected, or promoted by this change.

## Testing and compatibility

Existing numeric validation and publication-role assertions remain unchanged.
New tests assert JSON-safe provenance content for a deliberate crystallinity
conflict and for all Joint figure recipes. The shared FigurePipeline tests
continue to prove that recipes survive Manifest publication.
