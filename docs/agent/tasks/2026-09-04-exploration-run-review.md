---
task_id: 2026-09-04-exploration-run-review
kind: security
status: implementation_complete_review_required
date: 2026-09-04
title: Review ExplorationRun expansion boundaries
---

# ExplorationRun expansion boundary review

## Goal

审查 ExplorationRun 基础能力在安全、架构和科学语义上是否可以进入
Codex/GUI/CLI、自动探索、证据打包和 capability 晋升阶段，并给出放行门槛。

## Non-goals

- 不实现代码沙箱、worker、CLI/GUI 入口或自动搜索器。
- 不修改现有计算算法、ComputeRun、Evidence Package 或 capability catalog。
- 不把 exploration 结果自动提升为 Results、Discussion 或正式 capability。

## Affected boundaries

- Reviewed: `polynexus/core/exploration/` and its shared
  `ProviderResultInput`/`ComputationState`/`EvidenceItem` boundaries.
- Reviewed consumers: future Codex, GUI, CLI, automatic exploration,
  `ProjectEvidencePackager`, ARS and `CapabilityDescriptorRegistry` paths.
- Output: security/architecture/scientific review spec and durable acceptance
  notes; no runtime code changes.

## Implementation plan

1. Inspect current ExplorationRun contracts, runner and storage for execution,
   provenance, integrity and evidence-boundary assumptions.
2. Compare those assumptions with the PolyNexus AI/Core baseline and existing
   canonical, package and capability contracts.
3. Classify findings as P1/P2 security, architecture or scientific-semantic
   blockers and define a staged recommendation.
4. Record explicit go/no-go decisions and deferred human-review boundaries.

## Acceptance criteria

- [x] Current v1 trusted-executor boundary is distinguished from an untrusted
  Codex-code sandbox.
- [x] Canonical provenance, descriptor contract, resource, replay, evidence and
  promotion gaps are identified with file/line evidence.
- [x] A staged recommendation preserves AI flexibility without bypassing Core.
- [x] No runtime or scientific result is changed by the review.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-09-04-exploration-run-review.md --changed --types
git diff --check
```

## Completion evidence

- Review report: `docs/superpowers/specs/2026-09-04-exploration-run-review.md`.
- Findings: 5 P1 and 10 P2 security/architecture/scientific issues or gates.
- Overall: trusted built-in development use is conditionally allowed; Codex
  arbitrary code, formal package inclusion and automatic capability promotion
  are not allowed yet.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  manuscript plans/specs, literature files, and `tests/_tmp_phase3/`.
