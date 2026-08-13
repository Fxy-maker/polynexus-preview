---
task_id: 2026-08-13-unified-canonical-evidence-provenance
kind: architecture
status: implementation_complete_review_required
date: 2026-08-13
title: Register canonical technique conversion and scoped evidence provenance
---

# Unified Canonical Conversion and Evidence Provenance

## Goal

Make the project workflow use a validated canonical conversion boundary for
DSC, FTIR, SAXS, and WAXS, while ensuring each evidence item and technique
index expose only their own limitations and provenance.

## Non-goals

- Do not change DSC, IR, SAXS, or WAXS calculation algorithms.
- Do not add sample/batch/formulation inference or cross-technique scientific
  conclusions.
- Do not build ARS draft generation or GUI surfaces in this task.
- Do not modify raw PA6 data or existing real-data regression sources.

## Affected boundaries

- `polynexus/core/canonical_experiments/`: generic converter registry and
  versioned technique template contracts.
- `polynexus/core/project_workflow/`: recipe proposal and replay provenance.
- `polynexus/core/agent_workflow/`: canonical replay before provider execution.
- `polynexus/core/project_workflow/package.py`: technique-local limitations and
  provenance projection.
- Focused tests, acceptance evidence, and durable memory.

## Acceptance criteria

- [x] A registered DSC, IR, SAXS, or WAXS source produces a canonical template
  whose source artifact ID, conversion hash, and content hash are valid.
- [x] IR, SAXS, and WAXS project routes cannot execute directly from a raw
  single-file artifact when their canonical converter is unavailable or the
  replayed conversion mismatches.
- [x] Existing provider algorithms receive the same source representation and
  remain behaviorally unchanged apart from canonical provenance.
- [x] Each run manifest records the template and conversion hash for every
  canonical provider step.
- [x] A technique index and writing evidence item contain only limitations from
  the matching technique/run, never package-wide unrelated limitations.
- [x] Focused regressions cover success, unregistered converter, mismatch,
  technique-local limitation isolation, and existing DSC replay compatibility.
- [x] A bounded external PA6 four-technique read-only replay records all four
  template identities without claiming scientific publication readiness.

## Implementation plan

1. Add a closed canonical converter registry and narrow IR, SAXS, and WAXS
   converter contracts alongside the existing DSC converter.
2. Update project technique adapters and agent-workflow replay validation so
   every selected single-file route carries and reproduces its template.
3. Add technique-local provenance/limitation projection to the evidence package
   and regressions proving unrelated package limitations cannot leak.
4. Run focused tests and a bounded external PA6 four-technique replay; record
   acceptance evidence and update durable work memory.
5. Run the structured verifier, inspect the cumulative diff, and create one
   local allowlisted checkpoint commit without pushing or merging.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_canonical_experiment_templates.py tests/test_project_technique_adapters.py tests/test_project_workflow_package.py tests/test_ai_native_project_entrypoint.py
python scripts/verify.py --task docs/agent/tasks/2026-08-13-unified-canonical-evidence-provenance.md --changed --types
git diff --check
```

## Required evidence

- Acceptance note records the exact external read-only PA6 command, package
  path, four technique/template identities, and review limitations.
- A local `scripts/auto_commit.py` checkpoint uses an explicit allowlist after
  verification; it never pushes or merges.
