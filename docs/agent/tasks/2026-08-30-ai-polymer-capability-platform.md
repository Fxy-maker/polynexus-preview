---
task_id: 2026-08-30-ai-polymer-capability-platform
kind: architecture
status: completed_review_required
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

- [x] `DataBlock` supports scalar, series, matrix/cube and complex data references with dimensions, units, masks, missingness, uncertainty and content hashes.
- [x] Every physical axis carries `AxisProvenance`; synthetic or inferred axes cannot satisfy quantitative/kinetic/absolute capability gates.
- [x] A versioned `CapabilityDescriptor` declares input/output contracts, units, preconditions, dependencies, alternatives, uncertainty policy and missing-input actions.
- [x] A capability discovery/planning call distinguishes executable, blocked, needs-input and not-applicable cases without fabricating values.
- [x] A four-axis `ComputationState` separates data availability, computability, validity and publication promotion.
- [x] A minimal deterministic execution graph supports dependency ordering, cache keys and node-level provenance while remaining compatible with `ComputeRun`.
- [x] Existing `ir`/`ftir` aliases and provider capability projections resolve consistently across ComputeRun, CLI, Agent, GUI and evidence consumers.
- [x] Existing 1-D/2-D/NMR routes remain behavior-compatible; no diagnostic result is silently promoted.
- [x] The capability catalog contains the high-priority polymer families (DMA, rheology, TGA/DTG, SEC/GPC, mechanics) as explicit descriptors with honest unsupported/needs-input states; no placeholder scientific values are emitted.
- [x] Focused producer/consumer tests and the structured verifier pass; architecture and scientific semantics remain marked for human review.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_ai_platform_contracts.py tests/test_ai_platform_contract_hardening.py tests/test_ai_capability_planner.py tests/test_execution_graph.py tests/test_canonical_nd_adapters.py tests/test_ai_platform_cross_entry.py tests/test_capability_catalog.py tests/test_evidence_package_view.py tests/test_group_result_table.py tests/test_project_workflow_package.py tests/test_project_writing_metrics.py
python scripts/verify.py --task docs/agent/tasks/2026-08-30-ai-polymer-capability-platform.md --changed --types
python scripts/verify.py --changed --types --full --boundary
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

- Focused producer/consumer matrix: `207 passed in 10.78s`.
- Task verifier: `python scripts/verify.py --task docs/agent/tasks/2026-08-30-ai-polymer-capability-platform.md --changed --types` passed Ruff, `py_compile`, quality gate `313 passed`, preprocessing `157 passed`, and whitespace checks (exit 0).
- Broad boundary check: `python scripts/verify.py --changed --types --full --boundary` returned `4492 passed, 38 failed, 25 skipped, 27 warnings`. The failures are pre-existing GUI/figure/SAXS/TPAE baselines outside this goal; they are not treated as evidence of a green release boundary.
- `python -m compileall -q polynexus` and `git diff --check` both passed. A repository-wide standalone `ruff check` still reports 644 legacy findings in untouched modules; the task-scoped verifier's changed-file checks passed.
- Known limitations/follow-up: DMA/DMTA, rheology, TGA/DTG, SEC/GPC and mechanics descriptors intentionally report `unsupported`/`needs_input` until deterministic providers are implemented. N-D IR/SAXS/WAXS/NMR descriptors are contract-first and experimental; real provider binding, calibration-content validation, and broader replay fixtures remain separate atomic tasks.
- Architecture, schema, promotion policy, and scientific semantics require human review before mainline merge or publication use.
- Pre-existing changes left untouched: untracked `active_run.json`, `runs/`, `tests/_tmp_phase3/`, elastomer task/plan/spec/acceptance files, paper scripts/tests, memory edits, and any other paths reported by the initial `git status`.
