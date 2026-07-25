# IR Lifecycle Closure Design

## Goal

Prove the shared lifecycle for IR standard, temperature-2D, and mapping/ROI
modes while preserving the explicit typed mapping handoff boundary.

## Scope and non-goals

Use completed `IRResult`, `IRTemp2DResult`, and `IRMappingResult` DTOs to verify
provider publication, active Manifest/Gallery, editor revisions, export
provenance, and History restore. Do not add a vendor reader, infer coordinate
semantics, select a crystallinity band, or recalculate IR science in GUI code.

## Design

Each mode publishes through the existing IR FigureDefinition provider and
`FigureProductionPublisher`. The first Main entry is saved and republished by
`FigureProjectService`; the Gallery is reloaded from the active manifest after
each revision. Export copies the run tree and active pointer. A Qt history
record carries the mode and a real temporary source path, then checks that
MainWindow restores the same active Gallery and submodule.

Mapping assertions additionally retain `recipe.provenance.source_id` and
invalid-pixel diagnostics. No normal Gallery fallback or legacy `Fig-IRT*`
discovery is introduced.

## Verification

Run the new three-mode lifecycle regression with existing IR provider,
temperature, mapping, export, and history tests, then the structured verifier
with an external pytest basetemp.
