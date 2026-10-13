---
task_id: 2026-09-04-exploration-run-foundation
kind: architecture
status: implementation_complete_review_required
date: 2026-09-04
title: Add a traceable Core foundation for exploration runs
---

# Add ExplorationRun + ExplorationRunner

## Goal

Make unknown methods and bounded parameter exploration first-class,
content-addressed Core outcomes instead of private AI results.

## Non-goals

- Do not add arbitrary Python/code-string execution, subprocesses, network
  execution, or a Codex sandbox.
- Do not promote an exploration method into the formal capability catalog or
  a paper-ready conclusion.
- Do not add an account system, approval queue, GUI workflow, or change raw
  data.
- Do not alter existing `ComputeRun` provider algorithms or overwrite existing
  project manifests.

## Shared objects and entry points

- Objects: source artifact identity, exploration run, `ProviderResultInput`,
  metric manifest, `ComputationState`, project evidence item.
- AI/Codex/CLI: can later request registered exploration executors and consume
  their shared JSON manifests; this slice exposes no private result DTO.
- GUI: unchanged; a completed run uses the existing read-only `EvidenceItem`
  shape, so a future GUI consumer does not need technique-private state.
- Cross-entry rule: `ExplorationRunner` produces `ProviderResultInput`; the
  evidence adapter consumes it through `EvidenceItem`. Project manifests use
  the existing `.polynexus/research` derived storage boundary.

## Affected boundaries

- Create: `polynexus/core/exploration/` public contracts, registered runner,
  and append-only manifest store.
- Consume: the existing `ComputationState`, `ProviderResultInput`, and
  project `EvidenceItem` contracts without altering their schemas.
- Persist: `.polynexus/research/exploration/`, a documented child of the
  existing research-derived directory rather than a new project-root area.
- Tests: deterministic identity, registry rejection, output/source alignment,
  failure retention, evidence projection, and immutable persistence.

## Implementation plan

1. Define content-addressed executor descriptor, request, and run contracts
   bound to source and implementation hashes.
2. Add an explicit in-process registry and runner that converts only valid
   shared provider results into completed outcomes.
3. Persist immutable run manifests under the existing project research area.
4. Project completed explorations to the existing review-required evidence DTO
   and prove the producer/consumer boundary with focused regression tests.
5. Run task-scoped verification and create one allowlisted checkpoint.

## Context and output budget

- Read first: `docs/agent/memory/README.md`, current state, active work,
  `docs/superpowers/specs/2026-09-04-polynexus-ai-core-design-baseline.md`,
  shared AI/Core and project-evidence contracts.
- Search scope: `polynexus/core/ai_platform`, `polynexus/core/project_workflow`,
  the new `polynexus/core/exploration`, and focused tests.
- Expand only for architecture or a failing shared-contract verification.
- Report the outcome, changed files, exact verification, deferred sandbox and
  package-integration work, and untouched workspace changes.

## Acceptance criteria

- [x] An immutable executor descriptor identifies an implementation hash,
  version, supported techniques, and explicit input/output declarations.
- [x] An immutable request binds source artifact ID/hash, technique, method
  intent, frozen parameters, parent run, and executor implementation identity.
- [x] The runner executes only registered in-process callables; unknown,
  failed, malformed, and mismatched attempts remain traceable outcomes.
- [x] Completed results require a valid, aligned `ProviderResultInput` and
  shared metric manifest; results are never privately summarized by AI.
- [x] Parameters, source hash, or implementation hash produce a distinct run
  identity; persisted manifests are append-only and hash-verified.
- [x] Completed exploration evidence is `review_required` and binds the source
  run/raw artifact without making an interpretation claim.
- [x] Focused contract/evidence/storage tests and task-scoped verification pass.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_exploration_runs.py
python scripts/verify.py --task docs/agent/tasks/2026-09-04-exploration-run-foundation.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add bounded exploration run foundation" `
  --files docs/superpowers/specs/2026-09-04-exploration-run-design.md `
          docs/agent/tasks/2026-09-04-exploration-run-foundation.md `
          polynexus/core/exploration/__init__.py `
          polynexus/core/exploration/contracts.py `
          polynexus/core/exploration/runner.py `
          polynexus/core/exploration/storage.py `
          tests/test_exploration_runs.py
```

## Completion evidence

- Exact commands and outcomes: `python -m pytest -p no:cacheprovider -q
  tests/test_exploration_runs.py` passed (`11 passed`);
  `python scripts/verify.py --task
  docs/agent/tasks/2026-09-04-exploration-run-foundation.md --changed --types`
  passed (Ruff, compile, quality `313 passed`, preprocessing `157 passed`,
  whitespace).
- Known limitations or follow-up: a sandbox, capability promotion, UI/CLI
  routing, and direct package inclusion are deliberately deferred.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  untracked manuscript plans/specs, literature text files, and
  `tests/_tmp_phase3/`.
