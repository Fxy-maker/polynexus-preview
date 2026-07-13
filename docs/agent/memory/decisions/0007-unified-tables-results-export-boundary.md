---
kind: decision
status: active
date: 2026-07-13
title: Unified Tables result presentation and export stay behind service boundaries
---

## Context

The immutable table contracts are now in `main`. The next slice must expose generic and technique-specific structured result presentations and export them without putting scientific decisions into GUI handlers or mixing workspace/panel changes into the same PR.

## Decision

Keep structured result templates and adapters in pure GUI services, with `results_table_service.py` dispatching to SAXS and analysis presentation services and preserving a generic fallback for unsupported or failed adapters. Export consumes typed `TableExportData` bundles and writes summary/full/diagnostics outputs to CSV, TSV, or XLSX. Clipboard extraction remains a pure table-to-text helper; Qt clipboard mutation stays at its existing boundary.

## Alternatives rejected

- Merging the complete PR #9 would combine result services with GUI panels, history, preprocessing, and editor changes.
- Recomputing scientific status in export or table code would create a second evidence interpretation path.
- Returning formatted strings as raw values would make typed XLSX export and auditability unreliable.

## Consequences

The GUI panel task can consume these services later without changing the result contract. Generic fallback remains intentionally compatible, while structured adapters expose primary/detail/diagnostic sections and preserve evidence/status fields.

## Evidence

- Task card: `docs/agent/tasks/2026-07-12-unified-tables-results-export.md`
- Source boundary: result template/service/export/clipboard modules only
- Focused matrix: 133 passed; the repository quality gate passed with 280 tests. Changed-file Ruff, compileall, task-card validation, and whitespace checks also passed.
