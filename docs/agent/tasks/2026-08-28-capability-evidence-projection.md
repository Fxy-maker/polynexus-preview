---
task_id: 2026-08-28-capability-evidence-projection
kind: architecture
status: implementation_complete_review_required
date: 2026-08-28
title: Project canonical capability results into evidence
---

# Project canonical capability results into evidence

## Goal

Expose completed generic canonical capability items through Agent steps,
project evidence, and the ARS citation ledger using the existing shared
`ComputeRun` producer.

## Non-goals

- No provider algorithm or scientific eligibility changes.
- No new material database or automatic paper-role promotion.
- No raw-data copying or alternate entry-point calculations.

## Affected boundaries

- `polynexus/core/agent_workflow/service.py`: public step projection.
- `polynexus/core/project_workflow/writing_metrics.py`: generic metric
  extraction with item provenance.
- `tests/test_capability_evidence_projection.py` and existing package tests.

## Implementation plan

1. Add a failing project-package test requiring capability metrics and their
   deterministic provenance link.
2. Include JSON-safe capability item records in `WorkflowStepResult` summaries.
3. Extract completed capability result fields into diagnostic citation metrics;
   skip non-completed items without fabricating values.
4. Run focused project/capability/package tests and the structured verifier.
5. Record acceptance and checkpoint only the allowlisted files.

## Acceptance criteria

- [x] Completed canonical capability items appear in public step summaries.
- [x] Evidence packages expose generic capability citation metrics.
- [x] Metric provenance includes capability item id and source locator.
- [x] Existing package and historical compatibility tests remain green.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_capability_evidence_projection.py tests/test_capability_execution.py tests/test_project_workflow_package.py
python scripts/verify.py --task docs/agent/tasks/2026-08-28-capability-evidence-projection.md --changed --types
git diff --check
```

## Completion evidence

- Focused capability/evidence/project matrix: **104 passed, 3 skipped**.
- Task verifier, Ruff, compile, quality (**311**) and preprocessing (**157**)
  gates passed.
- Capability metrics remain `diagnostic_only`; publication promotion is still a
  separate ARS/human decision.
