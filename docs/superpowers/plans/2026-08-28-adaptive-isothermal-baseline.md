# 自适应等温 DSC 基线 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为每个等温 DSC 候选事件计算端点线性和尾部恒定基线，默认确定性选择端点线性基线，并将选择与备选结果通过现有共享结果投影暴露。

**Architecture:** 在 `dsc_kinetics.py` 内新增小型基线变体 DTO/函数；候选事件检测只提供事件窗口，基线模块负责窗口稳健统计、积分和选择。主 `AvramiResult` 只保存一个选定结果，`baseline_variants` 保存可复现的诊断结果。上层继续消费 DSCEngine 的参数映射，不增加 GUI/CLI 私有算法。

**Tech Stack:** Python 3.12+, NumPy, SciPy, dataclasses, pytest, existing ComputeRun and project evidence contracts.

---

### Task 1: Lock the baseline contract with regression tests

**Files:**
- Modify: `tests/test_dsc_kinetics.py`
- Modify: `docs/agent/tasks/2026-08-28-adaptive-isothermal-baseline.md`

- [x] **Step 1: Write failing tests for baseline selection and provenance**

Add tests that call the public `avrami_from_dsc` and assert:

```python
assert result.baseline_method == "endpoint_linear"
assert result.baseline_variants[0]["method"] == "endpoint_linear"
assert "baseline_selection_reason" in result.__dict__
```

Add a second synthetic curve whose event starts at index zero and assert the
result remains computable with `baseline_method == "tail_constant"` and a
warning containing `endpoint_baseline_unavailable`.

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_dsc_kinetics.py -k "baseline_method or endpoint_baseline"
```

Expected: FAIL because the result contract does not yet expose baseline fields.

### Task 2: Implement baseline variants and deterministic selection

**Files:**
- Modify: `polynexus/core/dsc_engine/dsc_kinetics.py`
- Test: `tests/test_dsc_kinetics.py`

- [x] **Step 1: Extend the result contract**

Add these fields to `AvramiResult`:

```python
baseline_method: str = ""
baseline_start_value_Wg: float = np.nan
baseline_end_value_Wg: float = np.nan
baseline_slope_Wg_per_min: float = np.nan
baseline_window_start_index: int = -1
baseline_window_end_index: int = -1
baseline_variants: List[Dict[str, Any]] = field(default_factory=list)
baseline_selection_reason: str = ""
baseline_sensitive: bool = False
```

- [x] **Step 2: Add endpoint-window and baseline helpers**

Implement helpers with no material inputs:

```python
def _stable_edge_window(start: int, end: int, *, side: str) -> np.ndarray: ...
def _baseline_variant(time_min, HF_Wg, start, end, method) -> dict[str, Any]: ...
def _select_isothermal_baseline(variants) -> tuple[dict[str, Any] | None, str]: ...
```

The helper must use a point-count fraction of the event window, robust medians
for edge values, and return `available`, baseline values, slope, corrected
signal, area, Xt, and a reason. `endpoint_linear` is available only when both
edge windows have finite points and at least three points each. `tail_constant`
uses the event tail window. No fixed material temperature or absolute seconds
may appear in the implementation.

- [x] **Step 3: Route candidate integration through the selected baseline**

Replace the current single tail-median baseline inside
`relative_crystallinity_isothermal` with variant calculation and selection.
Use the selected variant's corrected signal for Xt, keep every available
variant's scalar result in `meta["baseline_variants"]`, and add
`baseline_sensitive` when the selected and alternate `t_half_min` or `n`
differs by the documented relative threshold.

- [x] **Step 4: Copy metadata into every Avrami result**

In `avrami_candidates_from_dsc`, copy the selected baseline fields and variant
rows onto the `AvramiResult`. Keep candidate-specific event ranges intact.

- [x] **Step 5: Run the focused tests and verify GREEN**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_dsc_kinetics.py -k "baseline_method or endpoint_baseline or avrami"
```

Expected: all selected tests pass.

### Task 3: Expose the shared baseline projection

**Files:**
- Modify: `polynexus/core/dsc.py`
- Modify: `polynexus/core/dsc_engine/figure_isothermal.py` only if figure metadata needs the method
- Test: `tests/test_dsc_kinetics.py`, `tests/test_compute_service.py`

- [x] **Step 1: Add fields to parameter rows**

Extend `_avrami_parameter_row` with baseline method, endpoint values, slope,
window indices, sensitivity, selection reason, and JSON-safe variants.

- [x] **Step 2: Add a ComputeRun projection regression**

Run a real or synthetic DSC direct run and assert `run.result.metrics` contains
the same `baseline_method` and `baseline_variants` values as the engine's
parameter row. Do not add a second serializer or algorithm.

- [x] **Step 3: Run consumer tests**

```powershell
python -m pytest -p no:cacheprovider -q tests/test_dsc_kinetics.py tests/test_compute_service.py tests/test_cli_batch.py tests/test_cli_batch_run_service.py tests/test_agent_workflow_cli.py tests/test_evidence_package_view.py
```

Expected: all selected tests pass.

### Task 4: Real-data replay and evidence documentation

**Files:**
- Create: `docs/acceptance/2026-08-28-dsc-adaptive-baseline.md`
- Modify: `docs/agent/tasks/2026-08-28-adaptive-isothermal-baseline.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Replay the six real isothermal files read-only**

Use `ComputeRunService` with the existing canonical converter on
`D:\PolyNexus-six-sample-replay-20260827-v007\raw\dsc\isothermal\*-DWJJ.txt`.
Record status, selected baseline, candidate count, and primary `t₁/₂` values
without writing into the replay directory.

- [x] **Step 2: Compare PA6 against the historical endpoint-linear reference**

Confirm PA6 180–184 ℃ `t₁/₂` and `n` remain within the documented tolerance
of the historical AI table. Record any material sensitivity warnings instead
of silently selecting a different method.

- [x] **Step 3: Update acceptance and memory**

Record exact commands, result counts, limitations, and untouched pre-existing
files. Keep the task `review_required` until scientific review is complete.

### Task 5: Final verification and checkpoint

**Files:**
- All files from Tasks 1–4

- [x] **Step 1: Run task-scoped verification**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-28-adaptive-isothermal-baseline.md --changed --types
git diff --check
```

Expected: task/memory checks, Ruff, compile, quality gate, preprocessing gate,
and whitespace all pass.

- [x] **Step 2: Review the cumulative diff**

Confirm no raw datasets, generated replay outputs, `active_run.json`, `runs/`,
or `tests/_tmp_phase3/` are staged.

- [x] **Step 3: Create the allowlisted checkpoint**

```powershell
python scripts/auto_commit.py `
  --message "fix(dsc): add adaptive isothermal baseline selection" `
  --files polynexus/core/dsc_engine/dsc_kinetics.py polynexus/core/dsc.py tests/test_dsc_kinetics.py docs/superpowers/specs/2026-08-28-adaptive-isothermal-baseline-design.md docs/superpowers/plans/2026-08-28-adaptive-isothermal-baseline.md docs/agent/tasks/2026-08-28-adaptive-isothermal-baseline.md docs/acceptance/2026-08-28-dsc-adaptive-baseline.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```
