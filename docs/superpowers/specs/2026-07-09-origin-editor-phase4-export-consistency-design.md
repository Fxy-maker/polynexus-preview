# Origin Editor Phase 4 Export Consistency Design

**Date:** 2026-07-09

## Goal

Complete Phase 4 of the Origin-style editor roadmap by making exported figure assets stable, consistent, and safe to regenerate from the same `FigureDocument`.

This phase focuses on the export foundation first:

- one document drives `PNG`, `SVG`, and `PDF`
- export rules become explicit instead of being spread across UI state and ad hoc `savefig` calls
- exported asset groups become safe to replace without silently corrupting existing files

This phase does **not** yet implement the full user-facing submission checklist panel or the full batch re-export workflow. It prepares the service boundary those features will use next.

## Why This Phase Exists

The current editor has already gained two important capabilities:

- `FigureDocument` captures editable figure state for generated and static-background workflows
- SCI audit and export-context helpers already exist in the codebase

However, export is still fragmented:

- `plot_edits.savefig_with_edits()` applies style and saves one path at a time
- `ChartEditor` can save the current figure, but it does not own a single multi-format export contract
- generated-object figures and static-background figures do not yet share one export pipeline

As a result, `PNG`, `SVG`, and `PDF` are not guaranteed to remain geometrically and semantically aligned across re-export operations.

## Scope Boundary

Phase 4 covers export consistency only.

### In scope

- define one service-layer export entry point for `FigureDocument`
- export the same document to `PNG`, `SVG`, and `PDF`
- normalize export rules for canvas size, background, DPI, and font policy
- support both `object` mode and `static_background` mode through one service interface
- return structured export results and warnings
- protect existing asset groups from partial overwrite
- add test coverage for export consistency behavior

### Explicitly out of scope

- a new submission checklist UI
- journal-specific preflight UX beyond profile placeholders and data model hooks
- full batch re-export orchestration
- raster-to-object reverse parsing
- redesign of figure editing interactions

Those remain downstream consumers of this phase.

## Recommended Approach

Use a dedicated service-layer design centered on `FigureDocument`.

### Rejected alternatives

- **Patch the existing save buttons directly**
  - Fastest short-term path
  - Keeps export rules split across `ChartEditor`, `plot_edits.py`, and technique outputs

- **Post-process already exported files**
  - Lowest initial intrusion
  - Treats inconsistency as cleanup instead of fixing the source-of-truth problem

### Recommended option

Introduce a unified export service that accepts one `FigureDocument` plus one export profile and produces a consistent asset group.

This gives Phase 4 one stable control point that later Phase 4.x / Phase 5 work can reuse for:

- submission preflight
- journal presets
- batch re-export
- export package generation

## Architecture

### Core principle

`FigureDocument` becomes the only logical export input for the Origin-style editor workflow.

Upper layers decide **when** to export. The export service decides **how** to export consistently.

### Proposed module

- `polynexus/core/figure_export_service.py`

This service owns:

- request normalization
- render planning
- multi-format writing
- post-export inspection
- atomic asset-group replacement

### Responsibility split

- `FigureDocument`
  - describes what the figure is
  - remains the long-term editable truth

- `ChartEditor`
  - edits document state
  - invokes export requests
  - does not directly own multi-format save policy

- `FigureExportService`
  - turns one document into one consistent asset group
  - applies shared export rules for all formats
  - reports warnings and failures

- `plot_edits.py`
  - remains as a compatibility helper for older single-path save flows
  - is no longer the authoritative Phase 4 export entry point

- technique `*_output.py` modules
  - continue to generate figures and `.pnfig.json` documents
  - should progressively hand standardized asset-group export off to the new service

## Data Model

### `FigureExportRequest`

The service should accept a normalized request object with at least:

- `document`
- `source_path`
- `asset_spec`
- `profile`
- `formats`
- `write_mode`
- `target_root` or explicit target paths

### `FigureExportProfile`

Export rules should be explicit and serializable instead of being inferred from current widget state.

The profile should include:

- `canvas_size_in`
- `dpi`
- `background`
- `font_policy`
- `format_roles`
- `journal_preset_id`
- `bbox_strategy`

Phase 4 only needs the baseline profile shape plus a default profile. Rich journal presets can layer on later.

### `FigureExportResult`

The service should return structured output that the GUI and later audit layers can consume directly.

At minimum it should include:

- produced output paths
- per-format artifact metadata
- warnings and errors
- export timestamps
- consistency flags
- inspection results such as actual size and DPI

## Export Consistency Definition

Phase 4 consistency should not mean pixel-for-pixel identity across formats.

It should mean:

- the same `FigureDocument` is the input for all requested formats
- all formats share one canvas geometry baseline
- all formats share the same visible object set, ordering, text content, and style tokens
- `PNG` satisfies explicit pixel-size and DPI rules
- `SVG` and `PDF` remain vector-oriented outputs and do not silently degrade into screenshots
- any unavoidable format-level difference is reported as metadata, not hidden behavior

In short, consistency here means:

- semantic consistency
- geometric consistency
- export-spec consistency

## Internal Flow

The service should be broken into four layers.

### 1. Request resolver

Normalize external inputs into one `ResolvedExportRequest`.

Responsibilities:

- fill defaults from `document.export`, `asset_spec`, and the chosen profile
- resolve write targets
- choose `replace_asset_group` versus `export_copy`
- reject incomplete or contradictory requests early

### 2. Render plan builder

Convert the document into a render plan before writing any files.

This keeps format writers from inventing their own layout rules.

Two input branches feed one plan shape:

- `object` mode
  - render from generated figure objects and data sources

- `static_background` mode
  - render from background asset plus annotations

This is also the right place to reduce UI coupling around rendering helpers that currently live under `gui/`.

### 3. Format writers

Each writer consumes the same render plan.

- `PNG` writer
  - applies pixel size, DPI, and background rules

- `SVG` writer
  - preserves vector output and editable text where supported

- `PDF` writer
  - produces submission-oriented vector output

Writers must not independently redefine geometry, style, or object visibility.

### 4. Post-export inspector

After each temporary artifact is written, inspect the file and collect:

- actual dimensions
- actual `PNG` DPI and pixel size
- existence and readability
- fallback warnings
- format-specific downgrade signals

The combined inspection becomes part of `FigureExportResult`.

## Overwrite And Failure Policy

This phase should optimize for safety over convenience.

### Write modes

- `replace_asset_group`
  - replace the current figure's standard asset group

- `export_copy`
  - write a new asset group elsewhere without disturbing the current one

### Atomicity rule

When multiple formats are requested together, treat them as one atomic asset-group operation.

Recommended behavior:

1. write all requested outputs to temporary paths
2. inspect them
3. only replace official asset paths if all hard requirements pass
4. if any hard failure occurs, leave the old asset group and document pointers unchanged

This prevents a mixed state such as:

- new `PNG`
- missing `PDF`
- stale `.pnfig.json`

### Failure grading

- `ERROR`
  - blocks final replacement
  - examples: writer failure, unreadable temp artifact, impossible geometry request, target path not writable

- `WARN`
  - export may complete, but user-visible warning is required
  - examples: font fallback, derived background normalization, non-blocking metadata gaps

- `INFO`
  - records normal export details

### Asset safety rules

- never delete unrelated files in the output directory
- never update `.pnfig.json` pointers or sidecar path references until the export operation succeeds
- prefer temporary-write plus atomic-replace over proliferating backup files

GUI-level backup affordances may remain for older static flows, but they are not the primary Phase 4 protection strategy.

## Integration Plan

### `ChartEditor`

Update export actions so the editor builds a `FigureExportRequest` and hands it to the service.

It should no longer directly own the final `self._figure.savefig(...)` path for Phase 4 export actions.

### Generated figure pipeline

Technique outputs should keep generating `FigureDocument` sidecars as they do today.

The new service becomes the standardized export path once a document exists.

### Existing audit and export metadata helpers

Phase 4 should not replace current SCI audit helpers or export package metadata.

Instead, it should produce cleaner artifacts and result metadata that those helpers can consume later with less guessing.

## Tests

Phase 4 needs three levels of verification.

### Unit tests

- request/profile normalization
- target-path resolution
- format-role defaults
- failure grading
- atomic replacement decisions

### Integration tests

- one generated `FigureDocument` exports to `PNG`, `SVG`, and `PDF`
- one static-background `FigureDocument` exports through the same service interface
- resulting artifacts report aligned geometry and expected format metadata

### Regression tests

- `ChartEditor` export actions route through the new service
- failure in one requested format does not corrupt an existing asset group
- export results remain compatible with current audit and export-context layers

### Suggested files

- `tests/test_figure_export_service.py`
- targeted additions to `tests/test_chart_editor.py`

## Acceptance Criteria

- the same `FigureDocument` can export to `PNG`, `SVG`, and `PDF` through one service entry point
- both generated and static-background documents use the same export contract
- requested multi-format export is atomic at the asset-group level
- structured export results expose warnings, failures, and artifact metadata
- replacing an asset group does not update official paths when any hard export failure occurs
- `ChartEditor` no longer owns ad hoc multi-format export behavior directly

## Risks And Controls

### Risk: the service becomes a second oversized editor module

Control:

- keep request resolution, rendering, writing, and inspection as separate internal units

### Risk: rendering logic remains coupled to GUI helpers

Control:

- pull non-UI rendering behavior behind export-facing interfaces instead of making `core` depend on widget logic

### Risk: format-specific behavior drifts again

Control:

- require one render plan and one geometry baseline for all format writers

### Risk: scope expands into submission UX and batch orchestration

Control:

- keep journal presets and batch flows at the profile and request-model hook level only in this phase

## Out-Of-Scope Follow-Ons

Once this phase lands, the next layers can build on it safely:

- journal preset library
- submission preflight panel
- batch re-export UI and CLI
- export bundle generation aligned to `FigureExportResult`

Phase 4 should stop after the export foundation is stable enough to support those layers.
