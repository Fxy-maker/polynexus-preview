# PolyNexus 核心与物理可信度矫正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 PolyNexus 从“能跑出多技术分析结果”推进到“每个关键物理结论都有可追溯 evidence、可降级语义、可进入 Joint 的权重判断”。

**Architecture:** 先把单技术 evidence 固化为可持久化契约，再让 Joint 按 evidence 加权消费结果，最后逐步补齐 NMR、IR、SAXS、WAXS、DSC 的物理门控和不确定度字段。核心原则是保留 raw 数值，不静默改写物理量；通过 `status/reason/confidence/uncertainty` 解释数值能否进入结论区。

**Tech Stack:** Python 3.10+，NumPy/SciPy/lmfit，SQLite `SampleDB`，PySide6 GUI，pytest 回归测试，现有 `analysis_evidence.py` 证据契约。

---

## 1. 当前问题归纳

### 1.1 已经做得比较好的部分

- 多技术 engine 已经拆成 DSC、IR、WAXS、SAXS、NMR、Joint。
- `AnalysisResult` 已经有 `analysis_evidence` 字段。
- AI tuning orchestration 已经能构造和消费 `build_analysis_evidence()`。
- SAXS 温变 `lc` 已经有 `melting_window_status`、`lc_reliability_status`、reason 字段。
- WAXS/DSC/IR/NMR 都有基础 QC 或 quality flags。

### 1.2 当前主要短板

- `analysis_evidence` 没有作为一等数据持久化进 `SampleDB`，Joint Hub 主要读取 `parameters/results_summary`。
- Joint 当前更像 cross-check，不是真正 evidence-weighted joint reasoning。
- `JointModel.solve()` 目前只评估初始参数，没有执行真实优化。
- NMR evidence 约束偏薄，generic assignment、polymer DB assignment、computed shift、solvent risk、`Xc_NMR` assignment-limited 状态没有形成稳定门控。
- IR 的 `Xc_pct` 仍容易把 uncalibrated band ratio 当作可比较结晶度。
- WAXS Scherrer/Williamson-Hall 没有系统扣除仪器展宽，也没有给出尺寸不确定度。
- DSC 的 Xc 可信度还缺少基线、峰积分边界、冷结晶扣减、`DHm0` 来源和程序段一致性的证据。
- 日志和中文文本存在 mojibake 与 unreachable logger，影响解释链可信度。

---

## 2. 文件结构规划

### 2.1 数据与证据持久化

- Modify: `polynexus/data/sample_db.py`
  - 给 `analysis_runs` 增加 `analysis_evidence TEXT`。
  - `create_analysis_run()` 接收并保存 evidence。
  - `get_analysis_runs()` 读取并反序列化 evidence。
- Modify: `polynexus/gui/main_window.py`
  - GUI 保存分析记录时把当前 result 中的 evidence 写入 DB。
- Modify: `polynexus/__main__.py`
  - CLI / batch / ai-tune 保存 run 时带上 evidence。
- Test: `tests/test_sample_db.py`
- Test: `tests/test_main_window_persistence.py`

### 2.2 Joint evidence-weighted 消费层

- Modify: `polynexus/core/joint/dataset.py`
  - `JointRunRecord` 增加 `analysis_evidence`。
  - 增加单技术 confidence context 提取。
  - Joint issue family 扩展为 `single-tech evidence weak`、`IR calibration weak`、`NMR assignment limited`、`condition alignment weak`、`SAXS-WAXS scale mismatch`。
- Modify: `polynexus/core/joint/validation.py`
  - 让 validation 接收每个技术的 `evidence_weight` 与 `source_status`。
  - 低可信数值默认降为 WARN 或 skipped，不直接形成 ERROR。
- Modify: `polynexus/core/joint/coordinator.py`
  - joint fit 和 timeline 输出 confidence context。
- Test: `tests/test_joint_hub_dataset.py`
- Test: `tests/test_joint_coordinator.py`

### 2.3 Joint model 真优化

- Modify: `polynexus/core/joint/models.py`
  - 用 `scipy.optimize.least_squares` 或 `minimize` 实际优化参数。
  - 返回 final residual、active bound、success message。
- Test: `tests/test_joint_coordinator.py`

### 2.4 NMR 可信度增强

- Modify: `polynexus/core/nmr_engine/core.py`
  - 输出 assignment source 统计、solvent peak 统计、phase assignment 状态。
- Modify: `polynexus/core/nmr.py`
  - `_validate_results()` 增加 NMR evidence status flags。
- Modify: `polynexus/core/analysis_evidence.py`
  - NMR 增加 signal、peak、assignment、Xc、computed-shift 证据分区。
- Test: `tests/test_nmr_engine.py`
- Test: `tests/test_analysis_evidence.py`

### 2.5 IR 结晶度语义门控

- Modify: `polynexus/core/ir_engine/core.py`
  - 区分 user hint 与 spectral assignment confidence。
  - `Xc_pct` 来源标记为 calibrated、uncalibrated_index、unavailable。
- Modify: `polynexus/core/ir.py`
  - validation 中低 band support 不允许标记强 Xc。
- Modify: `polynexus/core/analysis_evidence.py`
  - IR evidence 中加入 calibration status 与 band support status。
- Test: `tests/test_ir_engine.py`
- Test: `tests/test_analysis_evidence.py`

### 2.6 SAXS 覆盖扩展

- Modify: `polynexus/core/saxs.py`
  - static/strain 汇总也输出可进入 Joint 的 reliability status。
- Modify: `polynexus/core/saxs_engine/core.py`
  - 单帧也产出 `lc_reliability_status/reason`，不只依赖温变序列。
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`
  - 拉伸序列把 low-q void、orientation、lamellar support 拆开记录。
- Test: `tests/test_saxs_batch_parameters.py`
- Test: `tests/test_saxs_scoring.py`
- Test: `tests/test_analysis_evidence.py`

### 2.7 WAXS/DSC 不确定度与仪器修正

- Modify: `polynexus/core/waxs_engine/config.py`
  - 增加 `instrument_fwhm_deg`、`size_uncertainty_mode`。
- Modify: `polynexus/core/waxs_engine/core.py`
  - Scherrer/WH 先扣仪器展宽，输出 `D_uncertainty_nm` 与 `instrument_broadening_applied`。
- Modify: `polynexus/core/dsc_engine/core.py`
  - 输出基线敏感性、积分边界敏感性、冷结晶扣减状态、`DHm0_source`。
- Modify: `polynexus/core/dsc.py`
  - validation 将 DSC Xc 分成 usable、low_confidence、diagnostic_only。
- Test: `tests/test_waxs_temperature.py`
- Test: `tests/test_dsc_engine.py`
- Test: `tests/test_analysis_evidence.py`

### 2.8 日志与用户可读解释

- Modify: `polynexus/core/*.py`
- Modify: `polynexus/core/*_engine/*.py`
- Modify: `polynexus/gui/i18n.py`
  - 修复用户可见 mojibake。
  - 删除 `return` 后 unreachable logger。
  - 将宽泛 except 的重要失败写入 evidence 或 validation warning。
- Test: `tests/test_core.py`
- Test: `tests/test_main_window_persistence.py`

---

## 3. 执行顺序

1. Evidence 持久化。
2. Joint 读取并展示 evidence context。
3. Joint validation 按 evidence 加权。
4. Joint model 真优化。
5. NMR evidence 补齐。
6. IR calibration gate 补齐。
7. SAXS static/strain reliability 统一。
8. WAXS 仪器展宽与不确定度。
9. DSC Xc 证据链与基线敏感性。
10. 日志、中文文本、导出解释收口。

这个顺序的理由：Joint 是多技术平台的“结论放大器”。如果单技术 evidence 不能持久化，后续所有 Joint 判断都会继续把弱来源当强来源，所以必须先修数据契约。

---

## 4. 任务分解

### Task 1: 持久化 analysis_evidence

**Files:**
- Modify: `polynexus/data/sample_db.py`
- Modify: `polynexus/gui/main_window.py`
- Modify: `polynexus/__main__.py`
- Test: `tests/test_sample_db.py`
- Test: `tests/test_main_window_persistence.py`

- [x] **Step 1: 写 SampleDB 失败测试**

在 `tests/test_sample_db.py` 增加：

```python
def test_analysis_run_persists_analysis_evidence(tmp_path):
    from polynexus.data.sample_db import SampleDB

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "annealed")
    evidence = {
        "technique": "SAXS",
        "constraint_summary": {"status": "soft_warn"},
        "structure_evidence": {
            "lc_reliability_status": "diagnostic_only",
            "lc_reliability_reason": "within_melting_window|peak_tracking_lost",
        },
    }

    run_id = db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.temperature",
        results_summary={"L_nm": 12.0, "lc_nm": 3.0},
        analysis_evidence=evidence,
    )

    runs = db.get_analysis_runs(batch_id)
    saved = next(run for run in runs if run["id"] == run_id)
    assert saved["analysis_evidence"] == evidence
```

- [x] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_sample_db.py::test_analysis_run_persists_analysis_evidence -v`

Expected: FAIL，报错包含 `unexpected keyword argument 'analysis_evidence'` 或返回 run 中没有 `analysis_evidence`。

- [x] **Step 3: 扩展 DB schema 与反序列化**

在 `polynexus/data/sample_db.py` 中给 `analysis_runs` 增加字段，并在初始化后执行迁移：

```python
def _ensure_column(self, table: str, column: str, ddl: str) -> None:
    rows = self._conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {str(row["name"]) for row in rows}
    if column not in existing:
        self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
        self._conn.commit()
```

在 schema 初始化后调用：

```python
self._ensure_column("analysis_runs", "analysis_evidence", "analysis_evidence TEXT")
```

把 `create_analysis_run()` 签名改成：

```python
def create_analysis_run(
    self,
    batch_id,
    technique,
    submodule="",
    parameters=None,
    results_summary=None,
    analysis_evidence=None,
    output_dir="",
    ai_tuned=False,
    confirmed=False,
):
```

INSERT 语句增加 `analysis_evidence`：

```python
"INSERT INTO analysis_runs "
"(id,batch_id,technique,submodule,parameters,results_summary,analysis_evidence,output_dir,status,ai_tuned,confirmed) "
"VALUES (?,?,?,?,?,?,?,?,'completed',?,?)"
```

绑定值中加入：

```python
json.dumps(analysis_evidence or {}, ensure_ascii=False)
```

在读取 run 的位置，把反序列化字段列表扩展为：

```python
for col in ("parameters", "results_summary", "analysis_evidence", "plot_edits"):
    if col in item:
        item[col] = json.loads(item[col]) if item[col] else {}
```

- [x] **Step 4: GUI 持久化 evidence**

在 `polynexus/gui/main_window.py` 的 `_persist_analysis_run()` 中，找到 `db.create_analysis_run(...)` 调用，加入：

```python
analysis_evidence=self._result_to_jsonable(
    current.get("analysis_evidence", {})
    if isinstance(current, dict)
    else getattr(result, "analysis_evidence", {})
),
```

如果当前函数里已经有 `summary` 和 `current` 变量，优先用 `current["analysis_evidence"]`；否则从 `result.analysis_evidence` 读取。

- [x] **Step 5: CLI / batch 持久化 evidence**

在 `polynexus/__main__.py` 的 `_persist_batch_run()` 和 `_persist_ai_tune_run()` 中传入：

```python
analysis_evidence=(
    getattr(result, "analysis_evidence", {})
    if result is not None
    else report.get("analysis_evidence", {})
),
```

AI tune report 中如果 evidence 在 best round 内，使用：

```python
analysis_evidence=report.get("best_record", {}).get("analysis_evidence", {})
```

- [x] **Step 6: 运行持久化相关测试**

Run:

```powershell
pytest tests/test_sample_db.py tests/test_main_window_persistence.py -q
```

Expected: PASS。

- [x] **Step 7: Commit**

```powershell
git add polynexus/data/sample_db.py polynexus/gui/main_window.py polynexus/__main__.py tests/test_sample_db.py tests/test_main_window_persistence.py
git commit -m "feat: persist analysis evidence with runs"
```

---

### Task 2: 让 Joint 消费 evidence context

**Files:**
- Modify: `polynexus/core/joint/dataset.py`
- Modify: `polynexus/core/joint/validation.py`
- Test: `tests/test_joint_hub_dataset.py`

- [x] **Step 1: 写 Joint evidence 失败测试**

在 `tests/test_joint_hub_dataset.py` 增加：

```python
def test_joint_hub_downgrades_assignment_limited_nmr_xc(tmp_path):
    from polynexus.data.sample_db import SampleDB
    from polynexus.core.joint.dataset import collect_joint_dataset, build_joint_hub_report

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "batch-a", condition_values={"temperature_C": 180})
    db.create_analysis_run(batch_id, "dsc", results_summary={"Xc_pct": 42.0})
    db.create_analysis_run(
        batch_id,
        "nmr",
        results_summary={"Xc_pct": 72.0, "Xc_method": "requires_crystalline_amorphous_assignment"},
        analysis_evidence={
            "constraint_summary": {"status": "soft_warn", "triggered_names": {"soft_warn": ["nmr_xc_assignment_limited"]}},
            "structure_evidence": {"Xc_assignment_status": "assignment_limited"},
        },
    )

    report = build_joint_hub_report(collect_joint_dataset(db))
    context = report["ai_context"]

    assert context["issue_count"] >= 1
    assert "NMR assignment limited" in context["issue_families"]
    assert any("assignment-limited" in item for item in context["highlights"])
```

- [x] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_joint_hub_dataset.py::test_joint_hub_downgrades_assignment_limited_nmr_xc -v`

Expected: FAIL，`issue_families` 没有 `NMR assignment limited`。

- [x] **Step 3: 扩展 JointRunRecord**

在 `polynexus/core/joint/dataset.py` 中扩展 dataclass：

```python
@dataclass
class JointRunRecord:
    run_id: str
    technique: str
    submodule: str = ""
    created_at: str = ""
    output_dir: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    results_summary: dict[str, Any] = field(default_factory=dict)
    analysis_evidence: dict[str, Any] = field(default_factory=dict)
```

在 `collect_joint_dataset()` 构造 `JointRunRecord` 时加入：

```python
analysis_evidence=run.get("analysis_evidence", {}) or {},
```

- [x] **Step 4: 增加 Joint confidence context helper**

在 `polynexus/core/joint/dataset.py` 中增加：

```python
def _run_evidence_context(run: JointRunRecord | None) -> dict[str, Any]:
    if run is None or not isinstance(run.analysis_evidence, dict):
        return {"status": "unknown", "weight": 0.5, "reasons": ["evidence_missing"]}
    evidence = run.analysis_evidence
    summary = evidence.get("constraint_summary", {}) if isinstance(evidence.get("constraint_summary"), dict) else {}
    structure = evidence.get("structure_evidence", {}) if isinstance(evidence.get("structure_evidence"), dict) else {}
    status = str(summary.get("status") or "ok").strip().lower()
    reasons: list[str] = []
    weight = 1.0
    if status == "hard_fail":
        weight = 0.0
        reasons.append("hard_fail")
    elif status == "soft_warn":
        weight = 0.45
        reasons.append("soft_warn")
    if str(structure.get("Xc_assignment_status") or "").strip() == "assignment_limited":
        weight = min(weight, 0.25)
        reasons.append("assignment-limited")
    if str(structure.get("lc_reliability_status") or "").strip() == "diagnostic_only":
        weight = min(weight, 0.25)
        reasons.append("diagnostic-only-lc")
    return {"status": status or "ok", "weight": weight, "reasons": reasons}
```

- [x] **Step 5: 扩展 issue family 与 highlights**

在 `_joint_issue_family()` 中加入：

```python
if "nmr_assignment_limited" in key:
    return "NMR assignment limited"
if "ir_calibration_weak" in key:
    return "IR calibration weak"
if "single_tech_evidence_weak" in key:
    return "single-tech evidence weak"
```

在 `validate_joint_row()` 中，在 cross-validation 后追加 evidence issue：

```python
for tech in TECHNIQUES:
    run = row.run(tech)
    ctx = _run_evidence_context(run)
    if run and ctx["weight"] <= 0.25:
        output.append({
            "sample": row.sample_name,
            "batch": row.batch_label,
            "check": f"{tech}_single_tech_evidence_weak",
            "severity": "WARN",
            "passed": False,
            "message": f"{tech.upper()} evidence is weak: {', '.join(ctx['reasons'])}",
            "details": ctx,
        })
    if tech == "nmr" and run and "assignment-limited" in ctx["reasons"]:
        output.append({
            "sample": row.sample_name,
            "batch": row.batch_label,
            "check": "nmr_assignment_limited",
            "severity": "WARN",
            "passed": False,
            "message": "NMR Xc is assignment-limited and should not be treated as strong crystallinity evidence.",
            "details": ctx,
        })
```

- [x] **Step 6: 运行 Joint tests**

Run:

```powershell
pytest tests/test_joint_hub_dataset.py tests/test_joint_coordinator.py -q
```

Expected: PASS。

- [x] **Step 7: Commit**

```powershell
git add polynexus/core/joint/dataset.py polynexus/core/joint/validation.py tests/test_joint_hub_dataset.py
git commit -m "feat: add evidence-aware joint context"
```

---

### Task 3: JointModel 执行真实优化

**Files:**
- Modify: `polynexus/core/joint/models.py`
- Test: `tests/test_joint_coordinator.py`

- [x] **Step 1: 写优化行为失败测试**

在 `tests/test_joint_coordinator.py` 增加：

```python
def test_joint_model_moves_parameters_toward_observations():
    from polynexus.core.joint.models import LamellarJointModel

    model = LamellarJointModel()
    model.add_observation("Tm_DSC_C", 240.0, 1.0)
    model.add_observation("L_nm", 18.0, 0.5)
    model.add_observation("Xc_pct", 35.0, 2.0)
    result = model.solve()

    assert result.success is True
    assert abs(result.parameters["Tm_DSC_C"] - 240.0) < 0.5
    assert abs(result.parameters["L_nm"] - 18.0) < 0.5
    assert abs(result.parameters["Xc_pct"] - 35.0) < 1.0
    assert result.message != "Solved with initial parameter vector"
```

- [x] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_joint_coordinator.py::test_joint_model_moves_parameters_toward_observations -v`

Expected: FAIL，参数仍是初始值。

- [x] **Step 3: 实现 least-squares solve**

在 `polynexus/core/joint/models.py` 中引入：

```python
from scipy.optimize import least_squares
```

替换 `solve()` 中初始向量直接返回的逻辑：

```python
names = list(self._parameters.keys())
x0 = np.array([self._parameters[name][0] for name in names], dtype=float)
lower = []
upper = []
for name in names:
    _, bounds = self._parameters[name]
    lo, hi = bounds if bounds else (None, None)
    lower.append(-np.inf if lo is None else float(lo))
    upper.append(np.inf if hi is None else float(hi))

def residual_vector(x: np.ndarray) -> np.ndarray:
    params = self._clip_to_bounds({name: float(value) for name, value in zip(names, x)})
    values: list[float] = []
    for obs_name, (obs_value, sigma) in self._observations.items():
        if obs_name in params:
            values.append((params[obs_name] - obs_value) / max(float(sigma), 1e-9))
    for fn, weight, hard in self._constraints:
        penalty = float(fn(params))
        scale = 1000.0 if hard and penalty > 0 else max(float(weight), 1e-9) ** 0.5
        values.append(scale * penalty)
    return np.asarray(values, dtype=float)

opt = least_squares(residual_vector, x0, bounds=(np.asarray(lower), np.asarray(upper)))
params = self._clip_to_bounds({name: float(value) for name, value in zip(names, opt.x)})
objective, residuals = self._objective(params)
return JointSolveResult(
    success=bool(opt.success),
    method=method,
    parameters=params,
    residuals=residuals,
    objective=float(objective),
    n_observations=len(self._observations),
    n_constraints=len(self._constraints),
    message=str(opt.message),
    details={"nfev": int(opt.nfev), "cost": float(opt.cost)},
)
```

- [x] **Step 4: 运行 Joint model tests**

Run: `pytest tests/test_joint_coordinator.py::test_joint_model_moves_parameters_toward_observations -v`

Expected: PASS。

- [x] **Step 5: Commit**

```powershell
git add polynexus/core/joint/models.py tests/test_joint_coordinator.py
git commit -m "feat: optimize joint model parameters"
```

---

### Task 4: 扩展 NMR evidence 门控

**Files:**
- Modify: `polynexus/core/nmr_engine/core.py`
- Modify: `polynexus/core/nmr.py`
- Modify: `polynexus/core/analysis_evidence.py`
- Test: `tests/test_nmr_engine.py`
- Test: `tests/test_analysis_evidence.py`

- [x] **Step 1: 写 NMR evidence 失败测试**

在 `tests/test_analysis_evidence.py` 增加：

```python
def test_nmr_evidence_marks_assignment_limited_xc_not_ready():
    from polynexus.core.analysis_evidence import build_analysis_evidence

    evidence = build_analysis_evidence(
        "NMR",
        {
            "nucleus": "13C",
            "sample_state": "solid",
            "n_peaks": 4,
            "median_snr": 12.0,
            "mean_fwhm_ppm": 3.5,
            "r_squared": 0.91,
            "Xc_pct": 55.0,
            "Xc_method": "requires_crystalline_amorphous_assignment",
            "assignment_source": "generic_region",
            "generic_assignment_fraction": 1.0,
            "phase_assignment_count": 0,
            "solvent_peak_count": 0,
        },
        {},
        {},
    )

    assert evidence["structure_evidence"]["Xc_assignment_status"] == "assignment_limited"
    assert evidence["structure_evidence"]["paper_conclusion_ready"] is False
    assert "nmr_xc_assignment_limited" in evidence["constraint_summary"]["triggered_names"]["soft_warn"]
```

- [x] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_analysis_evidence.py::test_nmr_evidence_marks_assignment_limited_xc_not_ready -v`

Expected: FAIL，缺少 `Xc_assignment_status` 或约束名。

- [x] **Step 3: NMR core 输出 assignment 统计**

在 `NMRResult.parameters` 增加：

```python
assigned = [pk for pk in self.peaks if pk.get("phase") not in ("", "unknown", None)]
generic = [pk for pk in self.peaks if str(pk.get("assignment", "")).endswith(("C", "H")) or "region" in str(pk.get("assignment", "")).lower()]
solvents = [pk for pk in self.peaks if pk.get("possible_solvent")]
p["assigned_peak_fraction"] = len(assigned) / max(len(self.peaks), 1)
p["generic_assignment_fraction"] = len(generic) / max(len(self.peaks), 1)
p["solvent_peak_count"] = len(solvents)
p["phase_assignment_count"] = len(assigned)
p["assignment_source"] = "polymer_db" if assigned else "generic_region"
```

- [x] **Step 4: NMR constraints 增加门控项**

在 `analysis_evidence.py` 的 NMR inventory 加入：

```python
EvidenceConstraint(
    name="nmr_xc_assignment_limited",
    kind="soft_warn",
    source="NMR",
    severity="WARN",
    description="NMR Xc is present without crystalline/amorphous phase assignment support.",
    field="Xc_method",
    rationale="Assignment-limited Xc should not enter Joint as strong crystallinity evidence.",
)
```

在 `evaluate_physical_constraints()` 的 NMR 分支中触发条件：

```python
triggered = (
    output.get("Xc_pct") is not None
    and str(output.get("Xc_method") or "") == "requires_crystalline_amorphous_assignment"
)
```

- [x] **Step 5: NMR structure_evidence 输出**

在 `build_analysis_evidence()` 的 NMR 分支填充：

```python
xc_method = str(output.get("Xc_method") or "")
phase_count = _safe_int(output.get("phase_assignment_count"), 0)
xc_assignment_status = (
    "supported" if phase_count >= 2 and xc_method
    else "assignment_limited" if xc_method == "requires_crystalline_amorphous_assignment"
    else "unavailable"
)
structure_evidence = {
    "Xc_NMR": _clean_float(output.get("Xc_pct")),
    "Xc_method": xc_method,
    "Xc_assignment_status": xc_assignment_status,
    "paper_conclusion_ready": xc_assignment_status == "supported",
}
```

- [x] **Step 6: 运行 NMR tests**

Run:

```powershell
pytest tests/test_nmr_engine.py tests/test_analysis_evidence.py -q
```

Expected: PASS。

- [x] **Step 7: Commit**

```powershell
git add polynexus/core/nmr_engine/core.py polynexus/core/nmr.py polynexus/core/analysis_evidence.py tests/test_nmr_engine.py tests/test_analysis_evidence.py
git commit -m "feat: gate nmr crystallinity evidence"
```

---

### Task 5: IR 结晶度 calibration gate

**Files:**
- Modify: `polynexus/core/ir_engine/core.py`
- Modify: `polynexus/core/ir.py`
- Modify: `polynexus/core/analysis_evidence.py`
- Test: `tests/test_ir_engine.py`
- Test: `tests/test_analysis_evidence.py`

- [x] **Step 1: 写 IR calibration 失败测试**

在 `tests/test_analysis_evidence.py` 增加：

```python
def test_ir_uncalibrated_band_index_is_not_paper_ready_xc():
    from polynexus.core.analysis_evidence import build_analysis_evidence

    evidence = build_analysis_evidence(
        "IR",
        {
            "polymer_name": "PA6",
            "polymer_score": 1.0,
            "n_peaks": 8,
            "Xc_pct": 62.0,
            "Xc_method": "PA6_A1200_A1637_uncalibrated",
            "Xc_calibration_status": "uncalibrated_index",
            "assigned_peak_fraction": 0.4,
            "key_band_support_score": 0.45,
        },
        {},
        {},
    )

    assert evidence["structure_evidence"]["Xc_calibration_status"] == "uncalibrated_index"
    assert evidence["structure_evidence"]["paper_conclusion_ready"] is False
    assert "ir_xc_uncalibrated" in evidence["constraint_summary"]["triggered_names"]["soft_warn"]
```

- [x] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_analysis_evidence.py::test_ir_uncalibrated_band_index_is_not_paper_ready_xc -v`

Expected: FAIL，缺少 `Xc_calibration_status` 或约束名。

- [x] **Step 3: IR core 区分 hint 和谱图 assignment**

在 `polynexus/core/ir_engine/core.py` 中，当用户传入 `polymer_hint` 时不要把 `polymer_score` 设成 1.0；改为：

```python
elif polymer_hint:
    result.polymer_score = np.nan
    result.parameters["polymer_hint_source"] = "user"
```

如果 `IRResult.parameters` 是 property，则加入：

```python
"polymer_hint_source": getattr(self, "polymer_hint_source", ""),
```

- [x] **Step 4: IR Xc 输出 calibration status**

在 band index 赋值处加入：

```python
result.Xc_calibration_status = "uncalibrated_index"
result.Xc_method = f"{first_key}_uncalibrated"
```

有明确 calibration curve 时使用：

```python
result.Xc_calibration_status = "calibrated"
```

无 Xc 时使用：

```python
result.Xc_calibration_status = "unavailable"
```

- [x] **Step 5: analysis_evidence 增加 IR 门控**

在 IR constraints 中加入：

```python
EvidenceConstraint(
    name="ir_xc_uncalibrated",
    kind="soft_warn",
    source="IR",
    severity="WARN",
    description="IR crystallinity index is uncalibrated and should be treated as a diagnostic index.",
    field="Xc_calibration_status",
    rationale="Uncalibrated IR ratios should not be compared directly with DSC/WAXS crystallinity.",
)
```

触发条件：

```python
triggered = str(output.get("Xc_calibration_status") or "").strip() == "uncalibrated_index"
```

- [x] **Step 6: 运行 IR tests**

Run:

```powershell
pytest tests/test_ir_engine.py tests/test_analysis_evidence.py -q
```

Expected: PASS。

- [x] **Step 7: Commit**

```powershell
git add polynexus/core/ir_engine/core.py polynexus/core/ir.py polynexus/core/analysis_evidence.py tests/test_ir_engine.py tests/test_analysis_evidence.py
git commit -m "feat: mark uncalibrated ir crystallinity"
```

---

### Task 6: SAXS static/strain reliability 统一

**Files:**
- Modify: `polynexus/core/saxs_engine/core.py`
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`
- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/core/analysis_evidence.py`
- Test: `tests/test_saxs_batch_parameters.py`
- Test: `tests/test_saxs_scoring.py`
- Test: `tests/test_analysis_evidence.py`

- [x] **Step 1: 写单帧 SAXS reliability 失败测试**

在 `tests/test_saxs_batch_parameters.py` 增加：

```python
def test_static_saxs_exports_diagnostic_only_lc_for_single_fragile_method():
    from polynexus.core.saxs import _compact_saxs_structure_summary

    row = {
        "L_nm": 12.0,
        "lc_nm": 1.1,
        "lc_method": "tangent",
        "lc_confidence": 0.18,
        "Q_star": 0.2,
    }
    summary = _compact_saxs_structure_summary([row])

    assert summary["dominant_lc_reliability_status"] == "diagnostic_only"
    assert "low_lc_confidence" in summary["dominant_lc_reliability_reason"]
```

- [x] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_saxs_batch_parameters.py::test_static_saxs_exports_diagnostic_only_lc_for_single_fragile_method -v`

Expected: FAIL，summary 没有单帧 reliability status。

- [x] **Step 3: 抽出共用 reliability helper**

在 `polynexus/core/saxs_engine/core.py` 中增加：

```python
def classify_single_frame_lc_reliability(params: dict[str, Any]) -> tuple[str, str]:
    reasons: list[str] = []
    lc_conf = float(params.get("lc_confidence", 0.0) or 0.0)
    if lc_conf < 0.2:
        reasons.append("low_lc_confidence")
    elif lc_conf < 0.5:
        reasons.append("limited_lc_confidence")
    method = str(params.get("lc_method") or "").strip()
    if method in {"", "tangent", "idf", "gamma_min"}:
        reasons.append("single_method_fragile")
    q_star = params.get("Q_star")
    try:
        q_star = float(q_star)
    except (TypeError, ValueError):
        q_star = float("nan")
    if np.isfinite(q_star) and (q_star > 50.0 or (0 < q_star < 0.5)):
        reasons.append("q_invariant_anomaly")
    if "low_lc_confidence" in reasons:
        return "diagnostic_only", "|".join(reasons)
    if reasons:
        return "low_confidence", "|".join(reasons)
    return "usable", "stable_structure_support"
```

- [x] **Step 4: SAXS result summary 写入 status**

在 `polynexus/core/saxs.py` 汇总 row 时，如果没有温变序列 status，则调用 `classify_single_frame_lc_reliability(row)` 并写入：

```python
row["lc_reliability_status"] = status
row["lc_reliability_reason"] = reason
```

- [x] **Step 5: 运行 SAXS tests**

Run:

```powershell
pytest tests/test_saxs_batch_parameters.py tests/test_saxs_scoring.py tests/test_analysis_evidence.py -q
```

Expected: PASS。

- [x] **Step 6: Commit**

```powershell
git add polynexus/core/saxs_engine/core.py polynexus/core/saxs_engine/saxs_strain.py polynexus/core/saxs.py polynexus/core/analysis_evidence.py tests/test_saxs_batch_parameters.py tests/test_saxs_scoring.py tests/test_analysis_evidence.py
git commit -m "feat: unify saxs lc reliability status"
```

---

### Task 7: WAXS 仪器展宽与尺寸不确定度

**Files:**
- Modify: `polynexus/core/waxs_engine/config.py`
- Modify: `polynexus/core/waxs_engine/core.py`
- Modify: `polynexus/core/analysis_evidence.py`
- Test: `tests/test_waxs_temperature.py`
- Test: `tests/test_analysis_evidence.py`

- [x] **Step 1: 写 Scherrer 仪器展宽测试**

在 `tests/test_waxs_temperature.py` 增加：

```python
def test_scherrer_subtracts_instrument_broadening():
    from polynexus.core.waxs_engine.core import scherrer_size

    raw = scherrer_size(0.40, 20.0, wavelength_A=1.5406, K=0.9)
    corrected = scherrer_size(0.40, 20.0, wavelength_A=1.5406, K=0.9, instrument_fwhm_deg=0.10)

    assert corrected > raw
```

- [x] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_waxs_temperature.py::test_scherrer_subtracts_instrument_broadening -v`

Expected: FAIL，`scherrer_size()` 不接受 `instrument_fwhm_deg`。

- [x] **Step 3: 扩展 config**

在 `WAXSConfig` 增加：

```python
instrument_fwhm_deg: float = 0.0
size_uncertainty_mode: str = "peak_spread"
```

- [x] **Step 4: 扣除仪器展宽**

修改 `scherrer_size()` 签名：

```python
def scherrer_size(
    fwhm_deg: float,
    two_theta_deg: float,
    wavelength_A: float = 1.5406,
    K: float = 0.9,
    instrument_fwhm_deg: float = 0.0,
) -> float:
```

在函数内替换 beta：

```python
beta_sample_deg = np.sqrt(max(float(fwhm_deg) ** 2 - float(instrument_fwhm_deg) ** 2, 0.0))
if beta_sample_deg <= 1e-9:
    return np.nan
beta_rad = np.radians(beta_sample_deg)
```

- [x] **Step 5: 输出 uncertainty**

在 `analyze_scan()` 完成 peaks 后，增加：

```python
sizes = [
    scherrer_size(pk.get("fwhm_deg", np.nan), pk.get("two_theta", np.nan), config.wavelength_A, instrument_fwhm_deg=config.instrument_fwhm_deg)
    for pk in result.peaks
]
sizes = [value for value in sizes if np.isfinite(value)]
if sizes:
    result.parameters["D_uncertainty_nm"] = float(np.std(sizes)) if len(sizes) > 1 else 0.0
    result.parameters["instrument_broadening_applied"] = bool(config.instrument_fwhm_deg > 0)
```

- [x] **Step 6: 运行 WAXS tests**

Run:

```powershell
pytest tests/test_waxs_temperature.py tests/test_analysis_evidence.py -q
```

Expected: PASS。

- [x] **Step 7: Commit**

```powershell
git add polynexus/core/waxs_engine/config.py polynexus/core/waxs_engine/core.py polynexus/core/analysis_evidence.py tests/test_waxs_temperature.py tests/test_analysis_evidence.py
git commit -m "feat: account for waxs instrument broadening"
```

---

### Task 8: DSC Xc 证据链与基线敏感性

**Files:**
- Modify: `polynexus/core/dsc_engine/core.py`
- Modify: `polynexus/core/dsc.py`
- Modify: `polynexus/core/analysis_evidence.py`
- Test: `tests/test_dsc_engine.py`
- Test: `tests/test_analysis_evidence.py`

- [x] **Step 1: 写 DSC evidence 失败测试**

在 `tests/test_analysis_evidence.py` 增加：

```python
def test_dsc_xc_with_unstable_baseline_is_low_confidence():
    from polynexus.core.analysis_evidence import build_analysis_evidence

    evidence = build_analysis_evidence(
        "DSC",
        {
            "Xc_pct": 38.0,
            "DHm_Jg": 78.0,
            "DHcc_Jg": 18.0,
            "DHm0_Jg": 230.0,
            "DHm0_source": "polymer_reference",
            "baseline_sensitivity_pct": 14.0,
            "integration_boundary_sensitivity_pct": 9.0,
        },
        {},
        {},
    )

    assert evidence["structure_evidence"]["Xc_reliability_status"] == "low_confidence"
    assert "dsc_baseline_sensitive_xc" in evidence["constraint_summary"]["triggered_names"]["soft_warn"]
```

- [x] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_analysis_evidence.py::test_dsc_xc_with_unstable_baseline_is_low_confidence -v`

Expected: FAIL，缺少 DSC Xc reliability status。

- [x] **Step 3: DSC core 输出敏感性字段**

在 DSC peak integration 完成后写入参数：

```python
result.baseline_sensitivity_pct = float(baseline_sensitivity_pct)
result.integration_boundary_sensitivity_pct = float(boundary_sensitivity_pct)
result.DHm0_source = "polymer_reference" if np.isfinite(result.DHm0_Jg) else "missing"
```

如果没有多基线重算，使用保守默认：

```python
result.baseline_sensitivity_pct = 0.0 if result.quality_score >= 0.8 else 12.0
result.integration_boundary_sensitivity_pct = 0.0 if result.quality_score >= 0.8 else 8.0
```

- [x] **Step 4: analysis_evidence 增加 DSC 门控**

在 DSC constraints 加入：

```python
EvidenceConstraint(
    name="dsc_baseline_sensitive_xc",
    kind="soft_warn",
    source="DSC",
    severity="WARN",
    description="DSC crystallinity is sensitive to baseline or integration boundaries.",
    field="baseline_sensitivity_pct",
    rationale="Xc should be downgraded when small baseline changes alter enthalpy materially.",
)
```

触发条件：

```python
baseline_sensitive = _clean_float(output.get("baseline_sensitivity_pct")) or 0.0
boundary_sensitive = _clean_float(output.get("integration_boundary_sensitivity_pct")) or 0.0
triggered = baseline_sensitive >= 10.0 or boundary_sensitive >= 8.0
```

- [x] **Step 5: DSC structure evidence 输出 reliability**

```python
status = "usable"
if baseline_sensitive >= 10.0 or boundary_sensitive >= 8.0:
    status = "low_confidence"
if str(output.get("DHm0_source") or "") == "missing":
    status = "diagnostic_only"
structure_evidence["Xc_reliability_status"] = status
```

- [x] **Step 6: 运行 DSC tests**

Run:

```powershell
pytest tests/test_dsc_engine.py tests/test_analysis_evidence.py -q
```

Expected: PASS。

- [x] **Step 7: Commit**

```powershell
git add polynexus/core/dsc_engine/core.py polynexus/core/dsc.py polynexus/core/analysis_evidence.py tests/test_dsc_engine.py tests/test_analysis_evidence.py
git commit -m "feat: grade dsc crystallinity reliability"
```

---

### Task 9: Joint validation 按 evidence 权重降级

**Files:**
- Modify: `polynexus/core/joint/validation.py`
- Modify: `polynexus/core/joint/dataset.py`
- Test: `tests/test_joint_hub_dataset.py`

- [x] **Step 1: 写低可信 SAXS 不触发硬 ERROR 测试**

在 `tests/test_joint_hub_dataset.py` 增加：

```python
def test_joint_low_confidence_saxs_xc_conflict_is_warn_not_error(tmp_path):
    from polynexus.data.sample_db import SampleDB
    from polynexus.core.joint.dataset import collect_joint_dataset, build_joint_hub_report

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "melt-window", condition_values={"temperature_C": 225})
    db.create_analysis_run(batch_id, "dsc", results_summary={"Xc_pct": 44.0})
    db.create_analysis_run(
        batch_id,
        "saxs",
        results_summary={"L_nm": 12.0, "lc_nm": 1.0},
        analysis_evidence={
            "constraint_summary": {"status": "soft_warn"},
            "structure_evidence": {"lc_reliability_status": "diagnostic_only"},
        },
    )

    report = build_joint_hub_report(collect_joint_dataset(db))

    assert report["ai_context"]["error_count"] == 0
    assert report["ai_context"]["warning_count"] >= 1
```

- [x] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_joint_hub_dataset.py::test_joint_low_confidence_saxs_xc_conflict_is_warn_not_error -v`

Expected: FAIL，当前 phi_c conflict 可能直接 ERROR。

- [x] **Step 3: validation 接收 confidence weights**

修改 `run_all_cross_validations()` 签名：

```python
def run_all_cross_validations(
    sample_id="",
    phi_c_dsc=None,
    phi_c_waxs=None,
    phi_c_saxs=None,
    phi_c_weights=None,
    tm_dsc=None,
    L_saxs=None,
    lc_saxs=None,
    L_bragg=None,
    L_corr=None,
    polymer_family="",
    **kw,
):
```

在 `validate_triple_phi_c()` 中接收 weights：

```python
def validate_triple_phi_c(phi_dsc, phi_waxs, phi_saxs, tolerance=0.05, sample_id="", weights=None):
```

当任一 pair 权重小于 0.5 时，失败 severity 用 WARN：

```python
pair_weight = min(weights.get(ni.lower(), 1.0), weights.get(nj.lower(), 1.0))
severity = "OK" if passed else ("WARN" if pair_weight < 0.5 else "ERROR")
```

- [x] **Step 4: dataset 传入 weights**

在 `validate_joint_row()` 中构造：

```python
weights = {
    tech: _run_evidence_context(row.run(tech))["weight"]
    for tech in ("dsc", "waxs", "saxs")
}
```

并传入：

```python
phi_c_weights=weights,
```

- [x] **Step 5: 运行 Joint regression**

Run:

```powershell
pytest tests/test_joint_hub_dataset.py tests/test_joint_coordinator.py -q
```

Expected: PASS。

- [x] **Step 6: Commit**

```powershell
git add polynexus/core/joint/validation.py polynexus/core/joint/dataset.py tests/test_joint_hub_dataset.py
git commit -m "feat: weight joint checks by evidence"
```

---

### Task 10: 文本、日志、导出解释收口

**Files:**
- Modify: `polynexus/core/*.py`
- Modify: `polynexus/core/*_engine/*.py`
- Modify: `polynexus/gui/i18n.py`
- Modify: `polynexus/gui/main_window.py`
- Test: `tests/test_core.py`
- Test: `tests/test_main_window_persistence.py`

- [x] **Step 1: 定位 mojibake 与 unreachable logger**

Run:

```powershell
rg -n "鈥|鈭|馃|logger\.warning.*$|return False\s*$|return .*logger" polynexus
```

Expected: 输出需要人工确认的用户可见字符串和 unreachable logger 周边行。

- [x] **Step 2: 写核心文本测试**

在 `tests/test_core.py` 增加：

```python
def test_public_engine_labels_do_not_contain_mojibake():
    from polynexus.core import list_techniques, get_engine

    bad_tokens = ("鈥", "鈭", "馃")
    for name in list_techniques():
        engine_cls = get_engine(name)
        public_text = " ".join(
            str(getattr(engine_cls, attr, ""))
            for attr in ("label", "description", "icon")
        )
        assert not any(token in public_text for token in bad_tokens)
```

- [x] **Step 3: 修复用户可见字符串**

把 engine `label/description/icon` 和 `SubModuleSpec` 中明显 mojibake 的文本改为 UTF-8 中文或 ASCII 英文。例如：

```python
label="静态 WAXS"
description="峰分解、结晶度、Scherrer 晶粒尺寸"
icon="WAXS"
```

如果图标在当前字体不稳定，统一使用 ASCII 技术缩写。

- [x] **Step 4: 删除 unreachable logger**

把这种结构：

```python
except Exception as e:
    self.log(f"Failed: {e}")
    return False
    logger.warning("异常已处理", exc_info=True)
```

改成：

```python
except Exception as e:
    self.log(f"Failed: {e}")
    logger.warning("Failed during WAXS load.", exc_info=True)
    return False
```

- [x] **Step 5: 运行核心与 GUI persistence 测试**

Run:

```powershell
pytest tests/test_core.py tests/test_main_window_persistence.py -q
```

Expected: PASS。

- [x] **Step 6: Commit**

```powershell
git add polynexus tests
git commit -m "chore: clean public text and reachable logging"
```

---

## 5. 阶段验收标准

### 5.1 第一阶段完成标准：Evidence 成为一等数据

- 新 run 能持久化 `analysis_evidence`。
- 旧 DB 自动迁移，不丢失旧 `analysis_runs`。
- GUI、CLI、batch 都能保存 evidence。
- Joint Hub 能读到每个 technique 的 evidence context。

### 5.2 第二阶段完成标准：Joint 不再误放大弱结论

- assignment-limited NMR Xc 不作为强结晶度来源。
- uncalibrated IR index 不和 DSC/WAXS 直接硬比。
- diagnostic-only SAXS lc 不触发硬 Tm_GT 结论。
- Joint AI context 能说清楚 issue 是真实跨技术冲突，还是单技术 evidence weak。

### 5.3 第三阶段完成标准：单技术物理矫正语义稳定

- NMR 输出 assignment source、solvent risk、Xc assignment status。
- IR 输出 Xc calibration status。
- SAXS static/temperature/strain 都输出 reliability status。
- WAXS 输出 instrument broadening 与 D uncertainty。
- DSC 输出 baseline/integration sensitivity 与 Xc reliability。

### 5.4 第四阶段完成标准：用户解释可信

- 结果详情、导出、Joint Hub 不只显示数值，还显示 status/reason。
- AI review 不能把 `diagnostic_only` 结果提升成 accepted physical truth。
- 用户可见中文不出现 mojibake。
- 日志能定位失败来源。

---

## 6. 推荐测试矩阵

### 6.1 快速回归

```powershell
pytest tests/test_sample_db.py tests/test_joint_hub_dataset.py tests/test_analysis_evidence.py -q
```

### 6.2 单技术物理可信度回归

```powershell
pytest tests/test_nmr_engine.py tests/test_ir_engine.py tests/test_saxs_batch_parameters.py tests/test_waxs_temperature.py tests/test_dsc_engine.py -q
```

### 6.3 GUI 与持久化回归

```powershell
pytest tests/test_main_window_persistence.py tests/test_sample_browser.py tests/test_joint_analysis_hub.py -q
```

### 6.4 全量回归

```powershell
pytest -q
```

---

## 7. 风险控制

- 不直接改 raw 数值：所有校正和降级都通过新增字段表达。
- 不一次性重构 `analysis_evidence.py`：先增量增加 helper 和 tests，避免 30 万字节级文件出现大范围冲突。
- Joint 的降级优先使用 WARN，不轻易 suppress issue；低可信来源仍要被看见。
- IR/NMR 的结晶度字段先保持兼容，但新增 status 阻止误用。
- WAXS 仪器展宽默认 `0.0`，不改变旧结果；用户配置后才启用。
- DSC 敏感性默认从当前质量分推断，之后再加入真实重积分。

---

## 8. 自检结果

- Spec coverage: 已覆盖 evidence 持久化、Joint 加权、Joint 真优化、NMR、IR、SAXS、WAXS、DSC、日志文本收口。
- Placeholder scan: 未发现空壳式任务描述或空泛实现指令。
- Type consistency: `analysis_evidence` 全程使用 `dict[str, Any]`；Joint confidence context 使用 `status/weight/reasons`；reliability status 使用 `usable/low_confidence/diagnostic_only`。

---

## 9. 建议里程碑

- M1: Task 1-2，约 1 个开发日。目标是 evidence 能被 Joint 看见。
- M2: Task 3 与 Task 9，约 1 个开发日。目标是 Joint 从初始检查升级成 evidence-weighted 判断。
- M3: Task 4-6，约 2-3 个开发日。目标是 NMR/IR/SAXS 弱来源不再被误当强结论。
- M4: Task 7-8，约 2 个开发日。目标是 WAXS/DSC 关键物理量带上不确定度和可靠性。
- M5: Task 10 与全量回归，约 1 个开发日。目标是解释、日志、导出收口。
