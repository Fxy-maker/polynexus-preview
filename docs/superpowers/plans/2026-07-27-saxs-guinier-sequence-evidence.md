# SAXS Guinier Sequence Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将逐帧 Guinier 证据汇总为不改变原始帧的变温序列趋势/连续性证据。

**Architecture:** 在现有质量契约模块新增不可变序列 DTO 和纯构造器；变温服务在逐帧分析结束后只传递温度数组与证据字典，并将返回的严格 JSON-safe 摘要挂到 `TempSeriesResult`。连续性检查只生成诊断元数据，不参与单帧物理结论或自动救援。

**Tech Stack:** Python dataclasses, NumPy, pytest, existing SAXS temperature pipeline.

---

### Task 1: Add sequence contract tests

**Files:**
- Create: `tests/test_saxs_guinier_sequence_evidence.py`

- [ ] Write tests for clean two-point trend, empty/single/all-failed inputs, missing frame positions, invalid/duplicate temperatures, and strict `contract_json` serialization.
- [ ] Add a monotonic multi-frame test asserting all input positions remain represented and no continuity outlier is reported for a steady trend.
- [ ] Add an isolated-jump test asserting a `continuity_break_indices` entry and an explanatory reason code without requiring a frame mutation.
- [ ] Run `pytest tests/test_saxs_guinier_sequence_evidence.py -q`; confirm RED because the sequence DTO/builder is absent.

### Task 2: Implement the immutable sequence evidence contract

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `polynexus/core/saxs_engine/__init__.py`

- [ ] Add `GuinierSequenceEvidence` fields for frame counts, valid/missing/diagnostic positions, temperature defects, continuity diagnostics, ranges, level, reasons, and nested metric evidence.
- [ ] Add the public shape below to `saxs_quality_contracts.py`, preserving the existing `to_dict/from_dict` and strict-JSON conventions:

```python
@dataclass(frozen=True)
class GuinierSequenceEvidence:
    frame_count: int = 0
    finite_temperature_count: int = 0
    valid_frame_count: int = 0
    missing_frame_indices: tuple[int, ...] = ()
    diagnostic_frame_indices: tuple[int, ...] = ()
    invalid_temperature_indices: tuple[int, ...] = ()
    duplicate_temperature_indices: tuple[int, ...] = ()
    continuity_break_indices: tuple[int, ...] = ()
    temperature_min_C: float | None = None
    temperature_max_C: float | None = None
    rg_min_nm: float | None = None
    rg_max_nm: float | None = None
    relative_change_stats: Mapping[str, Any] = field(default_factory=dict)
    level: QualityLevel = QualityLevel.UNUSABLE
    reason_codes: tuple[str, ...] = ()
    metric: MetricEvidence | None = None

    def to_dict(self) -> dict[str, Any]: ...

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GuinierSequenceEvidence": ...
```

- [ ] Add `build_guinier_sequence_evidence(temperatures, frame_evidence, source_ref="")` that parses only finite positive Rg with frame level `Quantitative`/`Trend`, preserves positions, and never mutates input arrays or dictionaries. Its output must use the fields above and `MetricEvidence(metric_name="Rg_sequence", unit="frames")`.
- [ ] Implement deterministic levels: no valid frames → `Unusable`; one valid frame or temperature defects → `Diagnostic`; otherwise → `Trend`; never emit sequence `Quantitative`.
- [ ] Compute relative adjacent changes and robust median/MAD diagnostics for at least four valid frames; report isolated jumps only as evidence/reason codes and keep all values.
- [ ] Export the DTO and builder through the module public API.
- [ ] Run the focused contract tests and confirm GREEN.

### Task 3: Attach the sequence DTO to temperature results

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `tests/test_saxs_temperature_guinier_evidence.py`

- [ ] Add `TempSeriesResult.guinier_sequence_evidence: Dict | None = None` with a `None` default and include `Rg_sequence_level`/`Rg_sequence_reason_codes` in the DataFrame rows.
- [ ] After all frame analyses, call the pure builder with sorted temperatures and each point's evidence dictionary; leave failed frames represented by `None` evidence.
- [ ] Extend the temperature regression to assert the summary is attached, failed frames remain missing, and the frame count is unchanged.
- [ ] Run focused temperature and SAXS physical-helper regressions.

### Task 4: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-27-saxs-guinier-sequence-evidence.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/superpowers/plans/2026-07-27-saxs-guinier-sequence-evidence.md`

- [ ] Run the task-scoped verifier with an external basetemp and `git diff --check`.
- [ ] Record exact focused/full/quality/preprocessing results and known limitations in the task card and memory.
- [ ] Run `python scripts/task_check.py --task ...` and use `scripts/auto_commit.py` with the explicit allowlist.
