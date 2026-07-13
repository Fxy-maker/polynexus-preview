---
kind: decision
status: active
date: 2026-07-13
title: Unified Tables uses immutable presentation contracts
---

## Context

Unified Tables needs to expose structured result values to later services and GUI consumers without copying scientific logic into presentation code or losing raw evidence values during formatting.

## Decision

The first mainline slice defines `TableColumn`, `TableCell`, `ResultTableSection`, `HeroMetric`, and `ResultsTablePresentation` as frozen presentation contracts. Raw values are limited to immutable scalar values, NumPy scalars are normalized to Python scalars, and nested presentation sequences are copied to tuples at construction. Formatting produces display text while preserving raw value, status, tooltip, and provenance separately.

## Alternatives rejected

- Reusing mutable dictionaries/lists directly from technique result payloads would allow later GUI mutation and make export/review state non-deterministic.
- Putting formatting and status decisions in `MainWindow` would duplicate technique-specific logic across GUI handlers.
- Merging the full Unified Tables PR #9 would combine unrelated result, GUI, preprocessing, and editor history and would not provide a reviewable rollback boundary.

## Consequences

Later result services may consume this contract, but they must not reclassify scientific evidence or mutate the underlying `AnalysisResult`. Batch aggregation, export, and GUI integration remain separate slices with their own task cards and tests.

## Evidence

- Task card: `docs/agent/tasks/2026-07-12-unified-tables-contracts.md`
- PR: #11
- Local focused tests: 16 passed
- GitHub quality gate: passed
