# PolyNexus AI/Core Design Baseline

## Context

PolyNexus is a Codex/AI-oriented polymer research compute middleware. AI may
explore broadly, while the deterministic Core owns calculation, provenance,
structure, and reproducible evidence.

This baseline defines product policy, not an implementation interface contract.
Specific DTO shapes, cache details, and QC thresholds remain later engineering
decisions.

## Design principles

### 1. One shared scientific pipeline

All entry points use the same scientific path:

```text
raw artifact -> CanonicalExperiment -> ComputeRun -> Metric Manifest
             -> Evidence Package -> FigurePlan -> ARS
```

No entry point may create a private scientific truth, a parallel provenance
store, or an entry-point-specific result representation.

### 2. AI explores, Core computes

AI/Codex is responsible for understanding the research question, selecting
files, proposing groupings and methods, organizing evidence, trying
preprocessing or parameter variants, and writing papers.

The Core is responsible for reading and converting data, running deterministic
calculations, persisting run records, generating metrics, charts, and evidence,
and preserving the source, method, and provenance chain.

AI may request work and may even generate new code paths for exploration, but
it must not fabricate values or bypass canonical validation.

### 3. Maximize calculability, minimize blocking

The Core should compute every applicable metric from the available data. A
missing or invalid local input only blocks the metrics that depend on it; it
must not suppress unrelated calculations.

Standard methods and AI-defined custom methods are both retained as distinct
runs. One must not overwrite the other.

### 4. Unknown methods become exploration runs

If a method is not yet a formal capability, it is not disguised as one. It
enters a unified exploration path and can still be preserved in the project,
compared later, and selected into evidence.

Exploration is a product path, not a scientific promotion.

### 5. Evidence is curated before ARS

Codex or a future orchestrator selects from the full run history and assembles
an Evidence Package before handing material to ARS.

ARS should receive curated evidence, not every intermediate warning, failed
attempt, or raw internal diagnostic.

### 6. Scientific meaning changes require user confirmation

If grouping, cross-technique alignment, or any orchestration choice changes the
scientific meaning of the result, the user must confirm that choice before it
becomes formal. Otherwise the system should continue with independent
calculation and keep the ambiguity visible.

### 7. Raw data stays immutable

Raw files are never overwritten. Cleaning, conversion, derived tables, figures,
and evidence packages are always new objects with provenance.

Standard derivative data may be generated automatically. Expensive, special, or
ambiguous parameter combinations are computed on demand.

### 8. Extension path is explicit

The first-wave core techniques are DSC, FTIR, SAXS, WAXS, and NMR.

FTIR condition x wavenumber matrices, synchronous/asynchronous 2D-COS, and
SAXS/WAXS detector-image processing are part of that first wave.

DMA, rheology, TGA, SEC/GPC, and mechanics enter through the general
exploration lane until dedicated capability work lands.

Origin is an optional plugin. Personal templates and recipes remain versioned
user assets and must not overwrite older project history.

## Explicit non-goals

- No account system, multi-user permissions, e-signatures, or heavy regulatory
  audit as a prerequisite for core use.
- No requirement that every result be immediately paper-ready.
- No early pruning of results only because they do not fit the current paper
  outline.

## Deferred implementation questions

The following are intentionally not decided by this baseline:

- ExplorationRun field names and payload shape.
- cache-key composition details.
- QC thresholds for individual techniques.
- stop conditions for repeated exploration attempts.
- the plugin boundary for Origin and other external tools.

Those are later implementation tasks, not product-direction decisions.
