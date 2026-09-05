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

Current core technique families are DSC, FTIR/IR, SAXS, WAXS, NMR, and the
sample-neutral TGA, DMA, rheology, SEC/GPC, and mechanics table-curve
foundations. Coverage varies
by workflow and input form. TGA descriptive curve summaries are available for supported table
exports. Normalized mass, DTG, specified-coordinate residue, and material-
neutral event candidates are emitted as diagnostic derived results; their
formal capability promotion remains pending independent replay, uncertainty
work, and scientific review, while kinetics is unsupported. DMA preserves
unambiguously labelled table signals and can derive unit-compatible loss
tangent series plus material-neutral temperature-response peak candidates.
Those derived outputs remain diagnostic pending independent replay,
uncertainty work, and scientific review; master curves, shift factors, and Tg
interpretation remain unsupported.
Rheology preserves unambiguous rheometer table signals and derives only
dimensionally compatible steady-flow and oscillatory identities with explicit
unit conversion and point-level unavailable masks. The formal viscosity,
moduli, yield-stress, thixotropy, creep/relaxation, and TTS capabilities remain
unsupported pending independent replay, uncertainty work, and scientific
review. SEC/GPC has an executable, sample-neutral chromatogram foundation:
retention/elution coordinates and explicitly labelled RI, UV, MALS/RALS/LALS,
viscometer/pressure, concentration, vendor molar-mass, and distribution columns
are preserved as separate measurements. Only a recorded-response peak and
baseline-uncorrected raw integral are derived; `Mn`, `Mw`, `Mz`, and dispersity
remain unavailable without a reviewed calibration/distribution contract.
Mechanics provides a sample-neutral table-curve foundation that preserves
explicit test axes and response channels and derives recorded response peaks
and raw trapezoid integrals. A canonical payload may explicitly bind test mode,
geometry, units, fit window, yield offset, and endpoint semantics; with that
contract the Core can compute a diagnostic stress-strain modulus, offset-yield
candidate, and last-valid stress-strain toughness value. These model outputs
remain unpromoted pending independent replay, uncertainty work, and scientific
review. Explicit measurement standard deviations now flow into a first-order
diagnostic uncertainty projection, and serialized replay cases can compare
outputs with an external expected-value fixture. These are validation aids, not
metrological claims or automatic promotion gates. Fatigue, fracture, and creep
remain unavailable.

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
