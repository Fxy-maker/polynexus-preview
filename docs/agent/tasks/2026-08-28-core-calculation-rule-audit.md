---
task_id: 2026-08-28-core-calculation-rule-audit
kind: scientific
status: implementation_complete_review_required
date: 2026-08-28
title: Audit core calculation rule tiers
---

# Audit core calculation rule tiers

## Goal

Produce an evidence-backed ledger that classifies DSC, FTIR, SAXS, WAXS, and
NMR rules as structural blocks, calculation warnings, or evidence restrictions.

## Non-goals

- Do not change numerical algorithms, quality thresholds, templates, or source data.
- Do not automatically reclassify, delete, or weaken any rule.
- Do not promote diagnostic values into manuscript claims.

## Shared objects and entry points

- Objects: canonical template, `ComputeRun`, evidence package, writing metric.
- AI/Codex/CLI: reads shared projections; no behavior change in this audit.
- GUI: reads shared projections; no behavior change in this audit.
- Cross-entry rule: the audit traces Core producers and their ComputeRun,
  evidence/ARS, CLI/Agent, and GUI consumers without creating a private view.

## Affected boundaries

- Canonical converters and technique providers are inspected as rule producers.
- `ComputeRun` and writing metrics are inspected as public status/evidence
  projections; their behavior remains unchanged in this audit.
- CLI/Agent and GUI are inspected only as consumers of those projections.

## Implementation plan

1. Map the public converter, provider, `ComputeRun`, and evidence entry points
   for each supported technique.
2. Build an evidence-backed rule ledger, tracing every candidate condition from
   producer to its shared public projection.
3. Classify each rule as a structural block, calculation warning, or evidence
   restriction, without changing the current implementation.
4. Publish a prioritized follow-up list of proposed reclassifications for human
   review; each approved item becomes a separate atomic implementation task.

## Context and output budget

- Read first: current memory, this task card, the public ComputeRun/canonical
  contracts, and targeted technique converter/provider/writing symbols.
- Search scope: `polynexus/core`, relevant `tests`, and focused acceptance notes.
- Expand only when a rule's behavior cannot be established from its producer
  and public projection.
- Report: a concise per-technique ledger and prioritized candidates; no raw logs.

## Acceptance criteria

- [x] Every supported technique has an evidence-backed rule ledger.
- [x] Each row separates calculation behavior from evidence eligibility.
- [x] Any recommended downgrade from block to warning has a concrete code/test
  boundary and is not applied automatically.
- [x] Existing historical engineering failures are separated from scientific
  calculation rules.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-28-core-calculation-rule-audit.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "docs(core): audit calculation rule tiers" `
  --files docs/acceptance/2026-08-28-core-calculation-rule-audit.md docs/agent/tasks/2026-08-28-core-calculation-rule-audit.md docs/agent/memory/active-work.md docs/superpowers/plans/2026-08-28-core-calculation-rule-audit.md
```

## Completion evidence

- Acceptance ledger: `docs/acceptance/2026-08-28-core-calculation-rule-audit.md`.
- Focused evidence: DSC/FTIR `42 passed, 2 warnings`; SAXS/WAXS `21 passed`;
  NMR/shared-entry `57 passed, 3 skipped` (see acceptance record for exact commands).
- No new block-to-warning downgrade was justified; finite results already retain
  warning/diagnostic status where the quantity is mathematically defined.
- Known follow-up: human scientific review is required before any future rule
  relaxation; full historical failures remain a separate release-boundary item.
- Pre-existing changes left untouched: `active_run.json`, `runs/`, and
  `tests/_tmp_phase3/`.
