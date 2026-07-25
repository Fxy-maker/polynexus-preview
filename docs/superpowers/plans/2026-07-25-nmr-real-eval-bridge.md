# NMR real-engine evaluation bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 NMR 四个分区接入现有真实 engine 评测桥接并保持可追溯输出。

**Architecture:** 只扩展 `tests/eval/runner.py` 的 technique dispatch 和 NMR 输出适配，
不改 NMR 科学核心；一个 focused test 用 engine double 锁定真实调用、provenance 和
峰位/质量字段，既有四技术 eval 作为兼容回归。

**Tech Stack:** Python, pytest, NumPy, existing EvalRunner contracts.

---

### Task 1: Lock the bridge contract

**Files:**

- Create: `tests/eval/test_runner_real_nmr.py`

- [x] 写出 NMR solid 13C case，断言四项行为：`_uses_real_engine` 为真、调用
  `nmr.solid_c`、输出 `peak_shifts`/`n_peaks`/`Xc_pct`、保留 engine/submodule。
- [x] 运行 `python -m pytest tests/eval/test_runner_real_nmr.py -q`，确认在未加入
  NMR allowlist 时失败。

### Task 2: Implement minimum dispatch

**Files:**

- Modify: `tests/eval/runner.py`

- [x] 将 `nmr.liquid_h`, `nmr.liquid_c`, `nmr.solid_h`, `nmr.solid_c` 加入
  allowlist，并在 real dispatch 中应用 NMR config aliases。
- [x] 从首个 `NMRResult` 提取稳定评测字段，全部经过 `_to_plain_value`。
- [x] 重跑 focused NMR test，确认绿灯。

### Task 3: Compatibility verification and checkpoint

**Files:**

- Modify: `docs/agent/memory/active-work.md` only with durable evidence.

- [x] 运行 Ruff 和 NMR + IR/DSC/SAXS/WAXS focused eval matrix。
- [ ] 运行 task-scoped `scripts/verify.py`。
- [ ] 用显式 allowlist 调用 `scripts/auto_commit.py` 创建原子 checkpoint。
