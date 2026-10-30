task_id: 2026-09-04-exploration-run-gates
kind: architecture
status: implementation_complete_review_required
date: 2026-09-04
title: Close ExplorationRun canonical, contract, worker, evidence and promotion gates
---

# Close ExplorationRun canonical, contract, worker, evidence and promotion gates

## Goal

把 ExplorationRun review 中列出的七个执行门槛落实为 Core 合约：

1. request 必须绑定已验证的 CanonicalDataset/CanonicalExperiment；
2. descriptor 输入/输出契约必须参与执行校验；
3. implementation hash 必须由真实执行体派生；
4. Codex/用户代码只能通过隔离、限时、限输出 worker；
5. 自动探索必须有 seed、attempt ID、预算和停止条件；
6. 进入 Evidence Package/ARS 前必须显式精选指标；
7. capability 晋升必须通过独立 replay、标准/负例、不确定度和人工科学审查。

## Non-goals

- 不修改现有技术提供器的数值算法或历史数据；
- 不增加账号、权限、电子签名或重型监管审计；
- 不把探索结果自动晋升为论文结论或正式 capability；
- 不把隔离 worker 描述成对抗宿主机的容器/虚拟机沙箱。

## Shared objects and entry points

- Objects: `CanonicalDataset`, `CanonicalExperiment`, `RawArtifact`,
  `ExplorationRequest`, `ExplorationRun`, `ProviderResultInput`, `EvidenceItem`,
  and `CapabilityDescriptor`.
- AI/Codex/CLI: create requests and consume the shared run/evidence DTOs; no
  private result representation or direct in-process arbitrary-code route.
- GUI: unchanged consumer of shared Core results; future exploration views use
  the same run and curated evidence contracts.
- Cross-entry rule: every entry point uses the Core admission, validator,
  worker, curation, and promotion gates.

## Affected boundaries

- `polynexus/core/exploration/`：canonical admission、严格契约验证、真实实现摘要、worker、自动探索、精选证据和晋升评估；
- 共享对象：`CanonicalDataset`、`CanonicalExperiment`、`RawArtifact`、`ProviderResultInput`、`EvidenceItem`、`CapabilityDescriptor`；
- Consumers：未来 CLI/GUI/Codex 只提交 request 或读取同一 ExplorationRun，不创建私有结果。

## Implementation plan

1. Bind requests to registered canonical admissions and validate descriptor
   input/output contracts before and after execution.
2. Derive implementation identity from the loaded callable, then run non-core
   executors in a spawned, network-denied, filesystem-bounded worker with wall,
   output, and best-effort resource limits.
3. Add seeded automatic exploration with independent attempts, budgets,
   duplicate suppression, and explicit stop reasons.
4. Require explicit metric curation for evidence/ARS projection and add an
   evidence-gated capability promotion assessment with human scientific review.
5. Add focused regression coverage, run the task verifier, update durable
   memory, and create one allowlisted local checkpoint.

## Acceptance criteria

- [x] 缺少 canonical admission、契约不满足、实现摘要不匹配、超时/超限和无效输出均保留为可审计失败/needs-input 运行。
- [x] 自动探索的每次尝试拥有独立 attempt identity，预算耗尽和停止原因可重放。
- [x] Evidence projection 只能包含显式选择的 computed metrics。
- [x] promotion assessment 不能修改历史 run，且只有 replay、标准、负例、不确定度和人工科学审查全部满足时才返回新的 capability descriptor。
- [x] AI/Codex/GUI/CLI 继续共享 Core DTO；未建立账号、重型审计或自动论文结论通道。
- [x] focused tests、`python scripts/verify.py --task docs/agent/tasks/2026-09-04-exploration-run-gates.md --changed --types`、`git diff --check` 通过。

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_exploration_runs.py
python scripts/verify.py --task docs/agent/tasks/2026-09-04-exploration-run-gates.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): close exploration execution gates" `
  --files docs/agent/tasks/2026-09-04-exploration-run-gates.md `
          polynexus/core/exploration/__init__.py `
          polynexus/core/exploration/contracts.py `
          polynexus/core/exploration/canonical.py `
          polynexus/core/exploration/validation.py `
          polynexus/core/exploration/automatic.py `
          polynexus/core/exploration/worker.py `
          polynexus/core/exploration/evidence.py `
          polynexus/core/exploration/promotion.py `
          polynexus/core/exploration/runner.py `
          tests/test_exploration_runs.py
```

## Completion evidence

- Exact commands and outcomes:
  - `python -m pytest -p no:cacheprovider -q tests/test_exploration_runs.py` — 17 passed.
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-04-exploration-run-gates.md --changed --types` — selected checks passed; quality 313 and preprocessing 157 passed.
  - `git diff --check` — passed through the task verifier.
- Known limitations or follow-up: the worker is a bounded Python process, not
  a hostile-kernel container/VM; OS-level deployment isolation, CLI/GUI/Codex
  routing, package integration, and scientific capability review remain
  follow-up work. No exploration result is automatically promoted.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  existing manuscript/spec plans, `li2020.txt`, `lotz2021.txt`, and
  `tests/_tmp_phase3/`.
