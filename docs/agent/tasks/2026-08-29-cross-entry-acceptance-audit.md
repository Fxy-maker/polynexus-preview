---
task_id: 2026-08-29-cross-entry-acceptance-audit
kind: architecture
status: completed
date: 2026-08-29
title: Verify shared GUI CLI ARS projections
---

# Verify shared GUI CLI ARS projections

## Goal

Verify that GUI, CLI/Codex, and ARS consume the same ComputeRun, evidence,
figure, and result-table projections after the method-sensitivity changes.

## Non-goals

- Do not alter provider algorithms or scientific eligibility.
- Do not modify real datasets or promote review-required evidence.
- Do not claim the historical full-suite release boundary is green.

## Affected boundaries

- EvidencePackageView and chart gallery filters.
- GUI result-table adapters and persistence.
- Project workflow CLI/Codex summaries.
- ARS writing-input and evidence-package projections.

## Implementation plan

1. Run the focused GUI/gallery/result-table and project workflow consumer
   matrix.
2. Run available native GUI automation tests and record environment skips.
3. Record the shared-object audit and known release limitations.

## Acceptance criteria

- [x] GUI/gallery/result-table/CLI/Codex/ARS matrix passes.
- [x] Native GUI automation passes where the environment supports it; skipped
  window-capture cases are recorded explicitly.
- [x] No raw data or immutable evidence is modified.
- [x] Acceptance evidence is recorded in
  `docs/acceptance/2026-08-29-cross-entry-acceptance-audit.md`.

## Verification

```text
pytest -q tests/test_evidence_package_view.py tests/test_chart_gallery_management.py tests/test_plot_gallery_service.py tests/test_results_table_service.py tests/test_analysis_results_table_service.py tests/test_results_table_panel.py tests/test_unified_tables_gui_integration.py tests/test_project_workflow_cli.py tests/test_cli_batch_run_service.py tests/test_ai_native_project_entrypoint.py tests/test_project_workflow_package.py
147 passed

pytest -q tests/test_native_gui_real_route_capture.py tests/test_gui_automation_bridge.py tests/test_gui_automation_mcp.py
9 passed, 17 skipped

python scripts/verify.py --task docs/agent/tasks/2026-08-29-cross-entry-acceptance-audit.md --changed --types
selected checks passed
```
