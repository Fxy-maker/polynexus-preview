---
task_id: 2026-08-30-ai-polymer-capability-platform
kind: architecture
status: active
date: 2026-08-30
title: Build AI-first polymer capability platform foundation
---

# AI-first 高分子通用实验数据与能力平台

## Goal

将 PolyNexus 的共享计算边界扩展为 AI 可发现、可规划、可组合、可拒答且可复算的高分子实验能力平台，同时保留现有技术 provider、GUI、CLI、Agent/Codex、Joint、evidence 和论文 Suite 的公共对象。

## Non-goals

- 本任务不一次实现每个厂家格式或所有长尾高分子测试算法。
- 不重写已经稳定的技术 provider，不放宽科学质量门和人工 promotion。
- 不创建 GUI/CLI/AI 各自私有的结果、状态或 provenance 表示。
- 不把论文写作模块当作计算 Core；论文只是共享能力的一个消费者。

## Shared objects and entry points

- Objects: `DataBlock`, `AxisProvenance`, `CalibrationRef`, `CapabilityDescriptor`, `ComputationState`, `ExecutionGraph`, `ComputeRun`, `metric_manifest`, `EvidencePackage`, `ResearchGraph`, `FigurePlan`.
- AI/Codex/CLI: discovers capabilities, submits plans, reads shared run/evidence projections; never bypasses canonical validation or writes raw artifacts.
- GUI: displays the same DTOs and may collect explicit user decisions; it does not branch on technique-private algorithm state.
- Joint: consumes shared ComputeRun/metric manifest and explicit sample/condition identity; legacy summaries remain compatibility-only and visibly labeled.
- Cross-entry rule: every new public field must have producer tests plus affected AI/CLI and GUI/evidence consumer tests.

## Affected boundaries

- Create: `polynexus/core/ai_platform/` public contracts and planner/execution helpers.
- Modify: `polynexus/core/canonical_experiments/`, `polynexus/core/compute/`, `polynexus/core/project_workflow/`, `polynexus/core/joint/`, Agent/CLI/evidence adapters and package exports.
- Tests: focused contract, planner, canonical replay, ComputeRun, Agent/CLI/GUI/evidence and Joint matrices.
- Durable docs: design spec, this task card, memory checkpoint and acceptance note.

## Implementation plan

1. Add immutable `DataBlock`, axis/calibration, uncertainty-reference and
   four-axis computation-state contracts with deterministic JSON hashes.
2. Add a versioned `CapabilityDescriptor` registry and planner that reports
   executable, blocked, needs-input and not-applicable outcomes.
3. Add a minimal deterministic execution graph with dependency ordering,
   cache keys, node provenance and no-executor behavior for unmet preconditions.
4. Project the new contracts through ComputeRun, metric manifests, Agent/Codex,
   CLI, GUI, evidence and Joint without duplicating scientific calculations.
5. Wrap existing IR temperature-series, detector-image and NMR-compatible data
   in the shared N-D representation, then register honest schemas for DMA,
   rheology, TGA/DTG, SEC/GPC and mechanics.
6. Run focused producer/consumer matrices, the structured verifier and the
   broad boundary check; record limitations and human-review requirements.

## Acceptance criteria

- [ ] `DataBlock` supports scalar, series, matrix/cube and complex data references with dimensions, units, masks, missingness, uncertainty and content hashes.
- [ ] Every physical axis carries `AxisProvenance`; synthetic or inferred axes cannot satisfy quantitative/kinetic/absolute capability gates.
- [ ] A versioned `CapabilityDescriptor` declares input/output contracts, units, preconditions, dependencies, alternatives, uncertainty policy and missing-input actions.
- [ ] A capability discovery/planning call distinguishes executable, blocked, needs-input and not-applicable cases without fabricating values.
- [ ] A four-axis `ComputationState` separates data availability, computability, validity and publication promotion.
- [ ] A minimal deterministic execution graph supports dependency ordering, cache keys and node-level provenance while remaining compatible with `ComputeRun`.
- [ ] Existing `ir`/`ftir` aliases and provider capability projections resolve consistently across ComputeRun, CLI, Agent, GUI and evidence consumers.
- [ ] Existing 1-D/2-D/NMR routes remain behavior-compatible; no diagnostic result is silently promoted.
- [ ] The capability catalog contains the high-priority polymer families (DMA, rheology, TGA/DTG, SEC/GPC, mechanics) as explicit descriptors with honest unsupported/needs-input states; no placeholder scientific values are emitted.
- [ ] Focused producer/consumer tests and the structured verifier pass; architecture and scientific semantics remain marked for human review.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_ai_platform_contracts.py tests/test_ai_capability_planner.py tests/test_execution_graph.py
python -m pytest -p no:cacheprovider -q tests/test_canonical_converter_registry.py tests/test_capability_execution.py tests/test_agent_workflow_contracts.py tests/test_analysis_evidence.py
python scripts/verify.py --task docs/agent/tasks/2026-08-30-ai-polymer-capability-platform.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add AI-first polymer capability foundation" `
  --files docs/superpowers/specs/2026-08-30-ai-polymer-capability-platform-design.md `
           docs/agent/tasks/2026-08-30-ai-polymer-capability-platform.md `
           polynexus/core/ai_platform/__init__.py `
           polynexus/core/ai_platform/contracts.py `
           polynexus/core/ai_platform/planner.py `
           polynexus/core/ai_platform/execution.py `
           tests/test_ai_platform_contracts.py `
           tests/test_ai_capability_planner.py `
           tests/test_execution_graph.py
```

## Completion evidence

- Exact commands and outcomes: no implementation verification has run yet; the task is active.
- Known limitations or follow-up: high-priority polymer descriptors initially expose honest `unsupported`/`needs_input` states; full provider algorithms are separate atomic tasks.
- Pre-existing changes left untouched: untracked `active_run.json`, `runs/`, `tests/_tmp_phase3/`, existing task/plan files and any other paths reported by the initial `git status`.
