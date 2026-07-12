---
kind: decision
status: active
date: 2026-07-12
title: Keep normal gallery discovery manifest-only
---

## Decision

The normal PolyNexus result gallery reads only the active `RunFigureManifest`.
It must not automatically fall back to recursive legacy file discovery.

Historical output is handled by the explicit Historical Figure Recovery view.
Recovery entries are isolated from the active gallery, do not implicitly change
the active run, and expose only the capability and lineage evidence that can be
proven from the legacy files.

## Rationale

Automatic fallback would mix current and historical assets, weaken figure
identity and provenance, and make missing or incomplete manifests appear valid.
The existing recovery service already provides a safer boundary by classifying
legacy candidates as rebuildable, partially repairable, or static-only.

## Evidence

- `polynexus/gui/main_window_figure_mixin.py` keeps recovery in a separate view.
- `polynexus/gui/plot_gallery_service.py` returns no active entries when the
  active manifest cannot be read.
- `polynexus/core/figures/legacy_recovery.py` owns recursive discovery.
- Focused gallery/recovery/quality-gate tests pass: 50 passed.

## Revisit condition

Reopen this decision only for a demonstrated recovery gap or a migration
contract that supplies stable legacy identity, provenance, and capability data.
