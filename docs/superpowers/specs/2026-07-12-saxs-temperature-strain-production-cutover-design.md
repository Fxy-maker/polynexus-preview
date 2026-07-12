# SAXS Temperature/Strain Production Cutover Design

**Date:** 2026-07-12
**Task:** `saxs-temperature-strain-production-cutover-2026-07-12`

## Goal

Lock SAXS temperature/time and strain plotting to the existing
`FigureDefinition -> FigurePipeline -> RunFigureManifest -> Gallery/Editor`
lifecycle without changing scientific analysis, emitted parameter semantics, or
the current mainline provider implementation.

## Current context

The repository already contains mode-aware SAXS figure providers:

- `figure_temperature.py` reads emitted temperature/time evidence and gates
  Main, SI, and Diagnostics content.
- `figure_strain.py` covers 1D profiles and evidence-gated 2D detector panels.
- `figure_provider.py` selects exactly one provider from the engine state.
- `BaseEngine.publish_figure_definitions()` writes the shared manifest and
  updates `result.metadata` and `result.figures`.

The current mainline already routes non-empty SAXS definitions through the
shared publisher and returns an empty mapping when no definitions are
available. The remaining work in this cutover is to preserve that contract
against future regressions and document the production boundary after the
unified figure lifecycle merge.

## Options considered

### Option A — Contract-lock the existing strict route (selected)

Keep the current providers and contracts, add boundary and acceptance tests,
and lock `SAXSEngine.plot()` to the shared publisher for every non-empty
definition tuple. If a provider returns no definitions, return no publication
assets for static, temperature/time, strain, or mixed/unsupported state instead
of invoking legacy helpers.

**Trade-off:** a malformed or incomplete series produces no files until its
provider can emit a governed definition. This prevents an ungated file from
being mistaken for a publication pack.

### Option B — Compatibility flag around legacy fallback

Add a configuration flag that lets callers choose shared publication or legacy
plotting for temperature/strain.

**Trade-off:** this preserves more short-term compatibility but leaves two
production semantics, makes acceptance behavior configuration-dependent, and
allows ungated output to remain the default by mistake.

### Option C — Rewrite all legacy plotting helpers as adapters

Make the old helper functions internally call the provider and shared pipeline.

**Trade-off:** this expands the change into old plotting and editor structures,
raises regression risk, and is outside this task's non-goals. It is better
handled as a later compatibility cleanup if still needed.

## Selected architecture and data flow

1. `SAXSEngine.build_figure_definitions()` calls
   `build_saxs_figure_definitions(self)`.
2. The dispatcher selects one of `static`, `temperature`, or `strain` from
   condition/result state. Conflicting condition and result states remain
   unsupported and return no definitions.
3. The selected provider reads only existing emitted frame/result evidence.
   It does not re-run analysis or repair missing values.
4. Temperature/time definitions expose the condition axis, representative
   frame provenance, waterfall/heatmap evidence, final lamellar metrics, and
   gated invariant/crystallinity/Avrami evidence. Missing Main evidence is
   represented by SI/Diagnostics roles or an explicit omission reason.
5. Strain definitions select either 1D or detector-backed 2D from available
   evidence, load only selected detector snapshots, and gate orientation panels
   on existing anisotropy evidence.
6. Non-empty definitions go through `BaseEngine.publish_figure_definitions()`.
   The publisher writes preview/SVG/PNG/PDF/600-DPI TIFF assets, a run manifest,
   and the active-run pointer, then updates `result.metadata` and
   `result.figures`.
7. For any SAXS state, an empty definition tuple is a governed no-publication
   result: `plot()` returns `{}` and does not call a legacy helper.

## Error and compatibility handling

- Provider conflicts remain safe no-ops: no mixed-mode definitions are emitted.
- Empty or malformed frame evidence must not be promoted to Main by fallback
  plotting.
- Existing legacy helper symbols remain outside this task; this task does not
  delete or rewrite them.
- Existing gallery behavior remains manifest-first. A successful cutover is
  observable through `active_run.json`, `figure_manifest.json`, and the result
  metadata paths.
- GUI streamlining, old gallery fallback removal, and old editor style-context
  migration remain out of scope.

## Testing strategy

### Provider boundary tests

- Temperature mode wins over static configuration only when completed
  temperature evidence is present; time axis is preserved.
- A temperature provider cannot mix with strain definitions, and vice versa.
- Temperature Main appears only when heatmap, q-star, representative profiles,
  and enough emitted final lamellar evidence exist; otherwise roles and gate
  reasons are explicit.
- Strain 1D and detector-backed 2D remain mutually exclusive; selected detector
  snapshots and orientation evidence are bounded and provenance-backed.

### Production acceptance tests

- A representative temperature engine publishes a manifest-backed pack and
  updates `result.metadata`/`result.figures`.
- A representative strain engine does the same.
- An active temperature/strain engine with no provider definitions does not call
  the old helper path.
- Static, temperature/time, strain, and unsupported empty-definition states all
  keep the no-publication behavior.
- The active manifest is consumable by the existing gallery ordering/filtering
  contract.

### Verification gates

Run focused provider and production tests first, then the changed-scope and
repository verification commands from the task card. No GUI streamlining or
unrelated technique changes are included.

## Scope boundary

Files are limited to SAXS production routing, provider/acceptance tests, and
task/spec/plan documentation. Scientific analysis functions and legacy helper
implementations are not redesigned.
