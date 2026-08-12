---
task_id: 2026-08-12-agent-native-pa6-project-evidence-loop
kind: architecture
status: design_review_required
date: 2026-08-12
title: Build a Codex-managed PA6 project evidence loop
---

# Agent-Native PA6 Project Evidence Loop

## Goal

Make PolyNexus usable by Codex as a project-local scientific evidence engine.
For one PA6 paper project, accept an optional research request plus mixed raw
folders, run registered deterministic providers, and create a versioned
`ResearchEvidencePackage` for ARS.

## Non-goals

- Do not require GUI sample/batch entry or replace legacy GUI/database flows.
- Do not copy/change raw PA6 artifacts, laboratory records, or manuscripts.
- Do not permit unvalidated AI numeric transformation or automatic conclusions.
- Do not implement arbitrary vendor formats or all techniques in the initial
  project-service contract slice.

## Affected boundaries

- New project-local service and JSON-safe contracts under `polynexus/core/`.
- Existing canonical experiment and agent-workflow provider boundaries.
- CLI/API for project inspection, planning, execution, and packaging.
- Focused fixtures/tests and external read-only PA6 smoke evidence.

## Acceptance criteria

- [ ] A selected paper root gets derived output only under `.polynexus/`.
- [ ] The index represents formulations, batches, conditions, artifacts,
  measurements, runs, and evidence without a one-file/one-sample assumption.
- [ ] Raw instrument facts override directory/file labels; lower-priority
  mismatches become audit discrepancies.
- [ ] Missing context does not block single-technique analysis.
- [ ] Codex/ARS submit JSON-safe analysis requests and receive `inspect`,
  `plan`, `run`, and `package` results.
- [ ] Run/package identities are immutable and replayable.
- [ ] The DSC PA6 path yields an ARS-readable evidence package with figure/table
  pointers, scope, provenance, status, and limits.
- [ ] Unsupported FTIR/SAXS/WAXS inputs remain explicit blockers until adapters
  are separately implemented.

## Design

`docs/superpowers/specs/2026-08-12-agent-native-project-evidence-loop-design.md`

## Implementation plan

1. Workspace, graph/index, source priority, and analysis-request contracts.
2. Project service over existing agent-workflow/DSC canonical provider path.
3. Versioned DSC evidence package, synthetic replay, and external PA6 smoke.
4. FTIR/SAXS/WAXS adapters as separate template/evidence tasks.

## Verification

The implementation plan will name focused pytest modules. Final task checks:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-12-agent-native-pa6-project-evidence-loop.md --changed --types
git diff --check
```

## Review Requirement

This is an architecture/scientific-evidence boundary. Human review of this
design and implementation plan is required before implementation.
