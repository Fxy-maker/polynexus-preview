# PolyNexus Research Preview: Open-Source Guide

## Scope

PolyNexus is released as a research preview under Apache-2.0. It is an
AI-oriented polymer research workbench: AI/Codex can organize a research task,
while the deterministic Core converts data, calculates results, retains
provenance, and exposes shared run/evidence/figure objects.

It is not a validated replacement for expert scientific judgement, instrument
software, laboratory information management systems, or regulatory workflows.
Users remain responsible for method selection, calibration, data quality,
scientific interpretation, and publication claims.

## Capability maturity

The public capability catalog is authoritative at runtime. Its status has the
following meaning:

| Status | Meaning |
| --- | --- |
| `available` | A registered deterministic route is supplied for the declared input contract. It can still expose unavailable metrics or quality information when a particular dataset lacks a required input. |
| `experimental` | A route is visible for evaluation, but its provider binding, validation range, calibration handling, or evidence semantics are not yet complete. Do not represent it as a settled scientific method. |
| `unsupported` | The catalog intentionally has no executable provider. The name records a planned extension; it is not a claim of analysis support. |

Current core technique families are DSC, FTIR/IR, SAXS, WAXS, and NMR. Coverage
varies by workflow and input form. In particular, several N-D routes remain
experimental, and DMA/DMTA, rheology, TGA/DTG, SEC/GPC, and mechanics are
currently cataloged as unsupported rather than implemented providers.

## Result and evidence boundary

All supported entry points should share this path:

```text
raw artifact -> canonical conversion -> ComputeRun -> Metric Manifest
             -> Evidence Package / FigurePlan -> AI or human interpretation
```

AI may select files, propose parameters, organize evidence, and request a
calculation. It must not fabricate numerical results, overwrite a raw artifact,
or use a private result object in place of the Core's shared contracts.

Warnings and unavailable values are retained at the metric or input level.
They are not evidence that a whole project is invalid, and they are not a
substitute for scientific review.

## What is intentionally optional

Codex/MCP automation, RAG, Zotero integration, Origin export, and external
instrument adapters are optional integrations. Basic deterministic analysis
does not require an external AI service or Origin installation.

## Public-release checklist

Before pushing a branch or publishing an archive:

1. Start from a clean, reviewable release branch; do not publish a personal
   working directory.
2. Confirm `LICENSE`, README capability statements, and release notes match
   the code actually being published.
3. Inspect tracked files and Git history for secrets, personal paths, logs,
   local databases, generated evidence packages, and experimental outputs.
4. Verify redistribution rights and attribution for every bundled sample,
   fixture, image, document, data table, font, and third-party asset.
5. Run the release verification matrix and report failures honestly. A passing
   focused matrix does not imply every workflow or scientific method is
   validated.
6. State which capabilities are `available`, `experimental`, and
   `unsupported` in the release notes.

No release procedure in this repository automatically pushes source code,
uploads data, publishes packages, or contacts external services.
