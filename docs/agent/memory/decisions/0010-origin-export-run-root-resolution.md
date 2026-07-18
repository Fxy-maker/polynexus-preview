---
kind: decision
status: active
date: 2026-07-18
title: Resolve Origin export sources from the figure run root
---

## Context

Manifest-backed generated figure documents record CSV data sources as
run-relative paths such as `figures/<figure>/data/<source>.csv`. The figure
renderer already resolves those paths through the active run root, but Origin
export originally received only the preview/primary figure path. Export then
searched the figure directory or process working directory and could not find
an otherwise valid source file.

## Decision

Carry the gallery entry's `run_root` through ChartEditor as
`ExportRequest.source_root`. Resolve relative sources through the source root
first in one shared helper, `polynexus/origin/path_resolution.py`, and retain
the existing figure-directory and working-directory fallbacks for older callers
that do not have run-root context.

All Origin adapters use the shared resolver. The GUI does not probe or branch
on adapter-specific path behavior.

## Consequences

- Package, COM/LabTalk, and `originpro` exports agree on source-path semantics.
- Existing absolute paths and inline data remain supported.
- A missing or stale run-root source still produces an explicit export failure;
  the resolver does not silently synthesize scientific data.
- External Origin runtime behavior remains optional and must be tested separately
  from the portable package path.

## Evidence

- Origin path and ChartEditor request tests: 36 passed in the affected suite.
- ChartEditor regression suite: 238 passed.
- The original failure was `data source does not exist` for a valid run-relative
  SAXS temperature-waterfall CSV.

## Revisit condition

Revisit if the figure/document contract introduces another path kind or if
package-relative and run-relative data sources must coexist in one export
request. In that case, preserve `path_kind` explicitly in the Origin mapping
instead of relying only on source-root availability.
