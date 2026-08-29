---
task_id: 2026-08-29-paper-quality-pipeline
kind: architecture
status: proposed
date: 2026-08-29
title: Build evidence-grounded paper generation pipeline
---

# Evidence-Grounded Paper Generation Pipeline

## Goal

Enable one controlled run from a PolyNexus evidence package to a usable paper
draft with reproducible figures, formulas, Zotero/CSL citations, coherent
whole-paper structure, and deterministic document preflight.

## Non-goals

- Reimplementing ARS or replacing Zotero.
- Moving scientific calculations or publication decisions into the writing
  skill.
- Automatically claiming that a figure or mechanism belongs in Results.
- Rewriting existing DOCX files in place.

## Shared objects and entry points

- Objects: project, evidence package, figure, export, and new manuscript-source
  projections; existing `ComputeRun` values remain authoritative.
- AI/Codex/CLI: reads evidence package, creates versioned source/plan objects,
  invokes the Suite skill, and exports draft artifacts.
- GUI: displays FigurePlan candidates, review decisions, and preflight reports
  through DTOs; it does not calculate or rewrite manuscript XML.
- ARS/Zotero/CSL: optional external consumers selected by the Suite adapter.
- Cross-entry rule: CLI, GUI, and skills consume the same serialized plans,
  figure manifests, citation keys, and review ledger.

## Affected boundaries

- `polynexus/core/project_workflow`: read-only evidence and figure contracts.
- `polynexus/suite`: paper-pipeline orchestration and skill handoff.
- `polynexus/cli` and `polynexus/gui`: DTO consumers and review surfaces.
- External ARS/Zotero: adapters only; no source code is copied into Core.

## Implementation plan

1. Define versioned `PaperBrief`, `ClaimRecord`, `FigurePlan`,
   `CitationRequest`, `ManuscriptSource`, and `PreflightReport` contracts, with
   adaptive `needs_input` requests rather than mandatory stage gates.
2. Build an evidence-to-source bridge that projects existing result tables,
   evidence boundaries, and metric provenance without recomputation.
3. Replace fixed image outputs with FigurePlan-driven candidate layouts,
   SVG-first rendering, optional PNG/PDF export, and machine checks.
4. Add AI ranking plus optional human selection recorded in
   `review-decision.json`; ask the user only when a decision materially changes
   the result or figure.
5. Add Zotero detection and dynamic-field mode, plus CSL static mode with
   stable keys and `.bib`/`.json` export when Zotero is unavailable.
6. Add formula objects, manuscript-source generation, and section/paragraph
   contracts for whole-paper coherence.
7. Add claim-boundary, citation, formula, figure, cross-section, and DOCX/PDF
   preflight checks.
8. Run the PA6 six-sample pilot and compare revision count and defects with the
   previous direct-AI workflow.

## Acceptance criteria

- [ ] A valid evidence package produces a versioned manuscript source without
      inventing values or bypassing ComputeRun provenance.
- [ ] Every selected figure has a FigurePlan, source links, a quality report,
      and a recorded human/AI decision.
- [ ] Zotero mode emits dynamic citations; no-Zotero mode emits CSL-correct
      static citations and importable bibliography files.
- [ ] Formula fields, figures, citations, result tables, and claims remain
      cross-linked after DOCX/PDF export.
- [ ] The generated draft passes structural preflight and leaves only the
      declared scientific/human review items.
- [ ] Non-ambiguous stages run automatically; only material unresolved choices
      return a machine-readable `needs_input` request.
- [ ] Existing Core and evidence-package tests remain green.

## Verification

Each phase runs its focused pytest matrix first, then:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-29-paper-quality-pipeline.md --changed --types
git diff --check
```

The final pilot additionally requires the existing cross-entry and evidence
package matrices plus a human visual review of rendered figures and the draft.

## Completion evidence

- Exact commands and outcomes:
- Known limitations or follow-up:
- Pre-existing changes left untouched:
