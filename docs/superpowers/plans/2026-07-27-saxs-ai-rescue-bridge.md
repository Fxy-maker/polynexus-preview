# SAXS AI Rescue Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将不可信 SAXS AI intent 通过现有 preprocessing 合同转成 candidate-only 计划和受硬门槛约束的 shadow/confirm/auto decision。

**Architecture:** `saxs_ai_rescue.py` 只负责 SAXS intent 强校验、复用 adapter/policy 生成候选、调用通用决策器并输出 JSON-safe bridge DTO。它不调用模型、不运行候选配置、不修改原始数据。

**Tech Stack:** Python dataclasses、现有 `preprocess_optimization` contracts/policy/adapter/decision、pytest。

---

### Task 1: Intent and candidate plan

**Files:**
- Create: `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- Test: `tests/test_saxs_ai_rescue_bridge.py`

- [x] 写失败测试覆盖非 SAXS、保护字段缺失、合法 intent、bounded candidate 和 candidate-only 标记。
- [x] 实现严格 intent 校验和 SAXS rescue plan。
- [x] 运行 focused 测试并确认通过。

### Task 2: Decision bridge

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- Modify: `polynexus/core/saxs_engine/__init__.py`
- Test: `tests/test_saxs_ai_rescue_bridge.py`

- [x] 复用 `decide_preprocess_candidate` 实现 shadow/confirm/tiered-auto 包装。
- [x] 确认 fallback、缺证据和未校准 tiered-auto 永远不可 apply。
- [x] 验证严格 JSON-safe decision。

### Task 3: Verification and checkpoint

**Files:**
- Modify: task card, plan, memory files.

- [x] 运行 focused、preprocessing、完整 SAXS、task verifier 和 `git diff --check`。
- [ ] 记录限制并按 allowlist 创建 checkpoint；不 push/merge/deploy。
