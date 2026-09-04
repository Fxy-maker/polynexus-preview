---
task_id: 2026-09-04-polynexus-ai-core-design-baseline
kind: architecture
status: implementation_complete_review_required
date: 2026-09-04
title: Formalize the PolyNexus AI/Core design baseline
---

# Formalize the PolyNexus AI/Core design baseline

## Goal

Formalize the product baseline that PolyNexus is a Codex/AI-oriented polymer
research compute middleware: AI explores broadly, while the deterministic Core
owns calculation, provenance, structure, and evidence.

## Non-goals

- Do not change algorithms, result values, provider behavior, or supported
  technique contracts.
- Do not add account systems, multi-user permissions, e-signatures, or heavy
  regulatory controls.
- Do not change runtime data, local evidence, or existing user worktrees.

## Shared objects and entry points

- Objects: project, run, chart, evidence package, export, and manuscript DTOs
  are unchanged; this task only formalizes their product policy.
- AI/Codex/CLI: unchanged; the document explains how they share the same Core
  pipeline.
- GUI: unchanged.
- Cross-entry rule: the same scientific pipeline and evidence boundary apply to
  every entry point.

## Affected boundaries

- Product boundary: the AI/Core division of responsibility.
- Scientific boundary: what gets computed, what gets curated, and what may be
  promoted into evidence.
- Expansion boundary: first-wave techniques, exploration runs, and optional
  plugins.
- Runtime boundary: documentation only; no source code or live data changes.

## Implementation plan

1. Draft the baseline spec from the agreed principles in the user discussion
   and the existing product contract.
2. Make the document explicit about the shared pipeline, exploration policy,
   evidence curation boundary, and deferred implementation questions.
3. Record the decision in project memory so later design work can reuse the
   same baseline instead of restating it.
4. Validate the task card, inspect the diff, and create one local checkpoint.

## Context and output budget

- Read first: `AGENTS.md`, `README.md`, current memory files, and the existing
  design-spec style under `docs/superpowers/specs/`.
- Search scope: `docs/superpowers/specs`, `docs/agent/tasks`, and the current
  product contract only.
- Expand only for: a mismatch with the product contract, a missing baseline
  principle, or a verification failure.
- Report: changed docs, exact verification result, limitations, and untouched
  pre-existing changes.

## Acceptance criteria

- [ ] The spec clearly states the AI/Core division of labor.
- [ ] The spec names the shared pipeline from raw artifact to ARS.
- [ ] The spec defines the calculability policy, exploration-run policy, and
  evidence-curation boundary.
- [ ] The spec states the first-wave technique set and the explicit
  non-goals.
- [ ] The task leaves existing runtime data and unrelated worktree changes
  untouched.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-09-04-polynexus-ai-core-design-baseline.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "docs(spec): formalize AI core design baseline" `
  --files docs/superpowers/specs/2026-09-04-polynexus-ai-core-design-baseline.md docs/agent/tasks/2026-09-04-polynexus-ai-core-design-baseline.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes:
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-04-polynexus-ai-core-design-baseline.md --changed --types` — passed: task/memory checks, Ruff, compile, quality gate (313 passed), preprocessing gate (157 passed), and whitespace check.
  - `git diff --check` — passed through the structured verifier.
- Known limitations or follow-up:
  - This is a product-policy baseline, not an implementation of `ExplorationRun`, caching, QC thresholds, or an Origin plugin.
  - Architecture and scientific-semantics review remains required before downstream implementation merges.
- Pre-existing changes left untouched:
  - `polynexus/core/agent_workflow/service.py`, the pre-existing untracked plans/specs, `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/` remain outside this checkpoint.
