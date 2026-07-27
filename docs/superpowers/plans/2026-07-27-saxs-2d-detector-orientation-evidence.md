# SAXS 2D Detector and Orientation Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 2D detector quality 和 anisotropy orientation 建立可追溯的证据基础。

**Architecture:** 质量契约层提供 detector report 与 orientation builder；`analyze_anisotropy` 只消费已有 2D map 和分析结果，保留 legacy 数值字段，并明确 `source_kind`。未知/缺失信息只降级 evidence，不自动修复图像。

**Tech Stack:** Python dataclasses, NumPy, pytest, existing anisotropy pipeline.

---

### Task 1: Write failing 2D evidence tests

**Files:**
- Create: `tests/test_saxs_2d_detector_orientation_evidence.py`

- [x] Test a fully finite raw detector with explicit mask and saturation value, a sector map without saturation, and an unknown source.
- [x] Test empty/invalid detector input, missing orientation metrics, unknown applicability, and strict `contract_json` round-trip.
- [x] Run `pytest tests/test_saxs_2d_detector_orientation_evidence.py -q`; the initial RED was followed by the GREEN implementation.

### Task 2: Implement detector and orientation contracts

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `polynexus/core/saxs_engine/saxs_anisotropy.py`
- Modify: `polynexus/core/saxs_engine/__init__.py`

- [x] Implement `DetectorQualityReport` and `build_detector_quality_report(image, mask=None, saturation_value=None, source_kind="unknown", beam_center=None)` with explicit saturation-only counting and no input mutation.
- [x] Implement `build_orientation_evidence(anisotropy_payload, detector_quality, applicability="unknown", source_ref="")` using existing orientation fields and the detector report reference, capped at `Trend`.
- [x] Add optional `detector_quality_report`/`orientation_evidence` fields to `AnisotropyResult` and attach strict dictionaries in `analyze_anisotropy` before returning, including early/empty returns.
- [x] Export public contracts and run focused tests.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-27-saxs-2d-detector-orientation-evidence.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/superpowers/plans/2026-07-27-saxs-2d-detector-orientation-evidence.md`

- [x] Run the task-scoped verifier, exact SAXS matrix, and `git diff --check`.
- [x] Record exact outcomes and known limitations.
- [x] Use `scripts/auto_commit.py` with only the changed-file allowlist; no push/merge/deploy.
