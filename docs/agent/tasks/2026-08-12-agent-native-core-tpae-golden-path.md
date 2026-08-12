---
task_id: 2026-08-12-agent-native-core-tpae-golden-path
kind: architecture
status: design_review
date: 2026-08-12
title: Establish an agent-native analysis core with a TPAE golden path
---

# Agent-Native Core and TPAE Golden Path

## Goal

Add a stable, technique-neutral analysis contract that an AI agent, CLI, and
future GUI workflow can call without accessing technique-internal state. Deliver
one end-to-end TPAE polymer-characterization workflow as the first production
consumer of that contract.

## Non-goals

- Do not replace `AnalysisResult`, existing technique engines, or existing CLI
  commands in this task.
- Do not redesign the GUI into a chat application.
- Do not promote unreviewed scientific conclusions or infer calibration that is
  absent from original data.
- Do not copy real TPAE data into the repository, push, merge, deploy, or alter
  external experimental files.
- Do not expand the golden workflow to NMR or arbitrary research domains.

## Affected boundaries

- New core agent-workflow contracts under `polynexus/core/`.
- Existing `AnalysisResult` and `AnalysisEvidence` remain the result/evidence
  source for individual technique steps.
- A TPAE workflow adapter composes existing DSC, IR, WAXS, and SAXS paths.
- CLI receives a dedicated agent-workflow entry point; existing single-analysis
  and `ai-tune` commands keep their current behavior.
- GUI remains a consumer of persisted results and is not a first-phase change.
- External TPAE data is referenced only through a manifest with file hashes.

## Implementation plan

1. Define JSON-safe contracts for input artifacts, recipes, run steps, evidence
   limits, inspection, and validation outcomes.
2. Implement a registry-backed agent workflow service with inspect, propose,
   run, validate, and export operations.
3. Add a manifest-only TPAE adapter that maps DSC, FTIR/2D-COS, WAXS, and SAXS
   source artifacts to existing pipeline boundaries.
4. Add a stable CLI command that emits one machine-readable envelope per
   operation without requiring a GUI event loop.
5. Lock the public behavior with focused contract, failure, replay, and
   provenance tests; use synthetic fixtures only in the repository.

## Acceptance criteria

- [ ] `inspect` returns artifact identity, format, file hash, header-derived
  facts, and explicit unsupported/missing reasons.
- [ ] `propose` returns a JSON-safe, versioned, replayable recipe and never
  mutates input files or engine configuration.
- [ ] `run` produces a run envelope whose technique steps reference existing
  `AnalysisResult`/evidence outputs without exposing engine internals.
- [ ] `validate` distinguishes pass, review-required, and blocked outcomes;
  each outcome records allowed and disallowed conclusion scopes.
- [ ] `export` writes a self-contained manifest/result bundle outside the input
  data directory and records every artifact/recipe hash.
- [ ] A missing file, unsupported format, missing calibration, or failed step
  is represented as structured data rather than an unclassified exception.
- [ ] The TPAE manifest can refer to external data but no real dataset is
  committed to this repository.
- [ ] Existing `AnalysisResult.to_dict()`, current CLI routes, and GUI-facing
  engine boundaries retain backward-compatible behavior.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_agent_workflow_contracts.py tests/test_tpae_golden_workflow.py tests/test_agent_workflow_cli.py
python scripts/verify.py --task docs/agent/tasks/2026-08-12-agent-native-core-tpae-golden-path.md --changed --types
git diff --check
```

## Pre-existing workspace state

The initial worktree had no tracked modifications. Git reported only existing
unreadable historical test-artifact directories; they are not part of this
task and must remain untouched.
