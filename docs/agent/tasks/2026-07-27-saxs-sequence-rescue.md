# SAXS 序列级救援任务卡

## Goal

让变温 SAXS 能审计已有替代方法路径，并在重新分析后通过显式硬门槛前保持候选态。

## Non-goals

- 不修改原始 q-I 数据或已有温度点。
- 不插值或补造缺失温度帧，不改变相变阈值。
- 不接入 AI 自动接受，不改变 Figure/Manifest 发布角色。

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_sequence_rescue.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_sequence_rescue.py`
- `docs/superpowers/specs/2026-07-27-saxs-sequence-rescue-design.md`

## Implementation plan

1. 为已有替代 `lc` 路径生成只读、JSON-safe 的 `RescueCandidate`，并为四个显式门槛生成 accepted/rejected `RescueValidationReport`。
2. 在 `TempSeriesResult` 保存候选并在 DataFrame 按帧引用候选 ID，保持原始帧和缺失位置不变。
3. 运行 focused、温度/Guinier/模式传播、完整 SAXS 和结构化 verifier，记录证据并创建 allowlist checkpoint。

## Acceptance criteria

- [x] 只把现有 non-primary `lc` 路径包装成 deterministic、JSON-safe candidate。
- [x] 候选携带帧位置、轴值、原始/建议值、来源和 `preserve_missing_frames`。
- [x] 空帧、缺失帧和已有 usable primary 帧不生成候选。
- [x] hard、physical、data-preservation、sequence 四个门槛全部显式通过后才 accepted。
- [x] `TempSeriesResult` 和 DataFrame 保留候选引用，不覆盖原始数值。
- [x] focused、温度/Guinier/模式传播、完整 SAXS 和结构化 verifier 有实际证据。

## Verification

```powershell
python -m pytest tests/test_saxs_sequence_rescue.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-sequence-rescue.md --changed --types
```

## Verification evidence (2026-07-27)

- `python -m pytest tests/test_saxs_sequence_rescue.py tests/test_saxs_temperature_guinier_evidence.py -q`: **8 passed**.
- Temperature/Guinier/mode propagation regressions: **26 passed**.
- Complete PowerShell-expanded SAXS matrix: **255 passed, 4 warnings**. The
  warnings are the existing Arial CJK glyph warnings from SAXS figure layout.
- Task-scoped verifier passed: quality gate **282 passed**, preprocessing gate
  **103 passed**, plus task-card, memory, Ruff, compile, type and whitespace
  checks.
- The candidate-only path preserves missing frames and legacy values; no
  candidate is automatically applied.

## Known limitations

本阶段不执行候选重新分析，也不校准相变附近的实验阈值；候选仍需后续确定性重算、人工科学审查和 AI shadow/confirm 阶段。

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_sequence_rescue.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_sequence_rescue.py`
- `tests/test_saxs_temperature_guinier_evidence.py`
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-sequence-rescue-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-sequence-rescue.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
