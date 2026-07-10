# Unified Figure Artifact Lifecycle Design

**Date:** 2026-07-10
**Status:** Approved design
**Scope:** SAXS, WAXS, DSC, IR, NMR, result gallery, ChartEditor, export, and legacy recovery

## Goal

Establish one system-wide figure contract so every PolyNexus technique produces, registers, previews, edits, publishes, and recovers figures through the same lifecycle.

The completed system must provide:

- one figure-definition contract across all techniques
- one global output profile per analysis run
- one directory and naming convention
- one run-scoped manifest
- one editable-document model
- one render plan for preview, editing, and publication assets
- one capability decision used by both the gallery and editor
- one atomic publish operation for SVG, PNG, and PDF
- one explicit recovery path for historical outputs

The objective is not merely to make more figures editable. The objective is to remove competing truths between analysis engines, exported files, the gallery, and the editor.

## Why A System-Level Design Is Required

The current output system is inconsistent at several boundaries:

- global configuration declares PDF while most technique configurations default to SVG
- SAXS uses `figure_format` while other techniques use `fig_format`
- SAXS hard-codes many PDF paths instead of honoring a shared profile
- SAXS uses `summary/` and `per_frame/` while other engines primarily use `figures/`
- naming conventions mix forms such as `Fig_1`, `Fig-W1`, `Fig_U1`, and `temperature_overview`
- technique modules directly choose paths, formats, DPI, and save behavior
- old files remain discoverable and can be mixed into a newer analysis run
- a `.pnfig.json` document may declare several supported formats even when only one was produced
- the gallery infers identity, category, and capability from filenames and neighboring files
- gallery state and editor-entry state are computed by different logic
- valid analysis data can exist without a discoverable editable relationship to the displayed figure

These are symptoms of the same architectural problem: each subsystem owns part of the figure lifecycle, but no subsystem owns the lifecycle contract.

## Scope

### In scope

- unified figure contracts and provider interface
- global output profiles and format roles
- stable figure identity
- standardized run and figure directories
- run-scoped figure manifest
- data snapshots and portable references
- multi-panel and multi-axis layout representation
- shared render planning
- atomic artifact-group publication
- gallery discovery and state
- editor open, save, publish, and copy semantics
- reanalysis and compatible style inheritance
- historical-output diagnosis and recovery
- cross-technique validation and CI enforcement

### Out of scope

- extracting numerical curves from arbitrary raster or PDF files
- guaranteeing object editing for an object type or layout that has no renderer
- journal-specific submission portals
- automatic insertion into external Word, WPS, or LaTeX processes
- persistent cross-session undo history
- silently rewriting historical runs in place

## Design Principles

### 1. One contract, many scientific providers

Technique engines define scientific content. Shared infrastructure defines storage, rendering, publication, identity, and lifecycle behavior.

### 2. FigureDocument is the editable truth

PNG, SVG, and PDF are derived assets. No exported file determines figure identity or editing capability.

### 3. RunFigureManifest is the run-index truth

The manifest decides which figures belong to a run. Directory scanning is a legacy-recovery tool, not a normal gallery-discovery mechanism.

### 4. Data sources are the numerical truth

Editable curve objects reference validated data snapshots with explicit columns and units. They do not depend on recovering data from rendered assets.

### 5. The same render plan drives every visible representation

Gallery preview, editor first screen, SVG, high-resolution PNG, and PDF must derive from the same document revision and render plan.

### 6. Formal outputs are complete asset groups

A new SVG, old PDF, and missing PNG must never be presented as one current publication version.

### 7. Fallbacks are explicit

Static-background or read-only operation is acceptable when the reason is visible. False object-editing promises are not acceptable.

## Considered Strategies

### Single global format only

Every figure would be emitted as one selected format.

Advantages:

- simple output directories
- easy uniformity checks

Disadvantages:

- no single format serves gallery preview, Word/WPS insertion, vector editing, and LaTeX equally well
- changing writing workflow requires regenerating all figures

### Always generate every known format

Every figure would always generate PNG, SVG, PDF, TIFF, and other supported forms.

Advantages:

- maximum immediate availability

Disadvantages:

- unnecessary files
- unclear asset roles
- future formats would automatically expand every run

### Role-based artifact contract with a run-level profile

Each artifact has a stable role, and one global profile determines which formal formats every figure in a run must contain.

Advantages:

- consistent across techniques
- supports Word/WPS and LaTeX without confusing artifact identity
- permits stricter or lighter profiles later
- keeps preview caches separate from formal outputs

Disadvantages:

- requires a shared pipeline and migration of existing engines

### Decision

Use the role-based artifact contract with a run-level profile.

## Default Output Profile

The default profile is `paper_complete`.

| Role | File | Requirements | Primary use |
|---|---|---|---|
| UI preview | `preview.png` | low-resolution, fast-loading, internal | gallery and history previews |
| vector master | `figure.svg` | editable text where supported | Word/WPS and vector editing |
| publication raster | `figure.png` | 600 DPI, fixed physical geometry | universal Word/WPS insertion |
| LaTeX/publication vector | `figure.pdf` | vector-oriented, embedded font policy | LaTeX, printing, submission |
| editable source | `figure.pnfig.json` | normalized FigureDocument | ChartEditor |
| numerical source | `data/*` | CSV or NPZ with schema metadata | reproducibility and object editing |

PDF remains part of the complete profile but is not the primary gallery preview or editing source.

Additional profiles may include:

- `word_standard`: SVG, 600 DPI PNG, internal preview
- `latex_standard`: PDF, SVG, internal preview
- `raster_submission`: 600 DPI PNG or TIFF, internal preview

Within one run, all ready figures must satisfy the same selected profile. Technique modules cannot override it.

## Global Configuration

Format and publication configuration moves out of technique configurations into one global structure:

    {
      "figure_output": {
        "profile": "paper_complete",
        "preview_dpi": 150,
        "publication_png_dpi": 600,
        "svg_font_policy": "editable_text",
        "pdf_font_policy": "embedded",
        "background": "white",
        "atomic_publish": true
      }
    }

Technique-level `fig_format`, `figure_format`, and publication DPI fields are removed after migration. Technique configuration remains responsible only for scientific analysis and plot-content parameters.

## Truth Model

The system has four non-competing truths:

1. `RunFigureManifest`
   - identifies figures belonging to one analysis run
   - records status, revision, assets, and capability results

2. `FigureDocument`
   - records editable objects, layout, styles, data references, and recipe
   - owns the working figure revision

3. `DataSourceSnapshot`
   - records the numerical data behind plot objects
   - includes column names, units, types, hashes, and relative paths

4. `FigureAssetGroup`
   - contains derived preview and formal publication files
   - records the published document revision

No exported asset may replace the responsibilities of the manifest, document, or data snapshot.

## Stable Figure Identity

Figure identity is semantic and independent of filename or export format.

The canonical form is:

    <technique>.<scope>.<figure_type>[.<instance>]

Examples:

    saxs.series.overview
    saxs.series.waterfall
    saxs.frame.001.scattering_profile
    waxs.series.crystallinity
    dsc.frame.003.full_curve
    ir.frame.001.spectrum
    nmr.series.crystallinity

Rules:

- use lower-case stable tokens
- an instance is required only when more than one figure of the same semantic type exists in the same scope
- frame instance IDs come from source identity or a stable run-local frame key, not display labels
- temperature, strain, sample label, and human title live in metadata
- exported filenames never define figure IDs
- format variants share the same figure ID and asset group
- a copied figure receives a new figure ID and lineage reference

## Standard Directory Layout

Each analysis run is isolated:

    polynexus_output/
    └── runs/
        └── <run_id>/
            ├── figure_manifest.json
            ├── run_metadata.json
            └── figures/
                └── <figure_id>/
                    ├── figure.pnfig.json
                    ├── data/
                    │   ├── plot_data.csv
                    │   └── data_schema.json
                    └── assets/
                        ├── preview.png
                        ├── figure.svg
                        ├── figure.png
                        └── figure.pdf

Directory layout is not used to infer category. Category is explicit manifest metadata.

FigureDocument and manifest paths must be relative to the run root. Absolute workstation paths are prohibited in persisted portable state.

## Gallery Categories

Stored figure categories are:

- `series_overview`
- `per_frame`
- `diagnostic`
- `supplementary`
- `legacy`, used only by recovery views

`All` is a UI filter, not a stored category.

The old `Other Exports` category is retained only as a temporary compatibility mapping during migration. New providers must use an explicit semantic category.

## FigureDefinition Contract

Technique modules return a normalized definition instead of saving files:

    FigureDefinition(
        figure_id="saxs.series.waterfall",
        technique="saxs",
        scope="series",
        category="series_overview",
        title="Scattering Waterfall",
        layout=...,
        data_sources=...,
        objects=...,
        recipe=...,
        style_profile="sci_default",
    )

Required fields:

- `figure_id`
- `technique`
- `scope`
- `category`
- `title`
- `layout`
- `data_sources`
- `objects`
- `recipe`
- `style_profile`

Generated object-mode definitions must include numerical data sources for every data-bound object. Static-background definitions may instead reference a portable background asset and have no numerical data source.

Technique providers may define:

- scientific series and derived objects
- axis labels, units, and scales
- panel composition
- semantic titles and captions
- recommended scientific style tokens
- data-source extraction from analysis results

Technique providers may not define:

- final output extension
- output directory
- final filename
- publication DPI
- asset-role mapping
- manifest paths
- save and overwrite behavior

## TechniqueFigureProvider Interface

Every technique implements the same provider interface:

    class TechniqueFigureProvider:
        def build_figures(
            self,
            analysis_result,
            context,
        ) -> list[FigureDefinition]:
            ...

The analysis orchestrator calls the provider and passes the resulting definitions to the shared figure pipeline.

Existing `generate_all_figures()` functions are compatibility sources during migration and are removed from the formal production path when their technique is migrated.

## Layout Contract

Multi-panel structure is first-class state, not a label stored in a style dictionary.

The layout model contains:

    Layout
    ├── canvas
    │   ├── width
    │   ├── height
    │   └── unit
    ├── grid
    │   ├── rows
    │   ├── columns
    │   └── spacing
    ├── panels[]
    │   ├── panel_id
    │   ├── grid_position
    │   ├── axes[]
    │   └── legend
    └── objects[]
        └── panel_id

Every rendered object must resolve to a panel and, where relevant, an axis.

The contract must represent:

- single-axis figures
- multiple series
- grid-based multi-panel figures
- twin axes
- colorbars
- legends scoped to a panel or figure
- image and heatmap layers
- normalized, data, axes, and canvas coordinate systems

Object editing is enabled only for layouts and object types supported by the current renderer.

## Shared Figure Pipeline

The shared pipeline contains:

1. `FigureDefinitionValidator`
2. `FigureDataSnapshotWriter`
3. `FigureDocumentBuilder`
4. `FigureRenderPlanBuilder`
5. `FigureArtifactExporter`
6. `FigureArtifactInspector`
7. `FigureCapabilityResolver`
8. `RunFigureManifestRepository`

### FigureDefinitionValidator

Validates:

- stable ID syntax and uniqueness
- category and scope values
- panel, axis, object, and data-reference integrity
- required units and column metadata
- recipe identity
- profile-independent geometry

### FigureDataSnapshotWriter

Writes reproducible data snapshots:

- CSV for tabular series
- NPZ for large matrices when appropriate
- explicit data-schema metadata
- relative document paths
- content hashes

### FigureDocumentBuilder

Builds the normalized FigureDocument and records:

- schema and renderer versions
- run ID, figure ID, and revision
- layout and object hierarchy
- data-source references
- recipe and scientific provenance
- working and published state

### FigureRenderPlanBuilder

Converts a FigureDocument into the only render plan used by:

- gallery preview
- editor first screen
- live editor redraw
- SVG export
- PNG export
- PDF export

Format writers do not independently reinterpret layout.

### FigureArtifactExporter

Renders the selected output profile into temporary paths and does not mutate official asset pointers until inspection succeeds.

### FigureArtifactInspector

Checks:

- existence and readability
- required formats
- physical canvas geometry
- PNG pixel dimensions and DPI
- SVG viewBox and text policy
- PDF page geometry and font policy
- render-plan and document revision identity
- artifact hashes

### FigureCapabilityResolver

Produces one capability report consumed by both gallery and editor. Editing capability, preview health, and publication completeness are separate fields so a missing PDF cannot incorrectly downgrade a valid data-bound figure to static editing.

### RunFigureManifestRepository

Writes the final run manifest only from validated staged results and atomically activates the completed run.

## Single Render Plan Rule

The visible flow is:

    FigureDocument
        ↓
    FigureRenderPlan
        ├── Gallery Preview
        ├── ChartEditor
        ├── SVG
        ├── 600 DPI PNG
        └── PDF

The gallery must not show an unrelated historical export and then ask the editor to approximate it.

Preview-to-editor consistency is guaranteed structurally because both representations use the same render-plan revision.

## Run Generation Flow

1. create a new immutable `run_id`
2. create a staging directory
3. ask each active technique provider for FigureDefinitions
4. validate all definitions
5. snapshot referenced data
6. build FigureDocuments
7. build render plans
8. generate required preview and formal assets
9. inspect the asset groups
10. resolve capabilities
11. write manifest entries for ready or explicitly failed figures
12. atomically commit the run manifest and active-run pointer
13. refresh the gallery from the manifest

Historical files are never used to fill missing current-run entries.

## RunFigureManifest Contract

The manifest records:

    {
      "schema_version": 1,
      "run_id": "...",
      "technique": "saxs",
      "output_profile": "paper_complete",
      "figures": [
        {
          "figure_id": "saxs.series.waterfall",
          "category": "series_overview",
          "document": "figures/.../figure.pnfig.json",
          "data_sources": ["figures/.../data/plot_data.csv"],
          "assets": {
            "preview": ".../preview.png",
            "svg": ".../figure.svg",
            "png": ".../figure.png",
            "pdf": ".../figure.pdf"
          },
          "capability_report": {
            "editing_mode": "object",
            "object_editing": true,
            "static_annotation": true,
            "reason_code": ""
          },
          "publication_status": "complete",
          "status": "ready",
          "working_revision": 1,
          "published_revision": 1
        }
      ]
    }

The manifest also records profile version, generator version, timestamps, hashes, and failure summaries.

## Capability Resolution

Object editing requires all of the following:

- valid FigureDocument schema
- resolvable and validated data sources
- supported object types
- supported panel and axis layout
- one render plan for preview and editor
- matching run, figure, and revision identity
- a successfully rendered current working preview

Publication status is evaluated independently:

- `complete`: every formal asset required by the profile exists for `published_revision`
- `unpublished_changes`: a newer working revision exists while the previous publication group remains complete
- `needs_repair`: the current publication group is missing, unreadable, or revision-inconsistent
- `not_published`: the figure has never been published

Example downgrade:

    {
      "editing_mode": "static_background",
      "object_editing": false,
      "reason_code": "unsupported_twin_axis_layout",
      "message": "The current renderer does not yet support twin-axis object editing."
    }

The report is computed once by the shared resolver and passed through the manifest entry. Gallery badges, card actions, editor mode, and capability messaging use the same report. Publication state is displayed alongside, but does not redefine editing mode.

## Gallery Behavior

The normal gallery:

- reads only the selected run manifest
- defaults to `Series Overview`
- groups by logical figure, never by export file
- uses the manifest preview role
- shows editing and publication state
- exposes assets only after figure selection
- never recursively scans the output root

Each card shows:

- logical title
- category and context
- object/static/read-only mode
- published/unpublished/repair state
- revision

Legacy discovery is a separate recovery surface.

## Editor Entry Behavior

### Object mode

Card activation opens ChartEditor directly with:

- the manifest entry
- FigureDocument
- matching render-plan revision
- capability report

Canvas, object tree, property panel, and selection state use one node identity.

### Static-background mode

Card activation opens preview first and clearly explains the downgrade reason.

Static mode supports annotation, crop, overlay, and export. It does not expose unsupported curve, axis, or legend controls.

### Broken or incomplete state

The UI displays the actual failure:

- missing data source
- missing document
- missing asset
- incomplete profile
- unsupported renderer
- revision mismatch

The user may repair, regenerate, or retain a static version. The system does not silently substitute an old file.

## Save, Publish, And Copy Semantics

### Save Edits

- writes a new working FigureDocument revision
- updates the internal preview
- preserves the previous complete formal asset group
- marks the card as having unpublished changes

### Publish

- renders every formal asset required by the active profile
- inspects the temporary asset group
- replaces the official group only when all hard requirements pass
- updates `published_revision`

### Save As Copy

- creates a new figure ID
- records lineage to the source figure
- copies or references data according to the copy policy
- never overwrites the source figure

The working revision and published revision remain distinct. A publication asset group is always complete even when newer working edits exist.

## Word, WPS, And LaTeX Usage

For Word/WPS, the asset panel prioritizes:

1. copy SVG
2. copy 600 DPI PNG
3. open containing directory
4. export copy

PNG is the compatibility fallback when the target Word/WPS version cannot preserve SVG behavior.

PDF is shown under LaTeX or additional formats and supports:

- copy PDF path
- copy a `\includegraphics{}` snippet
- export a LaTeX figure package

TIFF remains an optional profile format for journals that require it; it is not part of the default complete profile.

## Reanalysis And Style Inheritance

Reanalysis creates a new run ID. It never mutates the historical run.

Compatible inheritance rules:

- pure styles such as color, font, line width, and canvas size may be inherited automatically
- visibility, ordering, and legend placement may be inherited only when object IDs and layout remain compatible
- data-coordinate annotations may migrate only when their target objects still exist
- pixel-coordinate annotations, crops, and static overlays do not migrate automatically
- numerical values, fits, and analysis-derived objects always come from the new run

The system reports what was and was not inherited.

## Historical Output Recovery

Historical files live in a separate legacy view and never enter the active-run gallery automatically.

### Fully rebuildable

Required evidence:

- source or analysis data
- recognized recipe or figure type
- sufficient technique context

Action:

- rebuild as a new run through the unified pipeline

### Static only

Condition:

- only rendered PNG, SVG, or PDF remains

Action:

- import as a static-background FigureDocument

The system does not claim curve-level editing.

### Partially repairable

Examples:

- document and data exist but one asset is missing
- preview is missing
- manifest is missing but complete documents remain

Action:

- regenerate missing assets or rebuild the manifest without rerunning scientific analysis

Historical files are not deleted or modified in place.

## Atomicity And Failure Policy

### Per-figure atomicity

Initial run generation stages and validates the document, data snapshots, preview, and required publication assets as one figure project.

A later `Save Edits` operation atomically commits only the new working document revision and its internal preview. It never partially updates the formal publication group.

A later `Publish` operation atomically commits the complete set of formal assets required by the active profile and then advances `published_revision`.

Publish failure:

- leaves the previous official asset group unchanged
- leaves `published_revision` unchanged
- records structured failure details

### Per-run atomicity

A run may complete with some failed figures, but every expected figure is represented explicitly.

Example:

    12 figures ready
    1 figure generation_failed
    0 figures silently missing

Failed figures appear in a generation-problems surface and are not represented by historical substitutes.

Static-background figures may satisfy the SVG and PDF format roles by embedding their raster background. The inspector must record `vector_fidelity: raster_embedded` and surface a warning; the system must not describe those files as true vector content.

### Failure levels

- `ERROR`: prevents figure-project or publication commit
- `WARN`: permits commit with visible warning
- `INFO`: records normal generation and inspection metadata

## Migration Strategy

Use contract-first strangler migration.

### Rejected: big-bang replacement

Replacing every output module at once creates excessive regression and diagnosis risk.

### Rejected: permanent dual track

Keeping old and new output systems indefinitely preserves competing truths.

### Selected sequence

1. freeze contracts, profiles, manifest, and directory rules
2. build the pipeline, exporter, inspector, capability resolver, and manifest repository
3. migrate a simple IR spectrum vertical slice
4. migrate SAXS temperature workflows to validate series, per-frame, heatmap, and multi-panel behavior
5. migrate WAXS, DSC, and NMR
6. switch the gallery to manifest-only discovery
7. switch ChartEditor preview and publish to the shared render plan
8. add legacy diagnosis and recovery
9. remove old formal `generate_all_figures()` and direct-save paths
10. enable CI enforcement against reintroducing technique-owned output behavior

Compatibility adapters may exist only while a specific technique is being migrated. Each migrated technique closes its old production output path.

## Implementation Planning Boundary

This document is an umbrella architecture and is intentionally broader than one safe implementation plan.

Implementation is decomposed into bounded plans:

1. shared contracts, profiles, data snapshots, manifest, and pipeline foundation
2. IR vertical slice plus SAXS temperature vertical slice
3. WAXS, DSC, and NMR provider migration
4. manifest-only gallery and shared-render-plan editor integration
5. legacy recovery, removal of old output paths, and final CI enforcement

The first implementation plan covers only the shared foundation and the minimum IR vertical slice required to prove the contract. Later plans must use the acceptance gates in this design and may not redefine the approved contracts without updating this specification.

## Validation Strategy

### Contract tests

- stable and unique figure IDs
- valid categories and scopes
- complete panel, axis, object, and data references
- explicit data column names, types, and units
- relative persisted paths
- recipe and provenance presence

### Cross-technique integration tests

Run real fixtures for SAXS, WAXS, DSC, IR, and NMR and verify:

- one manifest per run
- one FigureDocument per ready figure
- complete `paper_complete` asset groups
- identical directory and naming conventions
- no technique-specific missing format

### Geometry and render consistency tests

- preview, editor, SVG, PNG, and PDF share one render-plan revision
- SVG, PNG, and PDF have aligned physical geometry
- PNG dimensions match physical size and DPI
- PDF page dimensions match the render plan
- visible objects, ordering, text, and style tokens match

### Editor lifecycle tests

- gallery capability equals editor mode
- gallery preview equals the editor first-screen revision
- save creates an unpublished working revision
- publish upgrades every required formal asset together
- a single writer failure preserves the old published group
- reopening restores document state

### Historical recovery tests

- rebuildable legacy output creates a new run
- asset-only legacy output remains static
- partial asset loss regenerates from document and data
- old files never enter the active-run manifest automatically

### Manual workflow checks

- insert SVG into supported Word and WPS versions
- insert 600 DPI PNG as fallback
- compile or inspect PDF in a LaTeX-oriented workflow
- verify copied paths and format labels match asset roles

## CI Quality Gates

CI rejects:

- direct `savefig` calls in migrated technique output modules
- hard-coded `.pdf`, `.svg`, or `.png` output paths in migrated providers
- new technique-level publication format configuration
- absolute data paths in FigureDocuments
- normal gallery recursion over the output filesystem
- gallery-originated editor opens that bypass manifest entries
- ready manifest entries missing required profile assets
- separate gallery and editor capability decisions

Shared rendering and export internals are the only allowed location for formal artifact writing.

## Acceptance Criteria

The lifecycle is complete only when:

- SAXS, WAXS, DSC, IR, and NMR implement the same FigureDefinition contract
- every run selects exactly one global output profile
- every ready figure satisfies that profile
- every ready figure has a portable FigureDocument
- every object-mode ready figure has validated numerical data snapshots for all data-bound objects
- every static-background ready figure has a portable background asset and explicit raster/vector fidelity metadata
- every run has one authoritative manifest
- the gallery reads the manifest rather than guessing from files
- gallery preview, editor, and published assets share one render plan
- gallery badge and editor mode always agree
- standard single-axis data figures enter object editing when their contract is complete
- multi-panel figures become object-editable through the formal layout model, not filename exceptions
- Save Edits and Publish have distinct revision semantics
- formal SVG, PNG, and PDF assets publish atomically
- current runs never mix with historical files
- legacy recovery is explicit and honest
- only one formal figure-output pipeline remains in production

## Risks And Controls

### Risk: the shared pipeline becomes one oversized module

Control:

- retain separate validator, writer, planner, exporter, inspector, resolver, and repository units

### Risk: techniques lose necessary scientific flexibility

Control:

- keep scientific content and recommended layout in FigureDefinition
- centralize only lifecycle and publication policy

### Risk: migration leaves permanent compatibility branches

Control:

- define closure criteria per technique
- remove its old production output path immediately after migration acceptance

### Risk: complete profiles increase runtime

Control:

- reuse one render plan
- keep preview rendering lightweight
- permit lighter run-level profiles while retaining uniformity within a run

### Risk: style inheritance changes scientific meaning

Control:

- inherit only presentation state through compatibility checks
- never inherit new numerical results from an old run

## Final Product Rule

Technique modules describe what a scientific figure means. The shared figure lifecycle determines how that figure is identified, persisted, rendered, edited, published, validated, and recovered.

There is one contract and one production pipeline. Exported files are consistent assets of a figure project, not independent sources of truth.
