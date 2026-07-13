---
kind: decision
status: active
date: 2026-07-13
title: Unified Tables GUI consumes structured result models through one panel boundary
---

## Context

The contracts and result presentation/export slices are now in `main`. The GUI must display their typed values, status, units, and evidence provenance while preserving existing generic result tables and workspace/history behavior.

## Decision

Use `ResultsTablePanel` as the single result-table view boundary. `MainWindow` and its mixins pass `ResultsTableModel`/`ResultsTablePresentation` data to the panel and retain the panel primary table as the compatibility `_results_table` target for copy, sorting, and legacy export actions. Structured adapters are selected only when an explicit submodule context exists; otherwise the generic fallback remains unchanged. History restore re-renders the stable result payload after restoring technique/submodule context, and language retranslation rebuilds structured headers without changing raw values.

## Alternatives rejected

- Merging the old `codex/unified-tables-panel` branch would reintroduce unrelated PR #9 work across preprocessing, history, editor, and GUI streamlining.
- Adding technique-specific scientific branching to `MainWindow` would duplicate adapter semantics outside the service boundary.
- Replacing the existing `_results_table` compatibility target would break copy/export/default-order paths and legacy tests.

## Consequences

Generic single/multi-sample/batch and joint-report paths keep their existing behavior, while structured models expose primary/detail/diagnostic tables and visible status/provenance. History/persistence restore can reconstruct the current table context without serializing provider objects. GUI layout changes remain independently revertible from the analysis/result services.

## Evidence

- Task card: `docs/agent/tasks/2026-07-12-unified-tables-gui-integration.md`
- Source boundary: result panel, GUI result/output/history/retranslate mixins, focused GUI tests only
- Focused GUI matrix: 225 passed after stale-submodule regression coverage; local quality gate: 280 passed; task-check, changed Ruff, compileall, boundary audit, and diff-check passed. The standard verifier scripts remain user-local and are explicitly waived for this production branch.
