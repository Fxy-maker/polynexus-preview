# Native SAXS Strain Editor Selection Specification

## Goal

Ensure a manifest-backed Gallery opens the Chart Editor for the first usable
figure when the manifest begins with a diagnostic entry that has no assets.
This preserves diagnostic visibility while preventing an empty-path editor
request in the native SAXS strain route.

## Scope and boundaries

- The Gallery selection helper may choose only an already-emitted non-empty
  figure path from the current manifest entries.
- Existing ordering, preferred-path matching, publication roles, and manifest
  failure visibility remain unchanged.
- No figure generation, scientific role promotion, fallback analysis,
  interpolation, or new quality threshold is introduced.
- The Chart Editor contract remains unchanged; it still receives the selected
  Gallery entry and an existing path.

## Acceptance criteria

1. An assetless diagnostic entry does not become the initial selected entry if
   a later entry has a usable emitted asset path.
2. The selected path is the first usable path exposed by that entry.
3. Existing preferred-path selection behavior remains unchanged.
4. The native SAXS strain route opens an Editor and captures
   `saxs_strain_editor.png`.

## Safety invariant

The change is presentation-only. It does not alter SAXS analysis results,
publication roles, quality gates, or the active manifest.
