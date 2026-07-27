# Temperature SAXS Guinier Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有确定性 Guinier 拟合包装为可解释的 `GuinierEvidence`，并把数据质量、物理门槛和逐帧分级接入变温 SAXS 结果。

**Architecture:** 不改变 `guinier_analysis` 的窗口选择和数值结果；新增证据构造器，对现有 q²-ln(I) 点重新计算拟合统计量和不确定度，并通过显式适用性上下文控制能否进入定量级。`SAXSResult` 保存证据字典，`TemperaturePointResult` 只消费 DTO 字典/标量，不在温度模块内重复物理算法。

**Tech Stack:** Python dataclasses, NumPy, pytest, existing SAXS core/temperature pipeline.

---

### Task 1: Specify Guinier evidence gates with failing tests

**Files:**
- Create: `tests/test_saxs_guinier_evidence.py`

- [ ] **Step 1: Write the failing tests**

```python
import numpy as np

from polynexus.core.saxs_engine.saxs_quality_contracts import (
    QualityLevel,
    build_data_quality_report,
    build_guinier_evidence,
)


def _clean_fit():
    q = np.linspace(0.02, 0.18, 24)
    rg = 4.5
    ln_i = np.log(120.0) - q**2 * rg**2 / 3.0
    return q, ln_i, rg


def test_supported_guinier_fit_reports_uncertainty_and_quantitative_level():
    q, ln_i, rg = _clean_fit()
    quality = build_data_quality_report(q, np.exp(ln_i))

    evidence = build_guinier_evidence(
        q, ln_i, rg_nm=rg, i0=120.0, quality_report=quality,
        applicability="supported", source_ref="synthetic",
    )

    assert evidence.level is QualityLevel.QUANTITATIVE
    assert evidence.assumption_supported is True
    assert evidence.q_rg_max < 1.3
    assert evidence.r_squared > 0.99
    assert evidence.rg_uncertainty_nm is not None
    assert evidence.rg_uncertainty_nm >= 0
    assert evidence.metric is not None
    assert evidence.metric.level is QualityLevel.QUANTITATIVE


def test_unknown_guinier_applicability_is_diagnostic_even_when_fit_is_clean():
    q, ln_i, rg = _clean_fit()
    quality = build_data_quality_report(q, np.exp(ln_i))

    evidence = build_guinier_evidence(
        q, ln_i, rg_nm=rg, i0=120.0, quality_report=quality,
        applicability="unknown",
    )

    assert evidence.level is QualityLevel.DIAGNOSTIC
    assert "guinier_applicability_unresolved" in evidence.reason_codes


def test_qrg_gate_downgrades_a_fit_outside_the_guinier_assumption():
    q, ln_i, rg = _clean_fit()
    q = np.linspace(0.02, 0.40, 24)
    ln_i = np.log(120.0) - q**2 * rg**2 / 3.0
    quality = build_data_quality_report(q, np.exp(ln_i))

    evidence = build_guinier_evidence(
        q, ln_i, rg_nm=rg, i0=120.0, quality_report=quality,
        applicability="supported",
    )

    assert evidence.level is QualityLevel.DIAGNOSTIC
    assert "qrg_gate_failed" in evidence.reason_codes


def test_unusable_input_quality_cannot_produce_quantitative_guinier_evidence():
    q = np.asarray([0.02, 0.03, 0.04])
    ln_i = np.log(np.asarray([10.0, 9.0, 8.0]))
    quality = build_data_quality_report(q, np.exp(ln_i))

    evidence = build_guinier_evidence(
        q, ln_i, rg_nm=4.0, i0=10.0, quality_report=quality,
        applicability="supported",
    )

    assert evidence.level is QualityLevel.UNUSABLE
    assert "data_quality_unusable" in evidence.reason_codes
```

- [ ] **Step 2: Run the focused tests to confirm RED**

Run: `pytest tests/test_saxs_guinier_evidence.py -q`

Expected: collection fails because `build_guinier_evidence` does not yet exist.

### Task 2: Implement evidence statistics and deterministic gates

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`

- [ ] **Step 1: Implement `build_guinier_evidence`**

Use the finite q/ln(I) pairs without mutating them. Fit `ln(I) = a + bq²`
with `np.polyfit`; calculate `R²`, residual mean-square error, slope standard
error, and `sigma_Rg = 3*sigma_slope/(2*Rg)` when the degrees of freedom and
`Rg` are valid. Use the hard physical gate `q_max*Rg < 1.3`, require at least
five points and `R² >= 0.90` for a strong fit, and emit these deterministic
reason codes when applicable: `guinier_fit_insufficient_points`,
`guinier_slope_nonnegative`, `qrg_gate_failed`, `guinier_fit_poor`,
`guinier_applicability_unresolved`, `guinier_assumption_unsupported`, and
`data_quality_unusable`.

Set level to `Unusable` for unusable input or missing/invalid fit; to
`Diagnostic` when the physical assumption is unknown/unsupported or a hard
gate fails; to `Trend` for a supported fit with recoverable evidence weakness;
and to `Quantitative` only when input quality is quantitative, applicability is
explicitly supported, qRg and fit gates pass, and uncertainty is finite.
Populate the nested `MetricEvidence` with Rg, uncertainty, fit evidence,
physical checks, and source/data-quality references.

- [ ] **Step 2: Run focused tests to confirm GREEN**

Run: `pytest tests/test_saxs_guinier_evidence.py -q`

Expected: `4 passed`.

### Task 3: Attach evidence to single-frame and temperature results

**Files:**
- Modify: `polynexus/core/saxs_engine/core.py`
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `tests/test_saxs_temperature_guinier_evidence.py`

- [ ] **Step 1: Add a regression for temperature-frame propagation**

Create a fake `analyze_single` result carrying `guinier_evidence` and
`data_quality_report` dictionaries, run `analyze_temperature_series` on two
frames, and assert each `TemperaturePointResult` retains its own evidence
level and Rg. Add a failure-frame case that keeps evidence `None`/`Unusable`
and does not fabricate a missing measurement.

- [ ] **Step 2: Extend `SAXSResult` with evidence payload fields**

Add `data_quality_report` and `guinier_evidence` fields with `None` defaults.
After the existing `guinier_analysis` call, use `build_data_quality_report`
with `low_q_truncated=result.mask_truncated` and build evidence from the
returned q/ln(I) arrays. Read applicability only from the explicit
`cfg.condition_context["guinier_applicability"]` value; absent/unknown context
must remain diagnostic.

- [ ] **Step 3: Thread the payload into `TemperaturePointResult`**

Add `Rg_nm`, `guinier_level`, `guinier_reason_codes`,
`data_quality_report`, and `guinier_evidence` fields. In the existing core
analysis block copy the emitted payloads with `getattr` and leave them absent
when core analysis raises. Add Rg and level columns to `TempSeriesResult`'s
DataFrame without changing existing column names or sorting.

- [ ] **Step 4: Run temperature and SAXS regression tests**

Run:

```powershell
pytest tests/test_saxs_guinier_evidence.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_temperature_status.py tests/test_saxs_physical_helpers.py -q
```

Expected: all focused tests pass and missing/failing frames remain explicit.

### Task 4: Verify, document, and checkpoint the atomic stage

**Files:**
- Create: `docs/agent/tasks/2026-07-27-saxs-temperature-guinier-evidence.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [ ] **Step 1: Create the stage task card**

Record the accepted gates, no-interpolation rule, affected files, focused
tests, and the limitation that sequence-level trend classification and AI
rescue are subsequent stages.

- [ ] **Step 2: Run the structured verifier with an external basetemp**

Run:

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_temperature_guinier_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-temperature-guinier-evidence.md --changed --types
git diff --check
```

Expected: task check, memory check, Ruff, compile/type baseline, quality gate,
preprocessing gate, and whitespace checks all pass. Preserve any exact
repository `.pytest_tmp` permission failure separately if it recurs.

- [ ] **Step 3: Create one atomic checkpoint**

Use `scripts/auto_commit.py` with an explicit allowlist containing only the
files changed for this stage; do not push, merge, deploy, or clean user-owned
temporary directories.

---

## Self-review

- Existing Guinier numerical selection remains the source of q/ln(I), Rg, and I0.
- `qRg < 1.3` is never treated as sufficient without explicit applicability,
  fit evidence, and data quality.
- Missing frames and failed core analyses remain missing/diagnostic.
- AI rescue is not introduced in this stage and cannot bypass these gates.

## Execution status (2026-07-27)

All implementation steps in this plan are complete. The continuation also
added a regression for processed-data provenance and made behavior-preserving
Ruff baseline corrections in `core.py` and `saxs_temperature.py` so the
repository's changed-file verifier can inspect the complete Stage 1 boundary.
The atomic checkpoint is created after the documented verification evidence is
recorded in the task card.
