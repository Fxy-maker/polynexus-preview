# SAXS Mode Evidence Propagation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让变温和应变每个观测帧携带单帧质量/方法证据，同时保留各自科学边界。

**Architecture:** point result DTO 只消费 `SAXSResult` 已有的 JSON-safe 字典；温度和应变模块分别传播，不共享序列算法。失败分支不创建证据，DataFrame 只增加等级摘要列。

**Tech Stack:** Python dataclasses, NumPy, pandas, pytest, existing SAXS series pipelines.

---

### Task 1: Write failing propagation tests

**Files:**
- Create: `tests/test_saxs_mode_evidence_propagation.py`

- [ ] Build fake `SAXSResult` payloads carrying `data_quality_report` and four `metric_evidence` entries.
- [ ] Write temperature success/failure tests asserting frame-specific payloads, unchanged frame count/order, and `Metric_evidence_levels` output.
- [ ] Write strain success/failure tests asserting the same propagation while no temperature sequence field appears.
- [ ] Run `pytest tests/test_saxs_mode_evidence_propagation.py -q`; confirm RED because point DTOs do not expose the new fields.

### Task 2: Propagate evidence in temperature and strain DTOs

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`

- [ ] Add `metric_evidence: Dict | None = None` to `TemperaturePointResult` and `StrainPointResult`; add `data_quality_report` to strain.
- [ ] In each successful `analyze_single` branch assign `getattr(saxs_result, "metric_evidence", None)` and `getattr(saxs_result, "data_quality_report", None)`; leave both `None` on exceptions.
- [ ] In each `to_dataframe()` format sorted `key:level` pairs as `Metric_evidence_levels`, returning `None` for absent payloads.
- [ ] Run focused tests and existing temperature/strain status tests.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-27-saxs-mode-evidence-propagation.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/superpowers/plans/2026-07-27-saxs-mode-evidence-propagation.md`

- [ ] Run the task-scoped verifier with an external basetemp, exact SAXS matrix, and `git diff --check`.
- [ ] Record exact outcomes and known limitations.
- [ ] Use `scripts/auto_commit.py` with only the changed-file allowlist; no push/merge/deploy.

## Execution status (2026-07-27)

Implementation and verification are complete. Temperature and strain point
results now retain frame-local quality and method evidence without interpolation;
the focused propagation matrix is `26 passed`, the exact SAXS matrix is `244
passed` with four existing warnings, and the structured verifier passes quality
`282`/preprocessing `103`. The atomic checkpoint follows the documented
allowlist.
