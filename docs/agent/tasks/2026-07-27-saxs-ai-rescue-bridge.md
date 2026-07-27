# SAXS AI 救援桥接任务卡

## Goal

让 AI 只能通过现有 SAXS preprocessing 合同提出候选，并在 shadow/confirm/calibrated tiered-auto 三种状态下得到可审计的安全决策。

## Non-goals

- 不实现或调用模型，不修改原始 q-I 数据和 SAXS 数值算法。
- 不绕过现有 evidence hard guards、physical parameter drift 或 fallback guard。
- 不添加 GUI、Workbench、Figure、Manifest 发布动作。

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_ai_rescue_bridge.py`
- `docs/superpowers/specs/2026-07-27-saxs-ai-rescue-bridge-design.md`

## Implementation plan

1. 严格解析并校验 SAXS AI intent，强制保护关键物理特征。
2. 复用 SAXS adapter/policy 生成 candidate-only rescue plan。
3. 复用通用 decision engine，包装 shadow/confirm/tiered-auto 和原始数据保留状态。
4. 运行 focused、preprocessing、完整 SAXS 和结构化 verifier，创建 allowlist checkpoint。

## Acceptance criteria

- [x] 非 SAXS、缺少保护字段或非法 intent 被拒绝。
- [x] 合法 intent 生成的候选均通过 SAXS policy bounded validation。
- [x] shadow 保持 `keep_original`，confirm-only 保持 `request_confirmation`。
- [x] 未校准 tiered-auto 被阻止，校准且所有 hard guards 通过才允许 apply。
- [x] 计划和决策严格 JSON-safe，且标记 `original_preserved`。
- [x] focused、preprocessing、SAXS 和 task verifier 有实际证据。

## Verification

```powershell
python -m pytest tests/test_saxs_ai_rescue_bridge.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-ai-rescue-bridge.md --changed --types
```

## Verification evidence (2026-07-27)

- `python -m pytest tests/test_saxs_ai_rescue_bridge.py -q`: **4 passed**.
- SAXS/preprocessing integration regressions: **48 passed**.
- Complete PowerShell-expanded SAXS matrix: **259 passed, 4 warnings**. The
  warnings are the existing Arial CJK glyph warnings from SAXS figure layout.
- The bridge keeps default shadow decisions at `keep_original`; calibrated
  tiered-auto can expose `apply_allowed` only after the shared hard guards pass.

## Known limitations

本阶段只完成 contract bridge；模型调用、真实候选重算、用户确认和科学/发布验收仍未关闭。

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_ai_rescue_bridge.py`
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-ai-rescue-bridge-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-ai-rescue-bridge.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
