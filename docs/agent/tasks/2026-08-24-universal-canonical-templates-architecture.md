---
task_id: 2026-08-24-universal-canonical-templates-architecture
kind: architecture
status: implementation_complete_review_required
date: 2026-08-24
title: Define universal canonical templates and maximal computation
---

# Define Universal Canonical Templates and Maximal Computation

## Goal

Record the approved universal canonical-data design that lets one export yield
multiple independent deterministic measurements and computes every supported,
executable capability without material-specific schemas or paper workflows.

## Non-goals

- Do not change runtime code, numerical methods, existing converter behavior,
  database schemas, or GUI layout in this documentation task.
- Do not infer material chemistry, create a material-specific data template, or
  let AI supply scientific numeric values.
- Do not create research review, evidence, RAG, ARS, Joint, or paper workflows
  in the conversion path.
- Do not remove legacy modules, commit real data, or run a scientific replay.
  NMR canonical conversion is deferred.

## Affected boundaries

- Conversion/contracts: future `CanonicalDataset`, immutable `Measurement`,
  `MappingProposal`, and conversion provenance replace the temporary direct
  envelope with reusable, validated canonical inputs.
- Deterministic calculation: a finite `CapabilityRegistry` routes every
  eligible measurement independently, preserving sibling results when one
  calculation fails.
- Application entry: Quick Analysis, CLI, Batch, and Codex will share
  proposal-to-canonical-to-capabilities-to-`ComputeRun` routing.
- Catalog/interpretation: material labels remain optional project-catalog
  context; material interpretation and paper workflows stay separate.
- Migration: generic one-dimensional conversion precedes general DSC and
  consumer migration; legacy removal follows a six-sample benchmark only.

## Shared objects and entry points

- Objects: `RawArtifact`, `MappingProposal`, `CanonicalDataset`, ordered
  immutable `Measurement`, `CapabilityRegistry`, capability item result, and
  `ComputeRun`.
- AI/Codex/CLI: future shared producers of mapping proposals and consumers of
  the same canonical datasets, item results, figures, warnings, and run
  status. They cannot bypass validation or calculate privately.
- GUI: future shared consumer and explicit-input provider over the same public
  contracts; it does not branch on technique-private algorithm state.
- Batch: future shared consumer of the same route; it remains a legacy
  consumer until its dedicated migration task.
- Cross-entry rule: Quick Analysis, CLI, Batch, and Codex must all traverse
  `proposal -> canonical dataset -> all eligible capabilities -> one ComputeRun`.
  This documentation-only task changes no live producer or consumer.

## Acceptance criteria

- [x] The design supports universal thermal-program and one-dimensional curve
  families, rather than schemas named for PA6 or another material.
- [x] One export may yield multiple measurements, and every directly supported
  deterministic capability runs independently with no unbounded parameter
  sweep.
- [x] Per-capability-item statuses are `completed`, `needs_input`, `failed`, or
  `not_applicable`; top-level `ComputeRun` status follows the approved
  aggregation rule.
- [x] Mapping provenance records observed, user, AI-proposed, and default
  fields; AI may choose only a validated mapping and cannot invent numeric data.
- [x] The scope excludes material chemistry, research review, evidence, RAG,
  ARS, Joint, and paper workflows from conversion and computation.
- [x] Migration preserves current Mettler PA6 conversion regression behavior,
  postpones NMR, and requires six-sample replay before legacy deletion.

## Implementation plan

1. Add public immutable canonical contracts, mapping validation/provenance, and
   a finite capability declaration contract with focused serialization tests.
2. Convert generic one-dimensional CSV, TXT, and XLSX exports into validated
   `spectrum_1d.v1` or `scattering_1d.v1` measurements; retain source locators,
   units, and background/normalization state.
3. Generalize DSC conversion to `thermal_program.v1` multi-program data while
   retaining the Mettler PA6 converter as a regression-protected adapter.
4. Route validated measurements through all eligible capability declarations,
   record independent item outcomes, and aggregate them into one `ComputeRun`.
5. Migrate Batch and Agent/Codex consumers after the shared Quick Analysis/CLI
   path proves the public contracts; do not remove their legacy paths earlier.
6. Replay the approved PA6, PA6-50, PA11, PA11-50, PA12, and PA12-50 benchmark
   set and record numerical/source-segmentation discrepancies explicitly.
7. Delete legacy conversion/workflow paths only after replay acceptance and
   import/consumer checks prove no supported entry point remains on them.

## Verification

```powershell
python scripts/task_check.py --task docs/agent/tasks/2026-08-24-universal-canonical-templates-architecture.md
python scripts/verify.py --task docs/agent/tasks/2026-08-24-universal-canonical-templates-architecture.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "docs(architecture): define universal canonical templates" `
  --files docs/agent/tasks/2026-08-24-universal-canonical-templates-architecture.md docs/superpowers/specs/2026-08-24-universal-canonical-templates-design.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes: recorded after final documentation validation.
- Known limitations or follow-up: this approved architecture still requires
  human review and separate implementation tasks; it changes no runtime path.
- Pre-existing changes left untouched: none; this worktree began clean.
