# SAXS Quality Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立阶段 0 的 SAXS 数据质量、指标证据、救援候选和验证结果公共契约，为变温 1D Guinier 纵向闭环提供可序列化、可追溯的基础。

**Architecture:** 复用现有 `SAXSResult`、`AnalysisEvidence` 和温度结果结构，不重写 Guinier/Porod 算法。新增一个只负责契约与确定性输入质量盘点的 `saxs_quality_contracts.py`；契约使用冻结 dataclass、显式 reason code、四级质量等级和稳定 JSON 表示，后续阶段把它们挂接到现有结果与发布链。

**Tech Stack:** Python 3.12/3.14, dataclasses, enum, NumPy, pytest, `scripts/verify.py`。

---

### Task 1: Define the stage-0 public contract through failing tests

**Files:**
- Create: `tests/test_saxs_quality_contracts.py`

- [ ] **Step 1: Write the failing contract tests**

```python
import json

import numpy as np

from polynexus.core.saxs_engine.saxs_quality_contracts import (
    DataQualityReport,
    GuinierEvidence,
    MetricEvidence,
    QualityLevel,
    RescueCandidate,
    RescueValidationReport,
    build_data_quality_report,
)


def test_quality_report_counts_faults_without_mutating_input_arrays():
    q = np.asarray([0.01, 0.02, np.nan, 0.02, 0.04, 0.03, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.13])
    intensity = np.asarray([10.0, -1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0])
    q_before = q.copy()
    intensity_before = intensity.copy()

    report = build_data_quality_report(q, intensity, source_id="frame-003")

    assert np.array_equal(q, q_before, equal_nan=True)
    assert np.array_equal(intensity, intensity_before, equal_nan=True)
    assert report.original_point_count == 15
    assert report.nonfinite_q_count == 1
    assert report.nonfinite_intensity_count == 1
    assert report.nonpositive_intensity_count == 1
    assert report.duplicate_q_count == 1
    assert report.nonmonotonic_q is True
    assert "q_nonfinite" in report.reason_codes
    assert report.level is QualityLevel.TREND


def test_quality_report_marks_too_few_usable_points_unusable():
    report = build_data_quality_report([0.01, 0.02, 0.03], [1.0, -1.0, np.nan])

    assert report.usable_point_count == 1
    assert report.level is QualityLevel.UNUSABLE
    assert "insufficient_points" in report.reason_codes


def test_contracts_round_trip_to_strict_json_without_numpy_or_enum_values():
    quality = build_data_quality_report(
        [0.01, 0.02, 0.03], [10.0, 9.0, 8.0],
        source_id="frame-001", raw_data_ref="raw/frame-001.xy",
        processing_config_ref="sha256:config",
    )
    metric = MetricEvidence(
        metric_name="Rg", value=4.5, unit="nm", level=QualityLevel.QUANTITATIVE,
        uncertainty=0.2, data_quality_ref="frame-001", source_ref="guinier-fit",
    )
    guinier = GuinierEvidence(
        rg_nm=4.5, rg_uncertainty_nm=0.2, q_rg_max=1.1, point_count=18,
        r_squared=0.998, level=QualityLevel.QUANTITATIVE,
        metric=metric,
    )
    candidate = RescueCandidate(
        candidate_id="candidate-1", kind="ai", parameters={"q_max": 0.12},
        reason_codes=("fit_window_candidate",),
    )
    validation = RescueValidationReport(
        candidate_id="candidate-1", hard_gate_passed=True,
        physical_gate_passed=True, data_preserved=True,
        decision="accepted",
    )
    payload = {
        "quality": quality.to_dict(),
        "guinier": guinier.to_dict(),
        "candidate": candidate.to_dict(),
        "validation": validation.to_dict(),
    }

    encoded = json.dumps(payload, allow_nan=False, sort_keys=True)

    assert json.loads(encoded)["quality"]["level"] == "Quantitative"
    assert DataQualityReport.from_dict(payload["quality"]) == quality
    assert GuinierEvidence.from_dict(payload["guinier"]).rg_nm == 4.5
    assert RescueCandidate.from_dict(payload["candidate"]).kind == "ai"
    assert RescueValidationReport.from_dict(payload["validation"]).decision == "accepted"


def test_ai_candidate_cannot_be_marked_accepted_without_validation_gates():
    candidate = RescueCandidate(candidate_id="candidate-2", kind="ai")
    report = RescueValidationReport(
        candidate_id=candidate.candidate_id,
        hard_gate_passed=False,
        physical_gate_passed=False,
        data_preserved=True,
        decision="accepted",
    )

    assert report.effective_decision() == "rejected"
    assert "hard_gate_failed" in report.rejection_reasons
    assert "physical_gate_failed" in report.rejection_reasons
```

- [ ] **Step 2: Run the focused tests and confirm the expected missing-contract failure**

Run: `pytest tests/test_saxs_quality_contracts.py -q`

Expected: collection fails with `ModuleNotFoundError` for `polynexus.core.saxs_engine.saxs_quality_contracts`.

### Task 2: Implement immutable, serializable quality and evidence contracts

**Files:**
- Create: `polynexus/core/saxs_engine/saxs_quality_contracts.py`

- [ ] **Step 1: Implement the minimal deterministic contract module**

Implement these exact public objects:

```python
class QualityLevel(str, Enum):
    QUANTITATIVE = "Quantitative"
    TREND = "Trend"
    DIAGNOSTIC = "Diagnostic"
    UNUSABLE = "Unusable"


@dataclass(frozen=True)
class DataQualityReport:
    source_id: str = ""
    raw_data_ref: str = ""
    processed_data_ref: str = ""
    processing_config_ref: str = ""
    low_q_truncated: bool = False
    original_point_count: int = 0
    finite_point_count: int = 0
    usable_point_count: int = 0
    invalid_point_count: int = 0
    nonfinite_q_count: int = 0
    nonfinite_intensity_count: int = 0
    nonpositive_intensity_count: int = 0
    duplicate_q_count: int = 0
    nonmonotonic_q: bool = False
    actions: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    level: QualityLevel = QualityLevel.UNUSABLE


@dataclass(frozen=True)
class MetricEvidence:
    metric_name: str
    value: Any = None
    unit: str = ""
    level: QualityLevel = QualityLevel.UNUSABLE
    applicable: bool = False
    uncertainty: Any = None
    fit_evidence: dict[str, Any] = field(default_factory=dict)
    physical_checks: dict[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    source_ref: str = ""
    data_quality_ref: str = ""
    processing_ref: str = ""


@dataclass(frozen=True)
class GuinierEvidence:
    rg_nm: float | None = None
    i0: float | None = None
    q_min_nm1: float | None = None
    q_max_nm1: float | None = None
    q_rg_max: float | None = None
    point_count: int = 0
    r_squared: float | None = None
    slope: float | None = None
    slope_uncertainty: float | None = None
    rg_uncertainty_nm: float | None = None
    assumption_supported: bool = False
    level: QualityLevel = QualityLevel.UNUSABLE
    reason_codes: tuple[str, ...] = ()
    metric: MetricEvidence | None = None


@dataclass(frozen=True)
class RescueCandidate:
    candidate_id: str
    kind: str = "deterministic"
    parameters: dict[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    source: str = ""
    requires_validation: bool = True


@dataclass(frozen=True)
class RescueValidationReport:
    candidate_id: str
    hard_gate_passed: bool = False
    physical_gate_passed: bool = False
    data_preserved: bool = False
    sequence_gate_passed: bool = True
    soft_score: float | None = None
    rejection_reasons: tuple[str, ...] = ()
    decision: str = "pending"

    def effective_decision(self) -> str: ...
```

`build_data_quality_report(q, intensity, ...)` must count only, never sort,
    repair, interpolate, or mutate its inputs. It accepts an explicit
    `low_q_truncated` flag supplied by the existing beam-stop/effective-q
    diagnostics; the report must never infer a physical Guinier applicability
    decision from q-array shape alone. It classifies clean data with at
least ten usable positive finite points as `Quantitative`; recoverable axis or
intensity faults with at least ten usable points as `Trend`; five to nine
usable points as `Diagnostic`; and fewer than five usable points as `Unusable`.
Every report and evidence object must provide `to_dict()` and `from_dict()`;
`to_dict()` converts enums and tuples to JSON-native values and converts
non-finite floats to `None`. `RescueValidationReport.effective_decision()` may
return `accepted` only when all hard gates, data preservation, and sequence
gates pass; otherwise it returns `rejected` and adds deterministic failure
reason codes.

- [ ] **Step 2: Run the focused tests and confirm they pass**

Run: `pytest tests/test_saxs_quality_contracts.py -q`

Expected: `4 passed`.

### Task 3: Add synthetic fault-injection fixtures and the stage task card

**Files:**
- Create: `tests/fixtures/saxs_quality_cases.py`
- Modify: `docs/agent/tasks/2026-07-27-saxs-quality-contracts-stage0.md`
- Modify: `tests/test_saxs_quality_contracts.py`

- [ ] **Step 1: Add deterministic synthetic cases**

Create fixture functions returning `(q, intensity)` for a clean Guinier curve,
    a curve with non-finite/negative values, and a low-q-truncated curve. The
fixtures must generate data in memory using NumPy and must not write regression
datasets or alter existing evaluation files.

- [ ] **Step 2: Add regression tests for the fault cases**

    Assert that the clean case is `Quantitative`, the dirty case retains explicit
    reason codes and is at most `Trend`, and the truncated case is never upgraded
    above `Diagnostic` without an explicit rescue/validation result. The
    truncated fixture passes `low_q_truncated=True` explicitly.

- [ ] **Step 3: Create the structured stage task card**

Record the goal, non-goals, affected files, acceptance criteria, focused test
command, structured verifier command, and the known limitation that this stage
does not yet calculate Guinier uncertainty or attach evidence to temperature
frames.

- [ ] **Step 4: Run task syntax validation**

Run: `python scripts/task_check.py --task docs/agent/tasks/2026-07-27-saxs-quality-contracts-stage0.md`

Expected: exit code `0`.

### Task 4: Verify, checkpoint, and update durable project state

**Files:**
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [ ] **Step 1: Run focused and structural verification**

Run:

```powershell
pytest tests/test_saxs_quality_contracts.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-quality-contracts-stage0.md --changed --types
git diff --check
```

Expected: focused tests and verifier exit `0`; `git diff --check` prints no
errors. If the repository's pre-existing Windows pytest temporary-directory
cleanup issue recurs, preserve the exact failure and run the focused test in
an external temporary directory as the acceptance evidence, without deleting
the existing local diagnostic directories.

- [ ] **Step 2: Update memory with evidence and the next stage**

Record the new contract module, the exact verification result, the atomic
checkpoint commit, and that the next task is to attach `GuinierEvidence` and
`DataQualityReport` to each `TemperaturePointResult` through deterministic
analysis.

- [ ] **Step 3: Create the atomic checkpoint with an explicit allowlist**

Run:

```powershell
python scripts/auto_commit.py `
  --message "feat(saxs): add quality and rescue evidence contracts" `
  --files `
    polynexus/core/saxs_engine/saxs_quality_contracts.py `
    tests/fixtures/__init__.py `
    tests/fixtures/saxs_quality_cases.py `
    tests/test_saxs_quality_contracts.py `
    docs/agent/tasks/2026-07-27-saxs-quality-contracts-stage0.md `
    docs/agent/memory/active-work.md `
    docs/agent/memory/current-state.md
```

Expected: one local commit is created and no push, merge, deploy, or cleanup
operation is performed.

---

## Self-review checklist

- The plan reuses existing `guinier_analysis`, `SAXSResult`,
  `TemperaturePointResult`, and `AnalysisEvidence`; it does not duplicate a
  numerical fitting algorithm.
- All new behavior is specified through failing tests before production code.
- Raw arrays are never mutated or silently repaired by the stage-0 quality
  report.
- Missing frames remain absent; no plan step interpolates temperature data.
- AI candidates remain pending until deterministic hard and physical gates
  pass.
- The remaining full-program stages are intentionally outside this atomic
  checkpoint and will receive their own task cards and plans.
