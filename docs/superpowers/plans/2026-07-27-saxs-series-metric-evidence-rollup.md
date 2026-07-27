# SAXS Series Metric Evidence Rollup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有温变/应变逐帧 `metric_evidence` 汇总为可序列化、可降级、可导出的系列级证据摘要。

**Architecture:** 在 `saxs_quality_contracts.py` 增加只读 `MetricEvidenceSummary` 和确定性 builder。温变与应变分析在已有所有帧完成后调用 builder，把摘要挂到各自 series result；逐帧结果保持不变，Export 通过现有 quality-field 读取路径原样传播摘要。

**Tech Stack:** Python dataclasses, Enum, NumPy finite-safe conventions, pytest, existing SAXS quality/export contracts.

---

### Task 1: Add failing series-summary contract tests

**Files:**
- Create: `tests/test_saxs_series_metric_evidence.py`

- [x] **Step 1: Write the failing tests**

Add tests for the public builder:

```python
import json

from polynexus.core.saxs_engine.saxs_quality_contracts import (
    MetricEvidenceSummary,
    QualityLevel,
    build_series_metric_evidence,
)


def test_complete_two_frame_series_is_trend_and_strict_json_safe():
    frames = [
        {"porod": {"level": "Quantitative"}},
        {"porod": {"level": "Trend"}},
    ]

    summary = build_series_metric_evidence(
        frames, metric_names=("porod",), source_ref="temperature.metric_evidence"
    )["porod"]

    assert MetricEvidenceSummary.from_dict(summary).level is QualityLevel.TREND
    assert summary["frame_count"] == 2
    assert summary["evidence_frame_count"] == 2
    assert summary["usable_frame_count"] == 2
    assert summary["coverage_fraction"] == 1.0
    assert summary["applicable"] is True
    assert "series_level_capped_at_trend" in summary["reason_codes"]
    json.dumps(summary, allow_nan=False, sort_keys=True)


def test_missing_and_diagnostic_frames_are_preserved_as_diagnostic():
    frames = [
        {"porod": {"level": "Trend"}},
        None,
        {"porod": {"level": "Diagnostic"}},
    ]

    summary = build_series_metric_evidence(
        frames, metric_names=("porod",), source_ref="strain.metric_evidence"
    )["porod"]

    assert summary["level"] == "Diagnostic"
    assert summary["applicable"] is False
    assert summary["missing_frame_count"] == 1
    assert summary["diagnostic_frame_count"] == 1
    assert summary["coverage_fraction"] == 2 / 3
    assert "series_metric_missing_frames" in summary["reason_codes"]
    assert "series_metric_diagnostic_frames" in summary["reason_codes"]


def test_empty_or_unknown_series_is_unusable_without_nan():
    summaries = build_series_metric_evidence(
        [{"porod": {"level": "not-a-level"}}],
        metric_names=("porod", "kratky"),
    )

    assert summaries["porod"]["level"] == "Unusable"
    assert summaries["kratky"]["level"] == "Unusable"
    assert summaries["kratky"]["coverage_fraction"] == 0.0
    assert "series_metric_missing_all_frames" in summaries["kratky"]["reason_codes"]
    assert "series_metric_invalid_level" in summaries["porod"]["reason_codes"]
    json.dumps(summaries, allow_nan=False)
```

- [x] **Step 2: Run the new tests and verify RED**

Run:

```powershell
python -m pytest tests/test_saxs_series_metric_evidence.py -q
```

Expected: collection fails because `MetricEvidenceSummary` and
`build_series_metric_evidence` do not yet exist.

### Task 2: Implement the immutable contract and deterministic builder

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `polynexus/core/saxs_engine/__init__.py`

- [x] **Step 1: Add `MetricEvidenceSummary` beside `MetricEvidence`**

Implement the following fields and the existing contract conventions:

```python
@dataclass(frozen=True)
class MetricEvidenceSummary:
    metric_name: str
    frame_count: int = 0
    evidence_frame_count: int = 0
    usable_frame_count: int = 0
    diagnostic_frame_count: int = 0
    unusable_frame_count: int = 0
    missing_frame_count: int = 0
    coverage_fraction: float | None = None
    level: QualityLevel = QualityLevel.UNUSABLE
    applicable: bool = False
    level_counts: Mapping[str, int] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    source_ref: str = ""
```

Add `__post_init__`, `to_dict`, and `from_dict` using `_freeze`,
`_quality_level`, and `_string_tuple`, with no raw arrays or file paths.

- [x] **Step 2: Implement `build_series_metric_evidence`**

Use only existing frame mappings and this algorithm:

```text
frame_count = len(frame_evidence)
for each requested metric:
    count mapping payloads as evidence frames
    missing/non-mapping payloads as missing frames
    normalize each payload level with _quality_level
    count Quantitative/Trend as usable, Diagnostic and Unusable separately
    if the raw level is absent or invalid, add series_metric_invalid_level
    coverage_fraction = evidence_frame_count / frame_count, or None for empty
    level = Unusable for empty/all-missing
    level = Diagnostic for missing/diagnostic/unusable/invalid frames
    level = Diagnostic for fewer than two fully usable frames
    otherwise level = Trend and applicable = True
    cap all-Quantitative summaries with series_level_capped_at_trend
```

Return a stable metric-name-sorted dictionary of `to_dict()` payloads. Do not
modify any frame mapping.

- [x] **Step 3: Export the new contract**

Import and list `MetricEvidenceSummary` and `build_series_metric_evidence` in
`polynexus/core/saxs_engine/__init__.py`.

- [x] **Step 4: Run the contract tests GREEN**

Run:

```powershell
python -m pytest tests/test_saxs_series_metric_evidence.py -q
```

Expected: all new contract tests pass with strict JSON serialization.

### Task 3: Attach summaries to temperature and strain series

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`
- Modify: `tests/test_saxs_mode_evidence_propagation.py`

- [x] **Step 1: Add failing propagation assertions**

Extend the existing temperature test with:

```python
assert result.metric_evidence["porod"]["level"] == "Diagnostic"
assert result.metric_evidence["porod"]["missing_frame_count"] == 1
assert result.metric_evidence["porod"]["applicable"] is False
```

The two failed temperature frames must remain absent at frame level while the
series summary remains explicit. Extend the strain test with:

```python
assert result.metric_evidence["porod"]["level"] == "Diagnostic"
assert result.metric_evidence["porod"]["missing_frame_count"] == 1
```

- [x] **Step 2: Attach the summary after the existing frame loop**

Import `build_series_metric_evidence` and assign:

```python
metric_names = ("porod", "kratky", "invariant", "lamellar")
result.metric_evidence = build_series_metric_evidence(
    [point.metric_evidence for point in result.temp_points],
    metric_names=metric_names,
    source_ref="saxs_temperature.metric_evidence",
)
```

Use the analogous `strain_points` list and `saxs_strain.metric_evidence` source
for strain. Leave existing `Metric_evidence_levels` DataFrame columns and all
numeric arrays unchanged.

- [x] **Step 3: Run the mode propagation matrix**

Run:

```powershell
python -m pytest tests/test_saxs_mode_evidence_propagation.py tests/test_saxs_series_metric_evidence.py -q
```

Expected: existing frame-preservation tests and new series-summary assertions
pass.

### Task 4: Verify read-only Export provenance

**Files:**
- Modify: `tests/test_saxs_export_bundle.py`

- [x] **Step 1: Add an export regression**

Construct a fake temperature series with a `metric_evidence` summary and one
frame payload, export it, and assert:

```python
quality = json.loads((root / "quality_evidence.json").read_text())
assert quality["temperature"]["metric_evidence"]["porod"]["level"] == "Diagnostic"
assert quality["temperature"]["frames"][0]["metric_evidence"]["porod"]["level"] == "Trend"
```

The test must also assert that the original summary and frame dictionaries are
not mutated by export.

- [x] **Step 2: Run Export and SAXS regression tests**

Run:

```powershell
python -m pytest tests/test_saxs_export_bundle.py tests/test_saxs_mode_evidence_propagation.py tests/test_saxs_series_metric_evidence.py -q
```

Expected: all tests pass; export remains audit-only and no publication role or
candidate decision changes.

### Task 5: Record acceptance and create the checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-27-saxs-series-metric-evidence-rollup.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/superpowers/plans/2026-07-27-saxs-series-metric-evidence-rollup.md`

- [x] **Step 1: Run task-scoped verification**

Run:

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_series_metric_rollup'
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-series-metric-evidence-rollup.md --changed --types
git diff --check
```

Record exact quality/preprocessing counts and warnings. Do not record a timeout
as a pass.

- [x] **Step 2: Run the applicable SAXS regression matrix**

Run the three focused commands from Tasks 1, 3, and 4 plus the exact changed
file SAXS matrix used by the repository verifier. Keep existing fixture and
temporary directories untouched.

- [x] **Step 3: Update durable records and checkpoint**

Mark only verified acceptance items, record known limitations (series summaries
are Trend-capped and do not impute missing frames), and use:

```powershell
python scripts/auto_commit.py --message "feat(saxs): add series metric evidence rollup" --files <explicit changed-file allowlist>
```

No push, merge, deploy, or cleanup is part of this task.

## Plan self-review

- Every design requirement maps to a task: contract, downgrade behavior,
  propagation, export, regression, and checkpoint evidence.
- The plan adds no new physical threshold or numerical analysis algorithm.
- Frame-level evidence remains authoritative; series summaries are derived and
  read-only.
- The only planned source of series evidence is the existing frame payload, so
  missing frames cannot be fabricated.

## Execution status

- Tasks 1–4 are implemented and their focused tests pass (`11 passed`); the
  complete SAXS test matrix passes (`274 passed, 4 existing warnings`).
- The explicit SAXS-file Ruff/compile checks and repository quality gates pass.
- Current task-scoped verification passes task/memory checks, quality `282`,
  preprocessing `106`, compile/type baseline, and whitespace. The complete
  current SAXS matrix is `317 passed, 4 warnings`; the warnings are existing
  Arial CJK glyph warnings. Full/boundary and human scientific review remain
  separate release gates.
