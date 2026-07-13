---
kind: decision
status: active
date: 2026-07-13
title: Keep DSC publication projection mode-specific and audit-compatible
---

## Context

The latest mainline shared figure contract does not expose the historical DSC
provider's display-order field or panel-label serialization, while DSC
publication acceptance requires deterministic Main/SI/Diagnostics ordering,
auditable `(a)`/`(b)` labels, and a 600-DPI TIFF asset.

## Decision

- `DSCEngine` passes its engine context to one mode-specific DSC provider and
  publishes only the resulting definitions through the shared manifest pipeline.
- Deterministic provider order is persisted in recipe metadata; panel labels
  are an optional `PanelDefinition.panel_label` field serialized into the
  existing document contract.
- DSC uses an additive `dsc_publication` output profile with TIFF support; the
  existing `paper_complete` profile remains unchanged for other techniques.
- The old sequence-based `build_dsc_figure_definitions(results)` entry remains
  available through an explicitly named compatibility module, but it is not
  used by the engine production path.

## Consequences

This keeps the DSC slice isolated from WAXS, SAXS, GUI streamlining,
Editor/Export, and AI preprocessing while preserving existing direct callers.
The shared panel-label/profile additions require architecture and publication
asset review before merge.
