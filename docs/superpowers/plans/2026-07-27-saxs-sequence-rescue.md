# SAXS Sequence Rescue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已有温度序列替代 `lc` 路径变成可审计候选，并用四个显式门槛验证候选。

**Architecture:** 新的 `saxs_sequence_rescue.py` 只读 `TemperaturePointResult` 的既有路径选择字段，复用质量契约中的 `RescueCandidate` 和 `RescueValidationReport`。`TempSeriesResult` 保存候选字典并在表格中展示候选 ID；不改变原始帧或分析数值。

**Tech Stack:** Python dataclasses、NumPy、现有 SAXS temperature/lc path pipeline、pytest。

---

### Task 1: Candidate and validation contracts

**Files:**
- Create: `polynexus/core/saxs_engine/saxs_sequence_rescue.py`
- Test: `tests/test_saxs_sequence_rescue.py`

- [x] 写 RED 测试：替代路径、缺失/usable primary 路径、四门槛验证和 JSON-safe 输出。
- [x] 运行 focused 测试，确认缺少 `saxs_sequence_rescue` 模块时按预期收集失败。
- [x] 实现只读 candidate builder 和 all-gates validation helper。
- [x] 运行 focused 测试，确认 4 项通过。

### Task 2: Temperature result handoff

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `polynexus/core/saxs_engine/__init__.py`
- Test: `tests/test_saxs_sequence_rescue.py`

- [x] 在 `TempSeriesResult` 增加 candidate 字典列表和按帧 DataFrame 引用。
- [x] 在现有 `select_lc_sequence_path` 完成后生成候选，不覆盖 `lc_nm` 或缺失帧。
- [x] 导出公共 builder/validator，并验证温度/Guinier/模式传播回归。

### Task 3: Verification and checkpoint

**Files:**
- Modify: task card, plan, memory files.

- [x] 运行完整 SAXS 矩阵、任务范围 verifier 和 `git diff --check`。
- [x] 记录实际结果和限制。
- [ ] 用 `scripts/auto_commit.py` 按 allowlist 创建 checkpoint；不 push/merge/deploy。
