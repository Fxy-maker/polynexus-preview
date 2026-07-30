# IR Mapping Results Provenance Design

## Goal

Expose the already validated IR mapping evidence in the shared Results review
surface without changing scientific interpretation or publication gating.

## Design

`result_review_ir_support_block_text()` remains the single formatter for the
mapping provenance line. `ResultReviewPanelTexts` carries that formatted value
as `ir_support_text`; the MainWindow Results mixin renders it as a dedicated
wrapped evidence row. This keeps analysis semantics in the service layer and
keeps the GUI unaware of mapping algorithm state.

The formatter reads only the canonical
`analysis_evidence.feature_evidence.mapping_evidence` payload. It reports the
official Thermo/OMNIC Picta rule currently recorded by the project: X is the
column/`microscope_stage_x` axis in `um`, Y is the row/`microscope_stage_y`
axis in `um`, origin is `stage_home` at `(0, 0)`, ROI is the area-map boundary
or explicit ROI, and flattened order remains unknown without a vendor map.
The status remains `official_rule_sample_metadata_unverified`, so the mapping
stays review-required.

## Failure and verification behavior

Malformed or absent evidence produces the existing empty/`N/A` behavior. The
native regression uses the real `IRMappingResult.to_evidence()` envelope, so a
fixture cannot accidentally bypass the shared evidence contract. The route
also verifies Gallery, Editor, and Origin package export as existing shared
acceptance boundaries.
