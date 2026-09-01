# First AI-Native Research Loop Design

## Purpose

This design turns the confirmed PolyNexus doctrine into one observable,
end-to-end product path. PolyNexus is an AI-facing polymer science compute
layer with a human quick-analysis entry point. Codex/AI owns research
organization, PolyNexus owns deterministic conversion and computation, and
ARS owns scientific interpretation and manuscript writing.

The first loop is deliberately narrow enough to finish and broad enough to
prove the product's actual advantage over ad-hoc AI scripts.

## First-loop scope

The loop accepts one project directory and an AI/Codex analysis request for a
selected group of files. The first acceptance project is mixed-technique:
DSC, FTIR, SAXS, and WAXS are exercised when present; NMR is included when the
project contains compatible input and otherwise appears as an explicit missing
capability input, not as a silent omission.

The repository contains a small public fixture project for deterministic CI.
The user's real project is replayed read-only as an external acceptance case;
raw files and generated personal manuscripts never enter the repository.

The observable path is:

```text
project directory
  -> Codex inventory and group selection
  -> AI-selected template and mapping
  -> canonical conversion
  -> deterministic ComputeRun execution
  -> per-file metrics and group statistics
  -> FigurePlan and figure data
  -> self-contained evidence package
  -> ARS writing input
  -> evidence-grounded manuscript draft and preflight
```

## Product boundaries

### Codex/AI

AI may inspect inventory, identify techniques and groups, select templates,
propose parameters, request standard or exploratory recipes, select figures,
and ask ARS to write or revise. AI must use the public project/run/evidence
interfaces and cannot invent scientific values or bypass canonical conversion.

An exploratory recipe is allowed for a missing standard capability. It is
recorded as an `ExplorationRun` (or the existing equivalent shared run object)
with code/recipe, parameters, environment, inputs, and outputs. It does not
become a global plugin automatically.

### PolyNexus Core

Core owns canonical templates, deterministic providers, group statistics,
figure generation, provenance, and serialization. It computes every applicable
metric and preserves successful results with warnings. It blocks only on
structural integrity failures such as unusable axes/units, damaged input, or
unbound provenance.

Calculation status and paper-use status remain separate. A result may be
`computed_with_warning` and still enter the evidence package. Scientific
promotion remains an ARS/human decision.

### ARS

ARS consumes the package-relative writing input and produces manuscript text,
citations, formulas, review actions, and revisions. PolyNexus does not copy
ARS's writing or multi-role review logic into Core.

### Human

Human input is requested only for a grouping or scientific choice that can
change meaning. Ordinary QC warnings are recorded and surfaced to AI; they are
not per-file approval gates.

## Shared public objects

The loop must reuse existing contracts:

- `Project` / inventory and selected file groups;
- `AnalysisPlan` and template mapping;
- `CanonicalExperiment` / canonical data blocks;
- `ComputeRun` and its metric manifest;
- `GroupResultTable`;
- `FigurePlan` and generated figure assets/data;
- `EvidencePackage` and package-relative run snapshots;
- `ars-writing-input.json` and manuscript/preflight DTOs;
- `ResearchTask` only as an orchestration shell, never as a second result store.

GUI, CLI, Batch, Codex, and ARS must read the same serialized objects. Quick
analysis may remain a human-only draft path, but if a user saves it into a
project it must be attached through the same run contract.

## Required output

For one selected project group, the loop must produce:

```text
.polynexus/
  analysis-plan.json
  runs/<run-id>.json
  result-tables.json
  result-tables.csv
  figures/<figure-id>/figure.svg
  figures/<figure-id>/figure.png
  figures/<figure-id>/figure.json
  figures/<figure-id>/figure-data.csv
  evidence/<package-id>/manifest.json
  evidence/<package-id>/writing-evidence.json
  evidence/<package-id>/ars-writing-input.json
  manuscript/<draft-id>/manuscript.md
  manuscript/<draft-id>/manuscript.json
  manuscript/<draft-id>/preflight.json
```

Every metric entry exposes value, unit, method, parameters, source run/file,
warnings, and computed/unavailable status. Every figure binds to source runs
and actual plotted data. The package is portable and does not require the
original chat transcript to interpret it.

## Failure behavior

- A mixed directory is never silently merged into one group; Codex supplies
  the selected paths or an explicit group mapping.
- Missing NMR or another technique is represented as an unavailable input with
  a reason and does not hide the other technique results.
- Provider failures are retained as failed run records with diagnostics; no
  placeholder number is emitted.
- A warning does not discard a finite deterministic result.
- Changed source files invalidate affected runs and require a new version; old
  runs and evidence remain readable.
- ARS unavailability leaves the evidence package usable for AI inspection but
  prevents claiming a completed manuscript stage.

## Acceptance criteria

1. A fresh checkout can run the public fixture through the full path using one
   documented CLI/Codex-facing entry point.
2. The same project run can be loaded by the CLI/AI consumer and the GUI view
   adapter without reconstructing values from raw files.
3. The output contains per-file results, group statistics, warnings and
   explicit unavailable/failed entries for all selected techniques.
4. At least one figure per selected technique is generated from a `FigurePlan`
   with SVG, PNG, JSON and plotted-data CSV bindings.
5. The evidence package is self-contained, hash-checked, and references the
   exact run snapshots used by the writing input.
6. ARS can consume the package-relative writing input and generate a draft
   whose numeric claims resolve to package metrics; no metric is recomputed or
   invented by the manuscript path.
7. A changed source or mapping creates a new run/package revision and leaves
   the previous revision intact.
8. The real project replay is read-only and records its limitations separately
   from the public fixture result.

## Explicit non-goals

- Complete support for every vendor format or every polymer technique.
- A GUI redesign or removal of quick analysis, Batch, Origin, or RAG.
- A plugin marketplace, account system, or regulated audit trail.
- Automatic scientific approval or automatic paper submission.
- Guaranteeing that the first generated manuscript is publication-ready.
- Adding a second private data model for ARS, GUI, or exploratory AI code.

## Follow-up: open-source readiness

After the first loop passes, open-source preparation is a separate release
task. It will cover dependency tiers, public fixtures, installation and Codex
integration docs, license choice, secret/path scanning, a clean-environment
install test, known-failure ledger, and exclusion of real data and local
runtime artifacts. It must not weaken the scientific or provenance boundaries
 defined here.
