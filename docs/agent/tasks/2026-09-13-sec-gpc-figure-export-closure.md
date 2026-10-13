---
task_id: 2026-09-13-sec-gpc-figure-export-closure
kind: scientific
status: implementation_complete_review_required
date: 2026-09-13
title: Close shared SEC/GPC figure and export loop
---

# Close shared SEC/GPC figure and export loop

## Goal

Expose a valid SEC/GPC chromatogram for every completed canonical run and,
when an explicit calibration has computed molecular moments, expose the
calibrated molecular-weight distribution and calibration curve through the
shared FigureDefinition and export pipeline.

## Non-goals

- Infer a calibration, standard, detector response factor, or material meaning.
- Promote SEC/GPC to a validated publication capability.
- Add GUI-only calculations, private Codex results, or a custom Origin binary writer.
- Implement uncertainty, vendor readers, standards/negative controls, or capability promotion.

## Shared objects and entry points

- Objects: run, chart, evidence package, export.
- AI/Codex/CLI: create the same canonical ComputeRun and consume its provider
  FigureDefinitions and metric manifest; no private figure path.
- GUI: reads the shared FigureDefinition document, data snapshots, SVG/PNG/PDF
  assets, and existing Origin-compatible worksheet/curve adapter.
- Cross-entry rule: `SECEngine` produces definitions; `FigurePipeline` writes
  snapshots and assets; the existing V2 adapter preserves worksheet/curve
  semantics for Origin-compatible export.

## Affected boundaries

- SEC engine result-to-figure provider boundary.
- Shared figure definition validation, snapshot, render, and V2 adapter
  boundaries.
- SEC focused tests; existing CLI/ComputeRun consumers remain unchanged and
  are covered by their current shared-contract tests.

## Implementation plan

1. Add failing SEC figure-provider tests for uncalibrated and calibrated runs.
2. Implement shared chromatogram, molecular-weight distribution, calibration,
   and metric-summary data definitions from existing result/template objects.
3. Enable the existing V2 adapter route for SEC and publish through the common
   FigurePipeline, then run focused and structured verification.

## Context and output budget

- Read first: agent memory, SEC processing/result contract, figure contracts,
  pipeline, V2 adapter, and SEC tests.
- Search scope: `polynexus/core/sec*`, `polynexus/core/figures`, relevant
  shared export adapters, and focused tests.
- Expand only for: invalid shared figure schema, export-consumer failure, or
  scientific-semantic ambiguity.
- Report: outcome, changed files, exact verification, limitations, and
  untouched pre-existing changes.

## Acceptance criteria

- [x] A completed SEC run with valid chromatogram data emits a valid shared
  chromatogram definition with source IDs, axes, units, and data snapshots.
- [x] A run with a computed explicit calibration additionally emits valid MWD
  and calibration definitions, including declared calibration provenance and
  mass/number distribution semantics.
- [x] A run with unavailable molecular moments emits no calibration-dependent
  figures while retaining its chromatogram.
- [x] Shared figure publication produces editable SVG, PNG/PDF, CSV snapshots,
  and an Origin-compatible V2 worksheet/curve sidecar from those definitions.
- [x] Mn/Mw/Mz/dispersity remain in the existing metric manifest; their figure
  recipe references the same method/provenance instead of duplicating values.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_sec_figures.py tests/test_sec.py
python scripts/verify.py --task docs/agent/tasks/2026-09-13-sec-gpc-figure-export-closure.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "fix(sec): bind figure summaries to metric manifest" `
  --files polynexus/core/sec_figures.py tests/test_sec_figures.py docs/agent/tasks/2026-09-13-sec-gpc-figure-export-closure.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes: focused SEC coverage passes `11`; targeted Ruff
  and `git diff --check` pass. Structured task verification passes task-card and
  memory checks, Ruff, compile, quality `313`, preprocessing `157`, and
  whitespace.
- Known limitations or follow-up: explicit calibration remains diagnostic only;
  scientific calibration validity, standards/negative controls, uncertainty,
  vendor calibration readers, and capability promotion remain outside scope.
- Pre-existing changes left untouched: agent workflow service, superpowers
  documents, local literature text, and temporary phase-3 test files.
