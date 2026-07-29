# SAXS Partial Detector Heatmap Design

Date: 2026-07-29
Status: Approved working design for the current SAXS quality goal

## Goal

Allow the existing static and temperature diagnostic detector Figures to pass
through the production FigurePipeline when a source contains finite and
non-finite pixels, while rendering omitted detector cells as masked blank
areas and retaining the existing partial_nonfinite provenance.

## Non-goals

- Do not interpolate, pad, reshape, replace, or fabricate detector pixels.
- Do not modify detector sampling, analysis results, quality levels, physical
  gates, orientation evidence, AI/rescue behavior, or publication roles.
- Do not relax the default behavior for ordinary heatmaps.
- Do not change Manifest schema or invent a second detector provenance field.

## Contract

The static and temperature detector heatmap objects explicitly carry
allow_partial_detector_grid: true. The generic Matplotlib renderer accepts
missing coordinate cells only when that exact boolean is present. It keeps the
missing cells as NaN in the render matrix and passes the matrix through
np.ma.masked_invalid, so Matplotlib renders them as blank/masked regions.

Any heatmap without the explicit detector opt-in continues to raise the
existing "heatmap data does not form a complete regular grid" error. Duplicate
cells and empty data remain errors for all heatmaps, including detector
Figures.

## Production boundary

No new pipeline branch is needed. The existing FigureDocumentBuilder preserves
the object property, FigureRenderPlanBuilder preserves it in the render plan,
and FigureArtifactExportService uses the shared renderer for preview, SVG, PNG,
PDF, and TIFF. A partial detector Figure therefore becomes ready with the same
document, assets, and recipe provenance as a complete detector Figure.

## Verification

- Renderer regression proves explicit partial detector opt-in masks the missing
  cell and that the default path remains strict.
- Static and temperature FigurePipeline regressions prove a mixed finite/
  non-finite detector source produces a ready Manifest entry and exported
  assets, while persisted provenance remains partial_nonfinite.
- Run the structured verifier, focused Figure/SAXS matrix, exact SAXS matrix,
  git diff --check, and storage report/dry-run clean.
- Create one checkpoint using only the task-card allowlist.

## Known limitation

The resulting Figure is still diagnostic evidence only. Masked cells indicate
that no finite sampled pixel was available at that coordinate; they are not a
detector validation result, a reconstructed image, or publication authorization.
