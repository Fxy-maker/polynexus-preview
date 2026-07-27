# Results Workbench Diagnostic Navigation Design

## Goal

Make the existing diagnostic Figure Pack reachable from every structured
Results Workbench profile. A user selecting a diagnostic link must be routed to
the first matching diagnostic figure in the active manifest Gallery, including
frame-indexed figure families whose exact index is only known after analysis.

## Scope

- Extend `WorkbenchFigureLink` with deterministic prefix candidates in addition
  to its existing exact candidates.
- Add one diagnostic link to every structured profile: SAXS static/temperature/
  strain, DSC standard/isothermal/non-isothermal, WAXS static/temperature/
  strain, IR standard/temperature-2D/mapping, NMR liquid/solid H/C, and Joint.
- Route exact IDs first, then the lexicographically first available ID matching a
  configured prefix. Existing exact fallback behavior remains unchanged.
- Add focused contract and routing regressions, including a frame-indexed
  diagnostic family.

## Non-goals

- No scientific calculation, evidence level, publication role, or threshold
  changes.
- No automatic promotion of diagnostic figures to Main or SI.
- No recursive filesystem discovery and no bypass of the manifest-only Gallery.
- No wildcard expansion outside the active Gallery's already-loaded figure IDs.

## Design

`WorkbenchFigureLink` keeps `key` and `alternatives` as exact manifest IDs and
adds `prefixes` as an immutable tuple of manifest-ID prefixes. Its resolver
accepts the Gallery's current ID set, checks exact candidates in declared order,
then checks prefix matches in sorted order. A link with no available match still
emits the existing requested key, preserving the current no-op behavior of the
Gallery selection route.

Profiles declare stable diagnostic IDs where providers have them, and a prefix
where providers emit frame-indexed diagnostics. Examples are
`dsc.standard.integration.diagnostic`, `joint.series.coverage`, and
`nmr.frame.deconvolution.`. The link role is `diagnostic`; this is navigation
metadata only and does not change the FigureDefinition publication role.

## Data flow

`ResultsWorkbenchProfile -> WorkbenchFigureLink.resolve(active Gallery IDs) ->
ChartGallery.select_figure -> existing manifest-backed Editor route`.

The results panel remains presentation-only. MainWindow continues to own
Gallery selection and does not inspect technique-specific analysis state.

## Acceptance

- Every structured profile exposes exactly one diagnostic link with role
  `diagnostic` and a real provider ID or explicit provider-ID prefix.
- Exact candidates win over prefix matches; prefix matches are deterministic.
- A real frame-indexed diagnostic ID can be selected from the Workbench without
  fabricating an ID or scanning outside the active Gallery.
- Existing SAXS fallback routing and all current profile/table/panel tests stay
  green.
