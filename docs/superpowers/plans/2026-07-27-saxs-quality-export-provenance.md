# SAXS Quality Export Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 SAXS Export Bundle 中输出 JSON-safe quality evidence snapshot 并保持现有导出与发布契约不变。

**Architecture:** Export 边界只读收集 result/series/AI bridge DTO 的已有字段，统一通过 `_jsonable` 写入 `quality_evidence.json`，然后把相对路径登记进 `bundle_manifest.files`。不把导出层变成分析层。

**Tech Stack:** Python、现有 `saxs_export_bundle`、NumPy JSON normalization、pytest。

---

### Task 1: Failing export regression

**Files:**
- Modify: `tests/test_saxs_export_bundle.py`

- [x] 增加静态质量 evidence、temperature sequence/candidate、AI audit 的失败断言。
- [x] 运行 focused 测试，确认 `quality_evidence.json` 当前缺失。

### Task 2: Quality snapshot implementation

**Files:**
- Modify: `polynexus/core/saxs_export_bundle.py`
- Modify: `tests/test_saxs_export_bundle.py`

- [x] 实现只读 `_quality_evidence_payload`，区分 static/temperature/strain 并保留缺失状态。
- [x] 写出文件并登记 manifest，运行 focused/export/provider 回归。

### Task 3: Verification and checkpoint

**Files:**
- Modify: task card, plan, memory files.

- [x] 运行完整 SAXS、task verifier、`git diff --check` 和 gates。
- [ ] 记录限制并按 allowlist 创建 checkpoint；不 push/merge/deploy。
