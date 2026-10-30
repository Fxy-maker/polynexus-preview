---
task_id: 2026-09-05-ai-validation-readiness
kind: architecture
status: implementation_complete_review_required
date: 2026-09-05
title: Add AI-readable capability validation readiness
---

# Add AI-Readable Capability Validation Readiness

## Goal

Expose one shared, content-addressed readiness result that lets AI/Codex see
which capability-promotion evidence is satisfied, missing, or failed; which
preparation actions can be automated after real inputs arrive; and when human
scientific review is the only remaining gate.

## Non-goals

- Do not let AI promote a capability, reinterpret a diagnostic output, or
  fabricate independent replay, standard-sample, negative-control, or
  measurement-uncertainty evidence.
- Do not add identity, account, signature, approval-queue, GUI, or persistence
  requirements.
- Do not change TGA processing, synthetic replay status, or capability maturity.
- Do not make ordinary ComputeRun, quick analysis, or exploration execution
  wait for promotion readiness.

## Shared objects and entry points

- Objects: existing `CapabilityDescriptor` and `CapabilityPromotionEvidence`,
  plus an additive `CapabilityPromotionReadiness` DTO.
- AI/Codex: reads the same readiness projection and may prepare/run registered
  calculations only after admitted data is supplied.
- CLI/GUI: unchanged; future consumers use the same public DTO rather than a
  TGA- or AI-private status object.
- Cross-entry rule: readiness is derived only from the existing shared evidence
  records and never changes the descriptor or calls `promote()`.

## Affected boundaries

- Generic exploration capability-promotion contract and public exports.
- Focused exploration regression tests using a TGA descriptor as a consumer.
- No canonical, ComputeRun, evidence-package, GUI, or persistence schema change.

## Implementation plan

1. Add an immutable JSON-safe readiness DTO derived from a descriptor and the
   existing promotion evidence records.
2. Classify required evidence kinds as satisfied, missing, or failed and expose
   deterministic AI preparation actions plus the final human-review condition.
3. Add a service method that returns readiness without mutating or promoting a
   descriptor.
4. Add regressions for empty, partial, evidence-complete, duplicate, and TGA
   consumer inputs.
5. Record the boundary and verify focused plus structured quality gates.

## Acceptance criteria

- [x] AI can distinguish absent evidence from present-but-failed evidence.
- [x] Readiness identifies only preparatory actions for AI and never reports a
  descriptor as automatically promotable.
- [x] A complete evidence set is marked ready for human scientific review, not
  available or promoted.
- [x] The DTO is deterministic, JSON-safe, content-addressed, and rejects
  duplicate/evidence-type-invalid input.
- [x] TGA can consume the generic path without a private promotion contract.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_exploration_runs.py tests/test_tga_validation.py
python scripts/verify.py --task docs/agent/tasks/2026-09-05-ai-validation-readiness.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add ai validation readiness" `
  --files docs/agent/tasks/2026-09-05-ai-validation-readiness.md `
          polynexus/core/exploration/promotion.py `
          polynexus/core/exploration/__init__.py `
          tests/test_exploration_runs.py docs/agent/memory/active-work.md `
          docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes:
  - Initial focused test failed collection because the readiness DTO had not
    yet been exported.
  - `python -m pytest -p no:cacheprovider -q tests/test_exploration_runs.py
    tests/test_tga_validation.py` - 22 passed.
  - `python -m ruff check polynexus/core/exploration/promotion.py
    polynexus/core/exploration/__init__.py tests/test_exploration_runs.py` -
    passed.
  - `python scripts/verify.py --task
    docs/agent/tasks/2026-09-05-ai-validation-readiness.md --changed --types`
    - passed Ruff, compile, quality 313, preprocessing 157, and whitespace.
  - `git diff --check` - passed.
- Known limitations or follow-up: AI can organize and execute only from
  admitted real inputs. It cannot create independent experimental evidence or
  complete the human scientific review gate.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  manuscript plans/specs, `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/`.
