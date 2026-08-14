# Canonical Figure Assets Design

**Date:** 2026-08-14

## Problem

A completed analysis currently writes several rendered representations of the
same logical figure: preview PNG, SVG, publication PNG, PDF, and sometimes
TIFF.  The evidence package recursively copies those outputs.  This makes a
package look larger and more complicated than the scientific evidence it
contains, and makes it easy for an AI or reviewer to mistake render formats for
different figures.

The simplification must not reduce the existing object-level Chart Editor.
The editor needs the persisted Figure Project document (`figure.pnfig.json`),
not a raster preview.  A bare SVG remains viewable but is only a static editing
fallback.

## Goal

For newly created evidence packages, represent each logical figure once through
one canonical, editable evidence set and one package-level index:

```text
figures/<figure-id>/
  figure.svg
  figure.pnfig.json
  data.csv or data.json
  metadata.json

figure-index.json
```

`figure.svg` is the only default rendered figure in an evidence package.  PNG,
PDF, and TIFF become explicit, on-demand publication exports.  GUI previews may
use transient local render caches but must not add PNG files to an immutable
evidence package.

## Non-goals

- Change scientific algorithms, computed metrics, canonical input conversion,
  or review eligibility.
- Migrate, rewrite, or delete historical packages or run output directories.
- Make SVG a substitute for structured data or provenance.
- Remove Chart Editor, Origin export, or Quick Analysis.
- Decide which manuscript figures a researcher ultimately selects.

## Shared Objects And Entry Points

This changes the shared **Chart**, **Export**, and **Evidence package**
contracts.

- Figure pipeline/export service produces profile-specific assets from the same
  Figure Project document and render plan.
- Project evidence packager consumes declared figure assets and materializes
  `figure-index.json`; it must not recursively promote every render format as a
  separate figure.
- GUI gallery, package view, and Chart Editor consume the index and the
  `figure.pnfig.json` object contract.  Object editing remains available when
  the document and capability report validate it.
- CLI, Codex, and ARS consume the same index plus structured data/metadata.
  They use SVG only for a requested visual review.

No consumer gets a private figure or provenance representation.

## Output Profiles

Two output purposes are explicit rather than inferred from file extensions.

### Evidence profile (default)

The default profile for a normal analysis run produces exactly the material
needed to inspect, edit, reproduce, and cite a logical figure:

| Asset | Purpose |
| --- | --- |
| `figure.svg` | Canonical visual rendering for GUI and optional visual review. |
| `figure.pnfig.json` | Editable Figure Project document with object model, data bindings, source run, revision, and export provenance. |
| `data.csv` or `data.json` | Structured plotted or derived data, selected according to existing figure data rules. |
| `metadata.json` | Figure role, technique/group/condition context, source runs, computation method, review limits, and data/document references. |

The SVG and document are produced atomically from one render plan.  Validation
still checks the asset set that this profile promises.  A local GUI thumbnail
may be rendered from SVG or the document into a cache directory, but it is not
an evidence-package asset and is disposable.

### Publication export profile (explicit command)

When the user selects a figure for a manuscript or an external journal format,
the existing publication route exports the requested format(s): PNG, PDF, and
where supported TIFF.  It uses the same frozen Figure Project revision and
records the requested format/profile in that export's provenance.

Publication export does not mutate an immutable evidence package and is not
run merely because a figure was analyzed.  Existing technique publication
profiles remain available as explicit export options; their legacy tests remain
valid for that route.

## Figure Index Contract

Each new package writes `figure-index.json` at its root and references it from
`manifest.json`.  It contains a version field and a `figures` array.  Every row
describes one logical figure, never one image format.

Required row fields:

```json
{
  "id": "stable-logical-figure-id",
  "role": "manuscript_candidate | supporting | diagnostic",
  "technique": "IR | DSC | SAXS | WAXS | NMR",
  "group": "explicit group id or null",
  "writing_eligibility": "Results | Discussion | review_only",
  "svg": "figures/<figure-id>/figure.svg",
  "document": "figures/<figure-id>/figure.pnfig.json",
  "data": "figures/<figure-id>/data.csv",
  "metadata": "figures/<figure-id>/metadata.json"
}
```

`group` and `writing_eligibility` may be unknown or review-bound, but they may
not be invented.  Their values are projected from the existing candidate,
evidence, and writing contracts.  A missing or unreadable required path makes
the new index entry invalid; consumers fail closed for object editing and do
not silently treat a broken document as editable.

The index is the package's figure discovery surface.  `figure-candidates.json`
continues to describe selection intent where it exists; the new index maps that
intent to one asset set.  Citation metrics and writing evidence continue to
link values to evidence IDs and source runs, rather than duplicating those
values inside the index.

## Packaging Rules

1. A package copies or materializes the declared canonical asset set for each
   eligible logical figure.
2. Packaging deduplicates by stable figure identity/document provenance, not
   by basename or extension.
3. A candidate figure is included once even when its source run has legacy PNG,
   SVG, PDF, or TIFF siblings.
4. Tables remain under `tables/` and are not represented as figures.
5. The package manifest counts logical figures separately from physical asset
   files, so reports do not imply that formats are figures.
6. Package creation remains immutable: no raw input is copied, and source run
   files are never modified.

## Compatibility

Old packages remain read-only and usable.  A package loader first prefers a
valid `figure-index.json`.  If it is absent, an adapter derives gallery/package
entries from existing manifest, candidate, and asset data without writing back
to the package.  Legacy multi-format entries continue to display and open in
the editor when they already have a valid `figure.pnfig.json`.

New consumers must accept both index-backed and legacy-derived entries.  New
packages do not create compatibility PNG/PDF copies simply to satisfy old
readers; those readers are updated at the same time.

## Editor And GUI Behavior

- Gallery and package views list logical figures from the figure index, with
  role, technique, group, and writing eligibility as metadata.  They do not
  list SVG/PNG/PDF variants separately.
- The GUI displays the indexed SVG directly where supported.  It may create a
  private cache thumbnail for fast scrolling.
- Opening a figure whose indexed document and capability report permit object
  editing continues to open Chart Editor in object mode.
- A legacy or external bare SVG opens viewable/static.  It may support limited
  annotations but must not claim editable axes, curves, legends, or provenance
  that it cannot recover.
- The existing explicit publication/export action is where the user requests
  PNG, PDF, or TIFF.

## Failure Behavior

- An invalid evidence asset declaration prevents that logical figure from being
  added to a new package; package construction reports the specific figure and
  missing/invalid asset.
- If a valid SVG exists but the document is invalid, viewing may remain
  available, while Chart Editor object mode is disabled with an explicit reason.
- Missing structured data or metadata invalidates the canonical evidence entry;
  AI/ARS must not cite it as a complete figure evidence object.
- A failed on-demand publication export leaves the evidence package unchanged
  and retains no partial publication group.

## Test Strategy

Focused tests precede implementation and cover:

1. Default evidence export creates SVG, `figure.pnfig.json`, structured data,
   and metadata, with no persisted preview PNG, PNG, PDF, or TIFF.
2. Explicit publication export still creates each requested legacy publication
   format and preserves its provenance/audit behavior.
3. Chart Editor opens an index-backed figure with a valid document in object
   mode and falls back safely for bare SVG or corrupt documents.
4. Project packaging emits one `figure-index.json` entry per logical figure,
   maps candidate references to package-relative canonical assets, and does
   not duplicate legacy siblings.
5. GUI package/gallery DTO and CLI/ARS package reader load the same index
   payload; old packages without an index use the read-only adapter.
6. Existing publication-profile and historical-package regressions remain
   covered at their respective boundaries.

## Acceptance Criteria

- New default evidence packages contain a single canonical visual per logical
  figure and no redundant persisted publication formats.
- Object-level Chart Editor behavior remains available through
  `figure.pnfig.json`.
- Publication formats are generated only after an explicit export request.
- GUI, CLI/Codex, and ARS discover the same logical figure list and
  package-relative references.
- Historical evidence packages remain viewable and editable where their stored
  Figure Project document already supports it.
- The focused producer, GUI, CLI/ARS, packaging, and compatibility tests pass,
  followed by the structured task verifier.

## Implementation Scope

This is one bounded architecture task: introduce the canonical evidence output
profile and index, update the shared consumers, and preserve legacy read-only
loading.  It does not redesign the scientific workflow or perform bulk storage
cleanup.
