---
task_id: 2026-08-12-agent-native-core-tpae-golden-path
kind: architecture
status: implementation_complete
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

- [x] `inspect` returns artifact identity, format, file hash, header-derived
  facts, and explicit unsupported/missing reasons.
- [x] `propose` returns a recursively immutable, JSON-safe, versioned,
  replayable recipe and never mutates input files or engine configuration.
- [x] `run` produces a run envelope whose technique steps reference existing
  `AnalysisResult`/evidence outputs without exposing engine internals.
- [x] `validate` distinguishes pass, review-required, and blocked outcomes;
  each outcome records allowed and disallowed conclusion scopes.
- [x] `export` writes a self-contained manifest/result bundle outside the input
  data directory, records every artifact/recipe hash, and preserves public
  figure references without copying raw inputs or figure assets.
- [x] A missing file, unsupported format, missing calibration, or failed step
  is represented as structured data rather than an unclassified exception.
- [x] The TPAE manifest can refer to external data but no real dataset is
  committed to this repository.
- [x] Existing `AnalysisResult.to_dict()`, current CLI routes, and GUI-facing
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

## Implementation evidence

- `polynexus.core.agent_workflow` now provides immutable JSON-safe artifact,
  recipe, proposal, run, step-result, and evidence contracts. Recipe hashes are
  canonical SHA-256 identities; legacy non-finite public result scalars are
  normalized to JSON `null` only at the new agent boundary.
- TPAE manifest inspection preserves separate evidence for EDF geometry and
  absent background handling. It does not infer a calibration or discard
  coordinate evidence because absolute intensity evidence is incomplete.
- `tpae.characterization.v1` requires an isothermal DSC directory sequence,
  validates declared technique/step compatibility, and orders optional FTIR,
  WAXS, and SAXS steps deterministically. Directory identities are a stable
  manifest hash of sorted relative paths and child hashes; replays compare those
  artifact hashes before any provider call.
- Default execution invokes existing `get_engine(...).run_pipeline(...)` public
  boundaries and records only `AnalysisResult.to_dict()`, public evidence, and
  figure references. Provider error logs become failed workflow steps even when
  legacy validation defaults are true; no engine-private arrays are exposed.
- Each executed run receives a local HMAC execution receipt. Validation and
  export verify its recipe, status, reasons, step summaries, evidence, and
  validation state before writing provenance; fabricated runs or edited evidence
  are blocked. Duplicate artifacts for one technique are rejected to keep every
  step's raw input unambiguous.
- `polynexus agent-workflow {inspect,propose,run,validate,export}` prints one
  JSON envelope, requires an explicit output directory, can replay a persisted
  recipe without a manifest, persists a replayable `run.json`, and exports JSON
  evidence without copying raw inputs. Run/export destinations inside input-data
  directories are rejected.
- Review repairs are regression-covered: nested recipe mappings cannot mutate,
  directory hashes are stable/change-sensitive, mismatched manifest techniques
  and non-directory DSC input block early, raw-data output writes block, engine
  error logs fail, figure references export as a manifest, and fabricated or
  tampered persisted runs cannot validate or export.
- Focused agent/TPAE/CLI/legacy-CLI suite: `47 passed`.
- Structured verifier passed on 2026-08-12: Ruff, py_compile, task/memory
  checks, quality gate `303 passed`, preprocessing gate `157 passed`, and
  whitespace check. No real TPAE scientific acceptance is claimed; an external
  read-only manifest replay and human scientific review remain required.
