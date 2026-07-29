# Advanced static/temperature SAXS Figure V2 binding design

## Decision

Use the existing reviewed V2 adapters for all Figures emitted by the current
advanced providers: `saxs_static` for static Figures and `temperature_saxs`
for temperature Figures.  The static provider already centralizes recipe
construction in `_definition`; its default is the narrowest way to cover all
static outputs.  Temperature recipes receive the same explicit key at their
existing recipe boundaries.

## Runtime and safety

`FigurePipeline` already writes a V2 sidecar when the adapter returns a valid
worksheet/document/layout.  The adapter and `LayoutResolver` remain the
fail-closed gate.  This task only changes capability declaration; all source
values, evidence provenance, quality levels, publication roles, and legacy
assets remain unchanged.

## Verification

Provider-wide tests will enumerate the existing static and temperature
definitions, assert the adapter key and `v2_runtime == ready`, and assert a
sidecar is produced for representative Pipeline runs.  No new physical
threshold or V2 default policy is introduced.
