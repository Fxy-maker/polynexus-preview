# PolyNexus 智能调参 Agent 与评测体系方案

**版本**：v4.1
**日期**：2026-06-22
**状态**：设计稿
**定位**：v4.0 的 AI 增强补充方案——先建 Eval 评测体系确保"什么是好"，再建 RAG Agent 自动找到"怎么变好"。

---

## 目录

- [§11 问题与目标](#11-问题与目标)
  - 11.1 当前痛点
  - 11.2 两层系统架构
  - 11.3 与 v4.0 的关系
- [§12 Eval 评测数据集](#12-eval-评测数据集)
  - 12.1 为什么先做 eval
  - 12.2 评测指标体系
  - 12.3 数据模型设计
  - 12.4 C 路线：合成数据
  - 12.5 B 路线：真实数据半自动标注
  - 12.6 目录结构
- [§13 RAG 智能调参 Agent](#13-rag-智能调参-agent)
  - 13.1 三层架构总览
  - 13.2 知识层：向量知识库
  - 13.3 推理层：DeepSeek 调参大脑
  - 13.4 执行层：ParameterOrchestrator
  - 13.5 各技术可调参数矩阵
  - 13.6 Prompt 模板设计
  - 13.7 闭环深度策略
  - 13.8 Agent 评估方案
- [§14 实施路线图](#14-实施路线图)
- [§15 桥接实施计划](#15-桥接实施计划)
- [附录](#附录)
  - C. EvalCase JSON schema 完整定义
  - D. 各技术可调参数完整列表
  - E. Agent prompt 示例：一次完整的 WAXS 调参

---

# §11 问题与目标

---

## 11.1 当前痛点

PolyNexus v4.0 已建成 5 种技术的完整分析管线——每个技术都有丰富的可调参数（WAXS ~30 个、SAXS ~25 个、DSC ~20 个、IR ~18 个、NMR ~15 个）。当前依赖用户手动调整这些参数，面临三个问题：

1. **默认参数不是万能的**——PA6 样品参数调好了，换 iPP 就不合适；同一聚合物不同加工工艺（注塑 vs 拉伸），最优参数也不同。
2. **调参依赖经验**——新手用户不知道 `arpls_lam` 该设 1e4 还是 1e8，也不知道什么时候该把非晶 halo 从 1 个加到 2 个。
3. **缺乏客观标准**——用户凭"图看起来好不好"来判断拟合质量，但峰分解"看起来好"可能意味着过拟合（多加了峰），结晶度可以差 10%。

## 11.2 两层系统架构

本方案采用先建靶、后射箭的策略：

```
┌──────────────────────────────────────────────────┐
│  Layer 1: Eval 评测体系（§12）                     │
│  - 定义"什么是好"                                  │
│  - 合成数据 + 真实数据标注 ground truth              │
│  - 多维度指标：物理合规 / 峰位偏差 / 交叉一致 / 人工评分│
│  - 产出：可复现的 benchmark 数据集                  │
└──────────────────────┬───────────────────────────┘
                       │ 为 Agent 提供目标函数
                       ▼
┌──────────────────────────────────────────────────┐
│  Layer 2: RAG 智能调参 Agent（§13）               │
│  - 自动找到"怎么变好"                              │
│  - 知识层：向量知识库（聚合物参考 + 历史成功案例）     │
│  - 推理层：DeepSeek 作为调参大脑                   │
│  - 执行层：多轮闭环迭代                             │
│  - 在 Eval 上做 A/B 测试验证效果                   │
└──────────────────────────────────────────────────┘
```

## 11.3 与 v4.0 的关系

| v4.0 设计 | 本方案承接 |
|-----------|-----------|
| §9 关键参数多技术校验矩阵（φc triple、Tm bidirectional、L consistency） | 落地为 Eval 评测指标 `cross_consistency` |
| §10 自动校验与质量标记（`validation_passed`、`quality_flags`） | 扩展为多维度 EvalMetric，Agent 的 reward 信号来源 |
| 附录 B 聚合物参考数据库（ΔHf、Tg/Tm、晶胞参数） | 成为 RAG 知识库的核心参考数据 |
| 各技术 Config dataclass（WAXSConfig、SAXSConfig 等） | Agent 的动作空间——可调参数的完整定义 |

---

# §12 Eval 评测数据集

---

## 12.1 为什么先做 eval

**没有 ground truth 的 Agent 会走向过拟合。** 实验物理中的经典陷阱：

| 什么是"更好的拟合" | r² 怎么看 | 物理上真的更好吗？ |
|-------------------|----------|-------------------|
| 峰函数换成 pseudo_voigt | ↑（多一个 fraction 自由度） | 不一定——对低结晶度样品可能引入伪影 |
| 非晶 halo 1 个→2 个 | ↑（多 3 个参数） | 不一定——没有物理理由多余一个非晶峰 |
| arpls_lam 降低 | ↑（基线更贴合） | 不一定——可能吃掉真实的宽衍射特征 |
| smooth_window 缩小 | ↑（保留更多信号） | 不一定——可能是噪声被误拟合为峰 |

**Agent 必须同时在统计指标和物理指标上都好，才能证明它真的"更胜一筹"。** Eval 数据集提供物理指标的 ground truth。

## 12.2 评测指标体系

结合 v4.0 §9-10 已有框架，扩展为 4 个维度：

### 指标总览

| 指标 | 缩写 | 说明 | 来源 | Agent 优化目标 |
|------|------|------|------|--------------|
| **物理合规率** | `PHYS` | 输出参数在物理可行范围内（结晶度 0-100%、Tg/Tm 在文献范围、峰宽 > 0） | v4.0 §10.3 合理性校验扩展 | 必须 100%，硬约束 |
| **峰位偏差** | `PEAK` | 拟合峰位 vs 参考峰位的 Δ2θ（WAXS）/ Δν（IR）/ Δδ（NMR） | polymers/*.json + polymer_peaks_db | < 0.3° (WAXS) |
| **交叉一致性** | `CROSS` | 多技术对应参数的一致性（φc ±5%、Tm ±3°C、L ±3%） | v4.0 §9 校验矩阵 | 最小化偏差 |
| **人工评分** | `HUMAN` | 专家看图判断拟合质量（1-5 分） | 人工审阅 | ≥ 4（好） |

### 物理合规率 (PHYS) — 详细规则

针对每个技术的输出参数，硬约束：

**WAXS：**
- `Xc_pct` ∈ [0, 100]（v4.0 已 clamp 到 95%，检查 clamp 是否触发）
- `D_Scherrer_nm` ∈ [1, 1000]
- 每峰 `fwhm` > 0.1° 且 < 10°
- 每峰 `center` 在数据 2θ 范围内
- `crystal_system` 非 `"unknown"` 时，晶胞参数与文献一致（v4.0 附录 B.3）

**DSC：**
- `Tg_C` / `Tm_peak_C` / `Tc_peak_C` 在各自聚合物的 BOUNDS 内（v4.0 `TG_BOUNDS` / `TM_BOUNDS`）
- `DHm_Jg` > 0（熔融峰）且 < `DHm0_Jg` 的 1.2 倍
- `Xc_pct` ∈ [0, 100]
- 反卷积分量占比 ≥ 1%

**SAXS：**
- `L_nm` ∈ [3, 150]（v4.0 `SAXS_L_BOUNDS`）
- `lc_nm` < `L_nm`（片晶厚度不能超过长周期）
- `phi_c` ∈ [0, 1]
- Porod 区域 I·q⁴ 不单调上升（无高 q 异常）

**IR / NMR：** 峰位在各自的合理区间；计算 vs 实验 RMSD 达标（v4.0 §7.7/§8.7）。

### 峰位偏差 (PEAK) — 详细规则

对可以被聚合物参考数据库验证的峰（已知归属的晶峰），计算：

```
Δ2θ = |fit_center - ref_center|    (WAXS)
Δν  = |fit_wavenumber - ref_wavenumber|  (IR)
Δδ  = |fit_ppm - ref_ppm|          (NMR)
```

参考来源：`polynexus/data/polymers/*.json` 的 `waxs_peaks` / `ir_peaks` / `nmr_13c` 字段，以及 `WAXSConfig.polymer_peaks_db` 的硬编码值。

**容差：**
- WAXS: Δ2θ < 0.3°（考虑仪器零点漂移）
- IR: Δν < 5 cm⁻¹
- NMR: Δδ < 1 ppm（¹³C）/ < 0.2 ppm（¹H）

### 交叉一致性 (CROSS)

直接调用 `joint/validation.py` 的三项检查（v4.0 §9 已设计，§10 未完成接入）：

| 检查 | 函数 | 条件 |
|------|------|------|
| φc 三重验证 | `validate_triple_phi_c()` | 同一 BATCH 有多技术数据 |
| Tm 双向校验 | `validate_tm_bidirectional()` | DSC + SAXS 同时存在 |
| L 一致性 | `validate_L_consistency()` | SAXS Bragg 和 corr 两法 |

当前限制：交叉验证**仅在同一个 Sample 的多个 Batch 分别用不同技术分析后可用**。如果只有单一技术数据，CROSS 指标标记为 N/A。

### 综合评分

```
EvalScore = w1 × PHYS + w2 × (1 - normalized_PEAK) + w3 × CROSS + w4 × HUMAN/5
```

默认权重：`w1=0.25, w2=0.25, w3=0.25, w4=0.25`。分数 ∈ [0, 1]，越高越好。

## 12.3 数据模型设计

### EvalCase（一个评测案例）

```python
@dataclass
class EvalCase:
    case_id: str                    # "waxs_synth_pa6_alpha_001"
    technique: str                  # "waxs" | "dsc" | "saxs" | "ir" | "nmr"
    submodule: str                  # "static" | "strain" | "temperature" | ...
    data_file: str                  # 相对 测试数据/ 的路径
    polymer_name: str               # "PA6"
    polymer_phase: str | None       # "alpha" | "gamma" | ...
    config_overrides: dict          # 可选，覆盖默认参数
    ground_truth: GroundTruth
    source: str                     # "synthetic" | "literature" | "cross_validation" | "expert_review"
    notes: str                      # 人工备注

@dataclass
class GroundTruth:
    # 所有字段为 (min, max) 范围，None 表示不检查此项
    # --- WAXS ---
    Xc_pct: tuple[float, float] | None = None
    peak_centers: list[tuple[float, float]] | None = None  # [(19.7, 20.3), (23.7, 24.3)]
    D_Scherrer_nm: tuple[float, float] | None = None
    crystal_form: str | None = None
    # --- DSC ---
    Tm_peak_C: tuple[float, float] | None = None
    DHm_Jg: tuple[float, float] | None = None
    Tg_C: tuple[float, float] | None = None
    Tc_peak_C: tuple[float, float] | None = None
    # --- SAXS ---
    L_nm: tuple[float, float] | None = None
    lc_nm: tuple[float, float] | None = None
    phi_c: tuple[float, float] | None = None
    Rg_nm: tuple[float, float] | None = None
    # --- IR ---
    peak_wavenumbers: list[tuple[float, float]] | None = None
    # --- NMR ---
    peak_shifts: list[tuple[float, float]] | None = None
    Xc_pct: tuple[float, float] | None = None

@dataclass
class EvalResult:
    case_id: str
    technique: str
    phys_score: float              # 0-1, 物理合规率
    peak_score: float              # 0-1, 峰位偏差分
    cross_score: float | None      # 0-1, 交叉一致性分 (N/A if single-technique)
    human_score: float | None      # 1-5, 人工评分 (N/A if synthetic)
    composite: float               # 综合分
    details: dict                  # 逐项细分
    parameters_used: dict          # 实际使用的参数
    output_parameters: dict        # 分析输出的参数
```

### EvalCase JSON 存储格式

一个 `.json` 文件 = 一个 case。详见附录 C。

### JSON 解析鲁棒性

EvalRunner 加载 EvalCase 时必须具备防御性解析能力，因为 case 文件可能被人工编辑引入格式错误：

1. **Schema 校验** — 加载时自动对照附录 C 的 JSON Schema 校验，不合规的 case 跳过并报告具体错误行
2. **类型强制** — `ground_truth` 中的范围数组缺少元素时（如只写了一个值），自动展开为对称范围 `[v*0.95, v*1.05]`
3. **路径解析** — `data_file` 支持三种格式：
   - `synth:<id>` → 调用合成数据生成器实时生成
   - `测试数据/waxs/...` → 相对项目根 `测试数据/` 解析
   - 绝对路径 → 直接使用
4. **`--dry-run` 模式** — `EvalRunner --dry-run` 仅校验所有 case 文件的 JSON schema，不实际运行分析管线。CI 中配合 `pytest tests/eval/` 使用，确保新 case 文件格式正确

## 12.4 C 路线：合成数据

每项技术生成 3–5 个合成 case，ground truth 完全已知。

### C.1 WAXS 合成策略

基于 `WAXSConfig.polymer_peaks_db` 和 `polymers/*.json` 的已知峰位/强度，生成理想 I(2θ)：

```
I(2θ) = baseline(2θ) + Σ crystal_peaks + Σ amorphous_halos + noise
```

- **baseline**: 线性（斜率±小扰动），模拟仪器基线漂移
- **crystal_peaks**: Pseudo-Voigt，center 从数据库取，sigma ∈ [0.2, 0.8]°，amplitude 从数据库相对强度推导
- **amorphous_halos**: 1–2 个宽 Pseudo-Voigt（sigma ∈ [5, 15]°），center 散布在 15°–30°
- **noise**: Poisson 噪声（模拟光子计数统计），强度水平参考真实 `PA6.raw` 的 SNR

**合成 case 列表：**

| case_id | 聚合物 | 晶型 | 特点 |
|---------|--------|------|------|
| `waxs_synth_pa6_alpha` | PA6 | α | 双峰 20.0°+24.0°，结晶度 ~45%，1 halo |
| `waxs_synth_pa6_alpha_gamma` | PA6 | α+γ 混合 | 三峰 20.0°+21.5°+24.0°，结晶度 ~35%，2 halo |
| `waxs_synth_pet` | PET | — | 多峰 (16.3°–32.2°)，结晶度 ~30% |
| `waxs_synth_ipp_alpha` | iPP | α | 五峰 (14.1°–21.9°)，结晶度 ~50% |
| `waxs_synth_low_xc` | PA6 | α | 低结晶度 ~15%，高噪声，测试极限性能 |

### C.2 DSC 合成策略

合成热流曲线：Tg 阶跃 + 冷结晶放热峰 + 熔融吸热峰，Gaussian 线型，加白噪声。

| case_id | 特点 |
|---------|------|
| `dsc_synth_heating_standard` | Tg ~50°C, Tcc ~120°C, Tm ~220°C，典型 PA6 |
| `dsc_synth_heating_cold_cc` | 含显著冷结晶峰，Tcc 与 Tg 接近 |
| `dsc_synth_cooling` | 降温结晶，Tc ~170°C |
| `dsc_synth_no_tg` | 基线平直无 Tg，只有 Tm，测试 Tg 误检 |

### C.3 SAXS 合成策略

合成 I(q)：Guinier 区（低 q）+ 片晶峰（中 q）+ Porod 尾（高 q），加 Poisson 噪声。

| case_id | 特点 |
|---------|------|
| `saxs_synth_lamellar` | 有清晰 Bragg 峰，L ~12 nm |
| `saxs_synth_guinier_only` | 无 Bragg 峰，只有 Guinier + Porod |
| `saxs_synth_noisy` | 高噪声，测试极限性能 |

### C.4 IR / NMR 合成策略

IR：基于已知官能团频率的 Lorentzian 叠加 + 基线 + 噪声。
NMR：基于 `polymers/*.json` 中 `nmr_13c` 的 Lorentzian 峰 + 噪声。

具体 case 略（各 3 个），与 WAXS/DSC/SAXS 同模式。

### C.5 合成数据的核心价值

- **Ground truth 绝对精确**——因为我们设的，没有标注歧义
- **可复现**——种子固定，任何人重跑得到相同结果
- **测试极限**——可以故意生成极端低 SNR、低结晶度、重叠峰
- **Agent 必须在合成集上 PHYS=100% 且 PEAK<0.1°**，否则就是乱调

## 12.5 B 路线：真实数据半自动标注

### Step 1: 自动批量重跑

从 `测试数据/` 中为每个技术选代表文件，用默认参数跑 `run_pipeline()`：

| 技术 | 选定文件 | 备注 |
|------|---------|------|
| WAXS | `waxs/普通广角/PA6.raw`、`50.raw`、`70.raw` | PA6 为主，50/70 可能是不同工艺 |
| DSC | `dsc数据/标准DSC数据格式一/FXY-PA6.txt`、`FXY-PA6TXT.txt` | 格式一文本 DSC |
| DSC | `dsc数据/标准DSC数据格式二/30.xls`、`默认(42).xls` | 格式二 Excel DSC |
| SAXS | `小角数据/普通小角/...PA6...edf` | PA6 静态 SAXS |
| IR | `IR/普通红外/TXT.SPA`、`YL.SPA` | SPA 格式红外 |
| NMR | `NMR数据/20260527-xye_Carbon-1-1/...Carbon...jdf` | 液体 C 谱 |
| NMR | `NMR数据/液体核磁/H谱/fid` | 液体 H 谱 |

**产出物**：每个 case 的审计报告（HTML 格式），包含：
- 拟合图（峰分解 / I(q) / 热流曲线）
- **Diff 视图**：当同一 case 有默认参数结果和人工微调后的结果时，并排展示 Round 0 vs Round N 的拟合图 + 参数对比表，方便快速判断改善方向
- 输出参数表格（对比 12.2 指标的 pass/fail）
- 与 `polymers/*.json` + `polymer_peaks_db` 参考值的偏差标注

### Step 2: 人工审阅

专家（你）对每张审计报告标注：

| 标记 | 含义 | 后续动作 |
|------|------|---------|
| ✅ 通过 | 拟合正确，参数合理 | 当前参数结果 → GroundTruth 范围 |
| ⚠️ 需微调 | 方向对，参数需调整 | 手动改 Config 重跑，审阅新结果 |
| ❌ 失败 | 拟合错误 | 标注原因，排除出 eval 集 |

### Step 3: 自动生成 EvalCase JSON

审阅通过后，自动把标注结果写入 `tests/eval/cases/real/` 下的 EvalCase JSON。

## 12.6 目录结构

```
tests/eval/
├── __init__.py
├── models.py              # EvalCase, GroundTruth, EvalMetric, EvalResult
├── runner.py              # EvalRunner: load case → run pipeline → compute metrics
├── synth_generator.py     # 合成数据生成器
├── audit_reporter.py      # 审计报告生成器 (HTML)
├── cases/
│   ├── synth/             # 合成数据
│   │   ├── waxs_pa6_alpha_single.json
│   │   ├── waxs_pa6_alpha_gamma_mix.json
│   │   ├── waxs_pet.json
│   │   ├── waxs_ipp_alpha.json
│   │   ├── waxs_low_xc.json
│   │   ├── dsc_heating_standard.json
│   │   ├── dsc_heating_cold_cc.json
│   │   ├── dsc_cooling.json
│   │   ├── dsc_no_tg.json
│   │   ├── saxs_lamellar.json
│   │   ├── saxs_guinier_only.json
│   │   ├── saxs_noisy.json
│   │   ├── ir_*.json       # 各 3 个
│   │   └── nmr_*.json      # 各 3 个
│   └── real/              # 真实数据（审阅后生成）
│       ├── waxs_pa6_default.json
│       ├── dsc_pa6_heating.json
│       ├── saxs_pa6_static.json
│       └── ...
└── audit_reports/         # 审阅工作台（临时）
    ├── waxs_pa6_audit.html
    ├── dsc_pa6_audit.html
    └── ...
```

---

# §13 RAG 智能调参 Agent

---

## 13.1 三层架构总览

```
                         ┌─────────────────────────┐
                         │    User / GUI / CLI      │
                         │   "帮我调 PA6 WAXS 参数"   │
                         └───────────┬─────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────┐
│                          ParameterAgent                                  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                     知识层 (VectorStore)                           │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────┐  │  │
│  │  │ 聚合物参考数据    │  │ 历史成功案例     │  │ 文献规则          │  │  │
│  │  │ polymers/*.json  │  │ analysis_runs   │  │ 硬编码约束        │  │  │
│  │  │ + peaks_db       │  │ (r²>0.95)       │  │ e.g. PA6 α 200   │  │  │
│  │  │                  │  │                  │  │ 必在 20.0±0.5°   │  │  │
│  │  └────────┬─────────┘  └────────┬─────────┘  └────────┬──────────┘  │  │
│  │           └─────────────────────┼───────────────────────┘             │  │
│  │                                 ▼                                    │  │
│  │                     ChromaDB (HuggingFace embedding)                  │  │
│  └─────────────────────────────────┬───────────────────────────────────┘  │
│                                    │ 检索结果                              │
│                                    ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                     推理层 (DeepSeek Brain)                        │  │
│  │  System Prompt: 你是聚合物分析专家，了解 WAXS/DSC/SAXS/IR/NMR       │  │
│  │  User Prompt:   当前参数 + 拟合结果 + 参考值 + 历史案例 + 可调参数表  │  │
│  │  LLM Output:    JSON {changes, reasoning}                          │  │
│  └─────────────────────────────────┬───────────────────────────────────┘  │
│                                    │ 建议的参数变更                         │
│                                    ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                  执行层 (ParameterOrchestrator)                    │  │
│  │  1. 接收 LLM 建议 → 应用到 Config                                  │  │
│  │  2. 执行 engine.analyze() 重跑                                     │  │
│  │  3. QualityEvaluator 评估新结果 vs 上一轮                           │  │
│  │  4. 判断收敛: ΔEvalScore < threshold? max_rounds?                  │  │
│  │  5. 未收敛 → 打包新状态 → 回到推理层                               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

## 13.2 知识层：向量知识库

### 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 向量数据库 | **ChromaDB** | 纯 Python，零外部依赖，嵌入式运行，适合桌面应用 |
| Embedding 模型 | **双模式**：DeepSeek Embedding API → `BAAI/bge-small-zh-v1.5`（离线 fallback） | 默认用 API 统一密钥；离线环境自动切换本地 HuggingFace 模型 |
| 检索策略 | 混合检索：语义相似度 + 关键词过滤（polymer_name + technique） | 确保检索到正确的聚合物和技术 |

### Embedding 双模式设计

```python
class EmbeddingProvider:
    """Auto-select embedding backend based on availability."""
    def __init__(self, mode: str = "auto"):
        self.mode = mode  # "auto" | "api" | "local"

    def _try_api(self, texts: list[str]) -> np.ndarray:
        """DeepSeek / OpenAI-compatible embedding API."""
        import openai
        client = openai.OpenAI(
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1"
        )
        resp = client.embeddings.create(model="deepseek-embed", input=texts)
        return np.array([d.embedding for d in resp.data])

    def _try_local(self, texts: list[str]) -> np.ndarray:
        """Offline HuggingFace model."""
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
        return model.encode(texts, normalize_embeddings=True)

    def embed(self, texts: list[str]) -> np.ndarray:
        if self.mode == "local":
            return self._try_local(texts)
        if self.mode == "api":
            return self._try_api(texts)
        # auto: try API first, fallback to local
        try:
            return self._try_api(texts)
        except Exception:
            logger.warning("API embedding unavailable, falling back to local BGE model")
            return self._try_local(texts)
```

**切换方式**：环境变量 `POLYNEXUS_EMBEDDING_MODE=local|api|auto`（默认 auto）。离线部署时设为 `local`，首次运行自动下载 `BAAI/bge-small-zh-v1.5`（~100MB）。

### 数据来源与 Chunk 策略

| 数据源 | Chunk 方式 | 预估 chunk 数 |
|--------|-----------|-------------|
| `polymers/*.json` 聚合物参考数据 | 按"聚合物+技术+相"分 chunk | ~150（7 个文件 × ~20 聚合物 × 不同相） |
| `WAXSConfig.polymer_peaks_db` | 每个晶型一个 chunk | ~16（PA6 α/γ, PE, iPP α/β, PET, PEEK, PTFE, PVDF α/β, POM, PCL, PLLA α） |
| `analysis_runs` 历史成功案例（r² > 0.95） | 每个 run 一个 chunk（仅存 parameters + results_summary） | ~10-50（取决于历史积累） |
| 硬编码物理约束 | 一个 chunk 一个规则 | ~10（Tg/Tm bounds、L bounds、φc 一致性规则等） |

### 历史案例衰减策略

`analysis_runs` 中的历史案例在检索时按时间加权，避免过时参数影响新样品：

```python
def compute_case_weight(run_created_at: str, current_time=None) -> float:
    """Exponential decay: weight = exp(-age_months / tau)."""
    from datetime import datetime
    if current_time is None:
        current_time = datetime.now()
    age_days = (current_time - datetime.fromisoformat(run_created_at)).days
    tau_days = 180  # 时间常数: 6 个月
    return math.exp(-age_days / tau_days)
```

- **τ = 6 个月**：6 个月前的案例权重衰减到 ~37%
- **硬 floor**：权重最低 0.1（即使很老的案例也保留最低参考价值）
- **RAG 检索时**：`similarity_score × case_weight` 综合排序，top-K 取 3 个
- **软件升级后**：当 PolyNexus 版本大升级时（如 v4.x → v5.0），可选择清空旧案例或打 `deprecated` 标记

### 冷启动策略

项目初期 `analysis_runs` 表为空（0 条历史案例），RAG 退化为纯聚合物参考数据库。此模式下 Agent 行为需做降级：

| 降级项 | 正常模式（有历史案例） | 冷启动模式（0 案例） |
|--------|---------------------|-------------------|
| **RAG 数据源** | `polymers/*.json` + `analysis_runs` | 仅 `polymers/*.json` + `polymer_peaks_db` |
| **检索结果** | 参考数据 + 3 个相似历史案例 | 仅参考数据，检索结果标注 `"历史案例: 无（冷启动模式）"` |
| **初始参数** | 可选最相似案例的参数作为起点 | 使用默认 Config（不做预设） |
| **Agent 建议** | 可参考历史成功参数组合 | 更保守——优先调整低风险参数，不提议加 halo 或改 `arpls_lam` |
| **成功标准** | EvalScore ≥ 0.9 | 只要求 PHYS=100% + PEAK < 容差（§12.2），不要求 CROSS/HUMAN |
| **案例积累** | 已有案例供检索 | 每次用户确认 Agent 建议后，自动写入 `analysis_runs`（标记 `ai_tuned=True`），RAG 渐趋丰富 |

**从冷启动到热身**：大约 5-10 次成功的 AI 调参后（每个聚合物-技术组合），RAG 检索能返回至少 1 个相关历史案例。此时 Agent 自动从"保守模式"切换为"正常模式"——在 AgentState 中检测到 `similar_cases` 非空即触发。

**冷启动的 System Prompt 注入**：当 `len(similar_cases) == 0` 时，在 prompt 中追加：

```
⚠️ 冷启动模式：当前无历史调参案例。请仅基于聚合物参考数据库和物理约束给出建议。
优先调整低风险参数；高风险参数（arpls_lam、max_peaks）仅在基线或峰数明显不合理时才建议调整。
建议的 confidence 应适当降低（≤ 0.7），以反映缺少经验数据的不确定性。
```

### Embedding 内容格式

```
[聚合物: PA6] [技术: WAXS] [相: alpha]
参考峰位: 2θ=20.0° (200, I=100), 2θ=24.0° (002/202, I=80)
晶系: 单斜 P2₁, a=9.56Å b=17.2Å c=8.01Å
典型结晶度: 35-55%
非晶 halo: 1-2 个宽峰, 中心 ~21°, sigma 5-15°
```

```
[聚合物: PA6] [技术: WAXS] [成功案例: run_abc123]
参数: peak_function=pseudo_voigt, smooth_window=5, arpls_lam=1e5,
      amorphous_n_peaks=2, background_method=polynomial
结果: Xc_pct=43.2%, n_peaks=4, D_Scherrer=12.3nm, r²=0.997
```

## 13.3 推理层：DeepSeek 调参大脑

### 每轮输入结构

```python
@dataclass
class AgentState:
    # 识别信息
    polymer_name: str           # "PA6"
    polymer_phase: str | None   # "alpha"
    technique: str              # "waxs"
    submodule: str              # "static"

    # 当前参数
    current_config: dict        # WAXSConfig.to_dict()

    # 分析结果（本轮）
    output_parameters: dict     # AnalysisResult.parameters
    r_squared: float
    redchi: float
    residuals_pattern: str      # 残差的定性描述（"随机分布" / "20-25°系统偏置" / "低角区漂移"）
    quality_flags: dict

    # 参考知识（RAG 检索注入）
    reference_peaks: list       # 聚合物参考峰位
    reference_ranges: dict      # 物理范围（Tg/Tm bounds 等）
    similar_cases: list         # 相似样品的历史成功参数

    # 可调参数白名单
    tunable_params: list[ParamSpec]  # 见 §13.5

    # 上一轮信息（第二轮起）
    previous_score: EvalResult | None
    improvement: float | None
```

### DeepSeek 期望输出

严格的 JSON 格式（通过 `response_format={"type": "json_object"}` 强制）：

```json
{
  "analysis": "残差在 20-25° 区间有微弱系统偏置（可能是非晶 halo 中心偏移），
              当前 r²=0.986，结晶度 38.2% 低于 PA6 α 典型值 (35-55% 下限)。
              峰位偏差：200 峰 20.05° vs 参考 20.0° 偏差 0.05° → OK",
  "changes": {
    "amorphous_n_peaks": 2,
    "amorphous_subtraction": "spline",
    "peak_function": "pseudo_voigt"
  },
  "reasoning": {
    "amorphous_n_peaks": "当前 1 个 halo 无法充分描述非晶散射，残差 20-25° 有结构；
                          加第 2 个 halo 可改善拟合，参考 PA6 成功案例多用 n=2",
    "amorphous_subtraction": "spline 比 polynomial 更灵活，可适应 PA6 的复杂非晶包络",
    "peak_function": "当前 gaussian 尾太轻，pseudo_voigt 的 Lorentzian 分量能更好描述实测峰形"
  },
  "expected_improvement": {
    "r_squared": "0.986 → 0.992+",
    "Xc_pct": "38.2% → 42-48%（更接近典型范围）"
  },
  "risk": "medium",
  "risk_note": "加第 2 个 halo 增加 3 个自由参数，有轻微过拟合风险；但如果 r² 改善 > 0.005 且 Xc 进入合理范围，值得采纳"
}
```

**拒绝（无需调整）时的输出**：当 Agent 判断当前拟合已最优时，返回：

```json
{
  "analysis": "当前 R²=0.997，PHYS=100%，PEAK 偏差均 < 0.05°，残差随机分布。
               所有指标已达到或超过典型 PA6 α WAXS 分析的最佳水平。
               当前参数已最优，无需调整。",
  "changes": {},
  "reasoning": {},
  "expected_improvement": {},
  "risk": "none",
  "risk_note": "无需调整——当前结果优于历史 95% 的 PA6 α WAXS 分析"
}
```

`ParameterOrchestrator` 收到空 `changes` 时立即终止迭代，标记为 `converged: optimal`。

## 13.4 执行层：ParameterOrchestrator

### 迭代循环

```
Round 0 (baseline): 用默认参数跑 analyze() → 得到 r²₀, redchi₀, 残差模式₀

Round 1: 打包 AgentState → DeepSeek → 解析 changes → 应用 Config → 重跑 analyze()
         → QualityEvaluator 计算 EvalResult
         → 如果 EvalScore₁ > EvalScore₀: 保留为 best
         → 如果改善 < threshold (1%): 收敛，退出

Round 2: 打包新 AgentState（含前两轮对比）→ DeepSeek → ... → 同 Round 1
         ...

最大轮数: 5（B 层闭环）/ 10（C 层闭环）
```

### QualityEvaluator

在 Agent 闭环中，`QualityEvaluator` 用 Eval 数据集相同的逻辑（§12.2）计算分数，但适应"没有人工标注"的场景：

- `PHYS` 总是可用（只依赖物理可行性规则）
- `PEAK` 只在能匹配到参考峰时可用
- `CROSS` 只在有对应的多技术数据时可用
- `HUMAN` 不可用 → 权重自动重分配

**权重重分配规则**（根据可用指标自动调整）：

| 可用指标组合 | PHYS | PEAK | CROSS | HUMAN | 使用场景 |
|-------------|------|------|-------|-------|---------|
| 全部可用 | 0.25 | 0.25 | 0.25 | 0.25 | Eval 数据集评测 |
| 缺 HUMAN（Agent 闭环） | 0.40 | 0.35 | 0.25 | — | Agent 自动迭代 |
| 缺 HUMAN + CROSS（单技术） | 0.55 | 0.45 | — | — | 仅一种技术的数据 |
| 缺 HUMAN + CROSS + PEAK | 1.00 | — | — | — | 无参考数据库的未知聚合物 |

重分配原则：缺位指标的权重按现有指标的默认比例分配给剩余指标。如果只剩 PHYS，权重为 1.0（此时 Agent 退化为纯物理合规性优化）。

```python
def redistribute_weights(available: set[str]) -> dict[str, float]:
    """Return weight dict for available indicators."""
    default_weights = {"PHYS": 0.25, "PEAK": 0.25, "CROSS": 0.25, "HUMAN": 0.25}
    active = {k: v for k, v in default_weights.items() if k in available}
    total_active = sum(active.values())
    return {k: v / total_active for k, v in active.items()}
```

### 收敛判定

```python
def has_converged(current_score, best_score, round_num, max_rounds):
    if round_num >= max_rounds: return True

    improvement = (current_score - best_score) / best_score
    if improvement < 0.01:     # < 1% 改善
        return True

    return False
```

### 回滚保护

每轮之前深拷贝当前的最优 Config。如果 LLM 建议导致 `PHYS=0`（物理不可行），自动回滚并请求 LLM 换方案。

## 13.5 各技术可调参数矩阵

Agent 的动作空间——每个参数有 `name` / `current_value` / `range` / `description` / `risk`（低/中/高）。

### WAXS（最丰富，~9 个可调参数）

| 参数 | Config 字段 | 范围 | 默认 | 调参风险 | Agent 策略 |
|------|------------|------|------|---------|-----------|
| 峰函数 | `peak_function` | gaussian / lorentzian / pseudo_voigt | pseudo_voigt | 低 | 看残差对称性；不对称 → voigt |
| 平滑窗口 | `smooth_window` | 3–15 (奇数) | 5 | 中 | 噪声大→加大；峰被抹平→减小 |
| 背景方法 | `background_method` | linear / polynomial / spline / chebyshev | linear | 中 | 基线弯曲→升级 |
| arPLS λ | `arpls_lam` | 1e4–1e8 | 1e5 | 高 | 基线太平/太凸→调整 |
| 非晶模型 | `amorphous_subtraction` | spline / polynomial / manual | polynomial | 中 | 结晶度异常→换模型 |
| 非晶峰数 | `amorphous_n_peaks` | 1–2 | 2 | 中 | 残差有结构→加 halo |
| 峰间距 | `peak_distance` | 0.5–2.0° | 0.8 | 低 | 漏峰→减小；假峰→加大 |
| 2θ 零点 | `two_theta_offset` | -0.5–0.5° | 0 | 低 | 峰位系统性偏差→校准 |
| 峰数上限 | `max_peaks` | 4–12 | 8 | 高 | 漏峰→加；过拟合→减 |

**参数依赖关系**：以下参数之间存在耦合，Agent 不得独立调整：

| 依赖组 | 涉及参数 | 关系 | Agent 约束 |
|--------|---------|------|-----------|
| arPLS 基线组 | `arpls_lam` + `arpls_diff_order` | lam 增大 → 基线更平；diff_order=1 刚性/2 平滑 | 调整 lam 时固定 diff_order；切换 diff_order 时重置 lam 到默认 |
| 峰检测组 | `peak_distance` + `max_peaks` + `peak_height_min` | distance 越小 → 峰数越多；max_peaks 为硬上限 | 先调 peak_distance，需要更多峰时再动 max_peaks；peak_height_min 最后调 |
| 平滑组 | `smooth_window` + `smooth_order` | window 越大 → 平滑越强；order 越高 → 保留更多高频 | 只调 window，不动 order（order=3 是 Savgol 通用最优） |
| 非晶组 | `amorphous_subtraction` + `amorphous_n_peaks` | 换 subtraction 方法会影响 halo 最优数量 | 先定 subtraction 方法，再根据残差调 n_peaks |
| 结晶度窗 | `crystallinity_min_two_theta` + `crystallinity_max_two_theta` | 窗口决定积分范围 | 两边界必须保持 min < max，且间距 ≥ 10° |

这些依赖关系硬编码在 `ParameterOrchestrator` 中：当 LLM 建议修改依赖组中任一参数时，Orchestrator 会根据上表自动补全关联参数的合理值，或拒绝不兼容的组合（如 `crystallinity_min > crystallinity_max`）。

### SAXS（~7 个可调参数）

| 参数 | Config 字段 | 范围 | 默认 | 调参风险 | Agent 策略 |
|------|------------|------|------|---------|-----------|
| 背景处理 | `baseline_method` | subtract / normalize / none | normalize | 低 | — |
| 平滑窗口 | `smooth_window` | 3–31 | 7 | 中 | 噪声大→加大 |
| q 下限 | `q_range_min` | 0.001–1.0 | 0.01 | 中 | 低 q 异常→提高下限 |
| q 上限 | `q_range_max` | 0.1–10.0 | 2.0 | 中 | Porod 区截断→调整 |
| Guinier 点数 | （拟合内部） | 5–len(q)//3 | len(q)//5 | 中 | Rg 不合理→调整 |
| 长周期方法 | `L_method` | bragg / lorentz / auto | auto | 低 | 单峰 vs 多峰选择 |
| lc 方法 | `lc_method` | tangent / gamma_min / ruland | tangent | 中 | lc > L 异常→换方法 |

### DSC（~5 个可调参数）

| 参数 | Config 字段 | 范围 | 默认 | 调参风险 | Agent 策略 |
|------|------------|------|------|---------|-----------|
| 基线校正 | `baseline_corr` | linear / tangential / sigmoid | tangential | 低 | 基线弯曲→升级 |
| Tg 方法 | `Tg_method` | half_height / inflection / onset | half_height | 低 | — |
| 平滑窗口 | `smooth_window` | 3–15 | 5 | 中 | 噪声→加大 |
| ΔHm0 参考 | `crystallinity_std` | 80–330 J/g | 数据库自动 | 低 | 聚合物选错→手动指定 |
| 峰检测阈值 | （内部） | — | — | 中 | 漏峰→降阈值 |

### IR（~4 个可调参数）

| 参数 | Config 字段 | 范围 | 默认 | 调参风险 |
|------|------------|------|------|---------|
| 基线方法 | `baseline_method` | rubberband / linear / polynomial / als | als | 低 |
| 平滑窗口 | `smooth_window` | 3–15 | 5 | 中 |
| 峰函数 | `lineshape` | lorentzian / gaussian / pseudo_voigt | lorentzian | 低 |
| 频率校正 | `freq_correction_factor` | 0.90–1.00 | 0.9613 | 低（仅 DFT 模式） |

### NMR（~4 个可调参数）

| 参数 | Config 字段 | 范围 | 默认 | 调参风险 |
|------|------------|------|------|---------|
| 基线方法 | `baseline_method` | polynomial / linear / spline | polynomial | 低 |
| 基线阶数 | `baseline_order` | 1–9 | 5 | 中 |
| 展宽 | `lb_Hz` | 1–20 | 5 | 中 |
| 反卷积方法 | `deconvolution_method` | lorentzian / gaussian / mixed | mixed | 低 |

## 13.6 Prompt 模板设计

### System Prompt（所有技术共用）

```
你是一位高分子物理表征专家，精通 WAXS、SAXS、DSC、IR、ssNMR 五种技术的数据分析。

你的任务：根据当前分析结果（拟合质量、残差模式、与参考值的偏差），
为指定技术推荐参数调整方案，以提高分析准确性。

规则：
1. 只调整给定的可调参数白名单内的参数，不超出范围。
2. 每次最多调整 4 个参数。优先调整低风险参数；高风险参数（arpls_lam、max_peaks）
   仅在明确必要时调整，且必须提供详细理由。
3. 物理合规性（PHYS）是硬约束——绝对不能推荐导致输出超出物理范围的参数。
4. 优先参考历史成功案例中相同聚合物的参数组合。
5. 如果参考峰位偏差 > 0.3°（WAXS）/ > 5 cm⁻¹（IR）/ > 1 ppm（NMR），
   优先调整与峰位校准或基线相关的参数。
6. 如果残差有系统性结构（非随机分布），优先考虑增加模型复杂度（加峰/加 halo）
   而非降平滑。
7. 输出必须为严格的 JSON 格式，包含 analysis、changes、reasoning、
   expected_improvement、risk、risk_note 字段。
8. **拒绝能力**：如果当前拟合已经很好（PHYS=100%, PEAK < 容差, 残差随机），
   在 `changes` 中返回空对象 `{}`，`analysis` 中说明"当前参数已最优，无需调整"。
   不要为了调而调——"不调"也是合法的 Agent 决策。
```

### User Prompt 模板（以 WAXS 为例）

```
## 当前任务
聚合物: {polymer_name} ({polymer_phase or "未指定相"})
技术: WAXS ({submodule})
数据文件: {data_file}

## 当前参数
{current_config_table}

## 分析结果
- 结晶度 Xc: {Xc_pct}%（方法: {Xc_method}）
- 拟合 R²: {r_squared}
- Reduced χ²: {redchi}
- 检测到 {n_peaks} 个衍射峰
- 晶粒尺寸 D_Scherrer: {D_Scherrer_nm} nm
- 晶系: {crystal_system}
- 质量标记: {quality_flags}
- 残差模式: {residuals_pattern}

## 峰详情
{peaks_table}

## 参考知识（聚合物数据库）
{reference_peaks_list}
{physical_bounds}

## 历史成功案例
{similar_cases_summary}

## 可调参数白名单
{tunable_params_table}

请分析当前拟合质量，推荐参数调整方案。输出 JSON。
```

## 13.7 闭环深度策略

分两个阶段实现：

### B 层闭环（Phase 4 实现）——仅迭代 analyze

```
load(data)  →  preprocess()  →  ┌─ analyze() ←── Agent 改参数 ─┐
                                  │       ↓                     │
                                  │   QualityEvaluator          │
                                  │       ↓                     │
                                  │   收敛？→ 否 → 继续 ────────┘
                                  │   是 → 输出最优参数
                                  └────────────────
```

- **优点**：analyze() 重跑快（秒级），不需要重新加载文件和预处理
- **限制**：不调整预处理参数（基线方法、平滑窗口等在 preprocess 阶段的参数需要在下一阶段支持）
- **最大轮数**：5

### C 层闭环（Phase 5 实现）——全管线迭代

```
load(data)  →  ┌─ preprocess()  ←── Agent 改预处理参数 ─┐
               │       ↓                                │
               │   analyze()  ←── Agent 改分析参数 ─────┤
               │       ↓                                │
               │   QualityEvaluator                     │
               │       ↓                                │
               │   收敛？→ 否 → 继续 ───────────────────┘
               │   是 → 输出最优参数
               └────────────────
```

- **扩展**：Agent 可调整预处理参数（smooth_window、background_method、arpls_lam）
- **代价**：每轮需要重跑 preprocess + analyze，可能涉及 pyFAI 积分（较慢）
- **最大轮数**：10

### 实现策略

先做 B（验证 Agent 核心逻辑正确），再做 C（扩展覆盖面）。B 跑通后，C 只是多加了几个可调参数 + 把 `preprocess()` 也纳入迭代循环。

## 13.8 Agent 评估方案

### A/B 测试设计

对 Eval 数据集中的每个 case：

| 组 | 参数来源 | 说明 |
|----|---------|------|
| **Baseline** | 默认 Config 参数 | 当前软件的行为 |
| **Agent-B** | B 层闭环（最多 5 轮） | 测试 Agent 的核心调参能力 |
| **Agent-C** | C 层闭环（最多 10 轮） | 测试 Agent 的完整调参能力 |

### 评估指标

| 指标 | 含义 |
|------|------|
| EvalScore 均值 | 综合分（§12.2）在全部 eval case 上的平均 |
| EvalScore 提升 | (Agent - Baseline) / Baseline × 100% |
| 收敛轮数 | Agent 平均几轮收敛 |
| 物理不可行率 | Agent 建议导致 PHYS < 1.0 的比例 |

### 成功标准

```
✅ 通过: Agent-B 的 EvalScore 比 Baseline 提升 ≥ 10%
✅ 合成数据 PHYS 100%, PEAK < 0.1°
✅ 真实数据 PHYS ≥ 95%, PEAK < 0.3°
✅ Agent 收敛轮数均值 ≤ 3
✅ 物理不可行率为 0%（回滚保护生效）
```

---

# §14 实施路线图

| Phase | 内容 | 优先级 | 代码量 | 依赖 |
|-------|------|--------|--------|------|
| **Phase 0** | Eval 框架：`EvalCase` / `GroundTruth` / `EvalMetric` / `EvalRunner` 数据模型 + 运行器 | P0 | ~500 行 | 无 |
| **Phase 1** | C 路线：合成数据生成器 + 15 个合成 EvalCase（WAXS×5 + DSC×4 + SAXS×3 + IR×3 + NMR×3） | P0 | ~500 行 | Phase 0 |
| **Phase 2** | B 路线：`audit_reporter.py` 自动重跑 + 审计报告生成 + 人工审阅后自动写入 EvalCase | P0 | ~350 行 | Phase 0 |
| **Phase 3** | RAG 基础设施：`polynexus/rag/` 模块，ChromaDB 向量库 + DeepSeek 客户端 + 知识加载器 | P1 | ~600 行 | Phase 0（需 EvalRunner 做验证） |
| **Phase 4** | Agent 核心（B 层）：`ParameterAgent` + `QualityEvaluator` + `ParameterOrchestrator` + Prompt 模板 | P1 | ~800 行 | Phase 3 + Phase 1 |
| **Phase 4b** | 桥接层：Engine Bridge + Config Bridge + Orchestrator Loop（将 rag/ 原型接入 polynexus 真实引擎） | P1 | ~700 行 | Phase 4 + Phase 0 |
| **Phase 5** | CLI 集成（`--ai-tune` + `--dry-run`）+ GUI "AI 调参"按钮 + C 层闭环扩展 + Eval 上的 A/B 测试 | P2 | ~500 行 | Phase 4b + Phase 2 |

**总代码量估算：~3,950 行 Python（含 ~700 行桥接层）+ ~500 行 JSON（eval cases）+ ~300 行 Markdown（prompt 模板）**

**关键里程碑：**

```
Week 1-2: Phase 0 + 1 → 合成 eval 集可运行，EvalRunner --dry-run 可做 CI 检查
Week 2-3: Phase 2       → 审计报告（含 diff 视图）生成，人工审阅 15 个真实 case
Week 3-4: Phase 3       → RAG 知识库可检索，DeepSeek 可调用，embedding 双模式就绪
Week 4-5: Phase 4       → Agent B 层闭环可运行（Advisor + Prompt），在合成 eval 上验证
Week 5-7: Phase 4b      → 桥接层（§15），~9 天：Engine Bridge + Config Bridge + Orchestrator
                           + ResidualAnalyzer + CLI/GUI 入口
Week 7-9: Phase 5       → 真实 eval A/B 测试 + 调优 + 扩展 DSC/SAXS（按多技术优先级）
```

**依赖说明**：
- `chromadb` — 新增 pip 依赖（`chromadb>=0.5`）
- `openai` — 用于 DeepSeek API 调用（兼容 OpenAI SDK）。如果已有 `openai` 包则无需新加
- 其他依赖（numpy, scipy, lmfit 等）已在 v4.0 的 `pyproject.toml` 中

### 多技术扩展优先级

当前 eval 数据集以 WAXS 最完善（15 个真实 + 5 个合成 case），其他技术合成 case 已就绪但真实标注 case 待补充。Agent 按以下顺序逐技术扩展：

| 优先级 | 技术 | 理由 | 参数数 | 真实case | 合成case |
|--------|------|------|--------|---------|---------|
| 1️⃣ | **WAXS** | 参数最多（22 个）、测试数据最全（静态/变温/拉伸）、已为默认分析主力 | 22 | 15 | 5 |
| 2️⃣ | **DSC** | 参数少（5 个）、合成 case 已就绪、真实数据丰富（FXY-PA6 等）、与 WAXS 交叉验证价值高（φc triple） | 5 | 0* | 4 |
| 3️⃣ | **SAXS** | 参数中等（6 个）、EDF 积分在现有管线已支持、真实数据多（5 个数据集）、与 DSC 交叉验证价值高（Tm bidirectional） | 6 | 0* | 3 |
| 4️⃣ | **IR** | 参数少（4 个）、SPA 格式已支持、变温 IR 是差异化亮点（2D-COS） | 4 | 0* | 3 |
| 5️⃣ | **NMR** | 参数少（4 个）、但固体 NMR JEOL .jdf/.bin 格式最复杂、液体谱更稳定、建议最后攻克 | 4 | 0* | 3 |

> \* 真实 case 需在 Phase 2 审阅阶段补充标注。当前 `tests/eval/cases/real/` 仅有 WAXS 的 15 个 case。
> 
> 每扩展一个技术，需补充：① 真实数据审阅标注（~1-2 小时/技术）② `TECHNIQUE_CONFIG_MAP` 参数映射 ③ Agent prompt 中该技术的专用规则 ④ 至少 1 个端到端测试（合成 case 跑通 Agent 闭环）。



---

# §15 桥接实施计划

> **现状**：Phase 0-3 已基本完成，但 `rag/`、`llm/`、`tests/eval/` 三个模块与 PolyNexus 软件本体**零连接**——没有任何一行 `import polynexus`。本章描述如何将孤立原型接入真实引擎管线。

---

## 15.1 现状诊断

```
┌─────────────────────────────┐    ┌──────────────────────────────┐
│  PolyNexus 软件本体 ✓        │    │  RAG/Eval 原型 ⚠️             │
│                             │    │                              │
│  polynexus/core/            │    │  rag/                        │
│  ├── engine.py BaseEngine   │    │  ├── indexer.py → ChromaDB   │
│  ├── waxs.py WAXSEngine     │    │  ├── retriever.py            │
│  ├── saxs.py SAXSEngine     │    │  ├── advisor.py → 文本建议   │
│  ├── dsc.py DSCEngine       │    │  └── prompt_builder.py       │
│  ├── waxs_engine/config.py  │    │                              │
│  │   → WAXSConfig (30参数)  │    │  llm/                        │
│  └── ...                    │    │  └── llm_client.py → DeepSeek│
│                             │    │                              │
│  polynexus/data/            │    │  tests/eval/                 │
│  ├── polymers/*.json        │    │  ├── runner.py               │
│  └── sample_db.py → SQLite  │    │  │   → _stub_output_from_gt()│
│                             │    │  │   → 不调任何 Engine！     │
│                             │    │  ├── synth_generator.py      │
│                             │    │  └── cases/                  │
│                             │    │                              │
│  ❌ 无 import rag ──────────┼──── ❌ 无 import polynexus ───────│
└─────────────────────────────┘    └──────────────────────────────┘
```

**四个断点：**

| # | 断点 | 现象 | 后果 |
|---|------|------|------|
| 1 | **EvalRunner 不跑引擎** | `_stub_output_from_ground_truth()` 用 ground truth 中值假装是分析结果，不调任何 Engine | 评测的是自己设的答案，无法反映引擎真实行为 |
| 2 | **Advisor 不认识 Config** | `advise()` 输入输出都是通用 dict，不知道 `WAXSConfig.peak_function` 等字段 | 建议是自然语言，无法写入 Config、无法触发重分析 |
| 3 | **无闭环回路** | Advisor 给建议后没有下一步——没有"改 Config → 重跑 analyze() → 对比结果 → 再调"的循环 | 只是聊天机器人，不是 Agent |
| 4 | **无 CLI/GUI 入口** | 没有 `--ai-tune`，GUI 无 AI 按钮 | 用户无法从软件内触发 |

## 15.2 总体策略

### 资产复用 vs 改造 vs 新建

| 模块 | 处理方式 | 理由 |
|------|---------|------|
| `rag/indexer.py` | ✅ 保留，加 `index_from_analysis_runs()` | 当前只索引 eval 结果 JSON；需扩展索引真实 `analysis_runs` 表 |
| `rag/retriever.py` | ✅ 保留，加时间衰减权重 | 方案 §13.2 的衰减策略未实现 |
| `rag/advisor.py` | 🔧 改造 system prompt + 输出 schema | 从通用"建议"改为方案 §13.3 的结构化 `{"changes": {...}}` |
| `rag/prompt_builder.py` | 🔧 改造，加技术专用参数白名单 | 当前只输出通用字段，需嵌入可调参数表 |
| `llm/llm_client.py` | ✅ 保留，加 `system_prompt` 参数 | 当前只支持 user message，需支持 system role |
| `tests/eval/runner.py` | 🔧 改造 `run_case()` | 替换 `_stub_output`，改为真实 engine 调用 |
| `tests/eval/models.py` | ✅ 保留 | 无需改 |
| `polynexus/core/engine.py` | 🆕 加 `run_pipeline_from_arrays()` | 合成数据无文件格式头，需数组注入 |
| — | 🆕 新建 `polynexus/orchestrator.py` | 闭环逻辑（改 Config → 重分析 → 评估 → 收敛） |
| — | 🆕 新建 `polynexus/config_bridge.py` | `TECHNIQUE_CONFIG_MAP` + `apply_changes()` + 依赖约束校验 |
| `polynexus/__main__.py` | 🆕 加 `--ai-tune` | CLI 入口 |
| `polynexus/gui/main_window.py` | 🆕 加 AI 调参按钮 | GUI 入口 |

## 15.3 Engine Bridge — EvalRunner 调用真实引擎

> **无需额外实现积分**：现有软件管线已完整覆盖 `.raw`/`.edf` → 1D 曲线。
> `.raw`（Rigaku 格式）由 `readers/raw_reader.py` 直接读取 1D 数据；
> `.edf`（2D 探测器）由 `waxs_engine/preprocess.py` 的 `integrate_2d_to_1d()` 处理——
> 优先使用 pyFAI（从 EDF header 自动提取几何参数：SDD、像素尺寸、beam center、波长），
> pyFAI 不可用时 fallback 到手动径向积分 `_manual_radial_integration()`。
> **不需要 `.poni` 标定文件**。eval case 中 `数据文件` 路径直接传给 `engine.run_pipeline()` 即可。

### 15.3.1 修改 `EvalRunner.run_case()`

当前：

```python
def run_case(self, case: EvalCase) -> EvalResult:
    output = self._stub_output_from_ground_truth(case)  # ← 假数据
    return self.compute_metrics(case, output)
```

改为：

```python
def run_case(self, case: EvalCase) -> EvalResult:
    output = self._run_real_engine(case)  # ← 真实引擎
    return self.compute_metrics(case, output)
```

### 15.3.2 `_run_real_engine()` 分两路

```python
def _run_real_engine(self, case: EvalCase) -> dict:
    if case.data_file.startswith("synth:"):
        return self._run_synth(case)   # 数组注入
    else:
        return self._run_real_data(case)  # 文件管线
```

**合成数据路径**：从 `.xy` 文件（两列 `x y`）读 numpy 数组，注入到 engine：

```python
def _run_synth(self, case: EvalCase) -> dict:
    from polynexus.core.engine import get_engine

    xy_path = self.eval_root / "synth_data" / f"{case.data_file.split(':',1)[1]}.xy"
    data = np.loadtxt(xy_path)
    x, y = data[:, 0], data[:, 1]

    engine = get_engine(case.technique, config=self._build_config(case))
    engine.run_pipeline_from_arrays(x, y, config_overrides=case.config_overrides)

    return {
        "parameters_used": engine.config.to_dict(),
        "output_parameters": engine.result.parameters,
    }
```

**真实数据路径**：直接调现有管线：

```python
def _run_real_data(self, case: EvalCase) -> dict:
    from polynexus.core.engine import get_engine

    data_path = self.resolve_data_file(case.data_file)
    engine = get_engine(case.technique, config=self._build_config(case))
    engine.run_pipeline(str(data_path), output_dir="", 
                        skip_to=None, config_overrides=case.config_overrides)

    return {
        "parameters_used": engine.config.to_dict(),
        "output_parameters": engine.result.parameters,
    }
```

### 15.3.3 在 `BaseEngine` 加 `run_pipeline_from_arrays()`

```python
class BaseEngine(ABC):
    def run_pipeline_from_arrays(self, x, y, config_overrides=None) -> AnalysisResult:
        """Run analysis on raw numpy arrays (no file I/O)."""
        self.result = AnalysisResult(technique=self.name, category=self.category)
        if config_overrides:
            self._apply_config_overrides(config_overrides)
        if not self.load_from_arrays(x, y): return self.result
        if not self.preprocess(): return self.result
        if not self.analyze(): return self.result
        self.result.parameters = self.get_parameters()
        return self.result
```

各技术 engine 需实现 `load_from_arrays(x, y)`——将数组包装为该技术的数据结构（如 WAXS 的 `WAXSDataset`），跳过文件解析。

### 15.3.4 合成数据文件格式

当前 `synth_data/*.xy` 是两列纯文本，需增加元数据头以适配各技术的 load 逻辑。方案：统一用 JSON 包装：

```json
{
  "technique": "waxs",
  "x_label": "2theta_deg",
  "y_label": "intensity",
  "x": [10.0, 10.05, ...],
  "y": [120.5, 118.3, ...]
}
```

或保持 `.xy` 纯文本 + 在 `synth_generator.py` 生成时追加 `# technique=waxs` 头行。

### 15.3.5 ResidualAnalyzer — 残差模式自动分析

`AgentState.residuals_pattern` 字段（§13.3）需要自动生成而非人工填写。新建 `polynexus/core/residual_analyzer.py`（~80 行）：

```python
def analyze_residuals(x: np.ndarray, y_fit: np.ndarray, y_obs: np.ndarray) -> str:
    """Analyze fit residuals and return a qualitative pattern description.
    
    Returns one of:
    - "随机分布" — white noise, no visible structure
    - "N-M° 系统偏置" — systematic bias in segment N-M°
    - "低角区漂移" — drift at low angles
    - "高角区振荡" — oscillation at high angles
    - "全局偏移" — constant offset
    """
    residuals = y_obs - y_fit
    
    # 1. Segment analysis: split into 3 regions, check mean deviation
    n = len(x)
    thirds = [(0, n//3), (n//3, 2*n//3), (2*n//3, n)]
    segment_means = []
    for lo, hi in thirds:
        seg_res = residuals[lo:hi]
        if len(seg_res) > 10:
            segment_means.append(np.mean(seg_res))
    
    threshold = 0.02 * (np.max(y_obs) - np.min(y_obs))
    biased_segments = [
        (i, m) for i, m in enumerate(segment_means) 
        if abs(m) > threshold
    ]
    if biased_segments:
        region_labels = ["低角区", "中角区", "高角区"]
        parts = [f"{region_labels[i]}" for i, _ in biased_segments]
        return f"{'、'.join(parts)}系统偏置"
    
    # 2. Durbin-Watson test for autocorrelation
    diff = np.diff(residuals)
    dw = np.sum(diff**2) / np.sum(residuals**2) if np.sum(residuals**2) > 0 else 2.0
    if dw < 1.0:
        return "残差正自相关（模型欠拟合，缺少特征）"
    if dw > 3.0:
        return "残差负自相关（可能过拟合）"
    
    # 3. Heteroscedasticity check
    abs_res = np.abs(residuals)
    slope, _ = np.polyfit(x, abs_res, 1)
    if abs(slope) > threshold / (x[-1] - x[0]):
        direction = "递增" if slope > 0 else "递减"
        return f"残差幅度随2θ{direction}（异方差性）"
    
    return "随机分布"
```

此函数在 `_build_agent_state()` 中调用，自动填充 `residuals_pattern`。

## 15.4 Config Bridge — Advisor 输出驱动真实 Config

### 15.4.1 每技术的参数映射表

```python
TECHNIQUE_CONFIG_MAP = {
    "waxs": {
        # param_name: (config_field, type, choices_or_range)
        "peak_function": ("peak_function", str, ["gaussian","lorentzian","pseudo_voigt"]),
        "smooth_window": ("smooth_window", int, (3, 15)),
        "background_method": ("background_method", str, ["linear","polynomial","spline","chebyshev"]),
        "arpls_lam": ("arpls_lam", float, (1e4, 1e8)),
        "amorphous_subtraction": ("amorphous_subtraction", str, ["spline","polynomial","manual"]),
        "amorphous_n_peaks": ("amorphous_n_peaks", int, (1, 2)),
        "peak_distance": ("peak_distance", float, (0.5, 2.0)),
        "two_theta_offset": ("two_theta_offset", float, (-0.5, 0.5)),
        "max_peaks": ("max_peaks", int, (4, 12)),
    },
    "saxs": { ... },
    "dsc": { ... },
    "ir": { ... },
    "nmr": { ... },
}
```

### 15.4.2 `apply_changes()` 函数

```python
def apply_changes(config, changes: dict, technique: str) -> tuple[bool, str]:
    """Validate and apply parameter changes to a Config dataclass.
    Returns (success, error_message).
    """
    param_map = TECHNIQUE_CONFIG_MAP.get(technique, {})
    for param_name, new_value in changes.items():
        if param_name not in param_map:
            return False, f"Unknown parameter: {param_name}"
        field_name, expected_type, constraint = param_map[param_name]

        # Type validation
        if not isinstance(new_value, expected_type):
            return False, f"{param_name}: expected {expected_type.__name__}, got {type(new_value).__name__}"

        # Range/choices validation
        if isinstance(constraint, list):  # choices
            if new_value not in constraint:
                return False, f"{param_name}: '{new_value}' not in {constraint}"
        elif isinstance(constraint, tuple):  # (min, max)
            if not (constraint[0] <= new_value <= constraint[1]):
                return False, f"{param_name}: {new_value} out of range {constraint}"

        # Apply
        setattr(config, field_name, new_value)

    # Check parameter dependencies (§13.5)
    dep_error = _check_dependencies(config, changes, technique)
    if dep_error:
        return False, dep_error

    return True, ""
```

### 15.4.3 依赖约束检查

```python
DEPENDENCY_RULES = {
    "waxs": [
        ("arpls", ["arpls_lam", "arpls_diff_order"],
         "arpls_lam 和 arpls_diff_order 不应同时修改"),
        ("crystallinity_window", ["crystallinity_min_two_theta", "crystallinity_max_two_theta"],
         lambda c: c.crystallinity_min_two_theta < c.crystallinity_max_two_theta - 10),
        ("amorphous", ["amorphous_subtraction", "amorphous_n_peaks"],
         "先定 subtraction 方法，再根据残差调 n_peaks"),
    ],
}

def _check_dependencies(config, changes: dict, technique: str) -> str | None:
    """Return error string if dependency rules are violated."""
    rules = DEPENDENCY_RULES.get(technique, [])
    for rule_name, params, check in rules:
        changed_params = [p for p in params if p in changes]
        if callable(check):
            if any(p in changes for p in params) and not check(config):
                return f"依赖约束 [{rule_name}] 不满足: {params}"
        elif len(changed_params) > 1:
            return f"依赖约束 [{rule_name}]: {check}"
    return None
```

### 15.4.4 改造 Advisor 的 Prompt

修改 `rag/prompt_builder.py`——在 prompt 中嵌入可调参数白名单（从 `TECHNIQUE_CONFIG_MAP` 读取），LLM 输出从通用 JSON 改为：

```json
{
  "assessment": "WARN",
  "confidence": 0.82,
  "reasoning": "...",
  "changes": {
    "peak_function": "pseudo_voigt",
    "amorphous_n_peaks": 2
  },
  "expected_improvement": {
    "r_squared": "0.986 → 0.993+",
    "Xc_pct": "38.2% → 42-46%"
  },
  "risk": "low"
}
```

`Advisor.advise()` 返回的 dict 增加 `"changes"` 字段，供 Orchestrator 直接传给 `apply_changes()`。

## 15.5 Orchestrator Loop — 迭代闭环

### 15.5.1 模块位置

新建 `polynexus/orchestrator.py`——这是桥接层的中枢，同时 import `rag/` 和 `polynexus.core/`。

### 15.5.2 ParameterOrchestrator 类

```python
@dataclass
class RoundRecord:
    round_num: int
    config_snapshot: dict
    eval_result: EvalResult
    llm_advice: dict | None  # None for baseline round

class ParameterOrchestrator:
    def __init__(self, technique: str, submodule: str, data_file: str,
                 polymer_name: str, max_rounds: int = 5,
                 convergence_threshold: float = 0.01):
        self.technique = technique
        self.submodule = submodule
        self.data_file = data_file
        self.polymer_name = polymer_name
        self.max_rounds = max_rounds
        self.convergence_threshold = convergence_threshold
        self.history: list[RoundRecord] = []
        self.best_config = None
        self.best_score = -1.0

    def run(self) -> dict:
        """Main loop: baseline → advise → apply → rerun → evaluate → converge."""
        # Round 0: baseline
        engine = get_engine(self.technique)
        engine.run_pipeline(self.data_file)
        baseline_result = self._evaluate(engine, round_num=0)

        self.history.append(RoundRecord(0, engine.config.to_dict(),
                                         baseline_result, None))
        self.best_config = deepcopy(engine.config)
        self.best_score = baseline_result.composite

        # Rounds 1..N
        for round_num in range(1, self.max_rounds + 1):
            # 1. Get advice
            advisor = Advisor()
            state = self._build_agent_state(engine, round_num)
            advice = advisor.advise(state)

            # 2. Check for "no change needed"
            if not advice.get("changes"):
                self._log(f"Round {round_num}: Agent 判定已最优，退出")
                break

            # 3. Apply changes
            new_config = deepcopy(engine.config)
            ok, err = apply_changes(new_config, advice["changes"], self.technique)
            if not ok:
                self._log(f"Round {round_num}: apply_changes 失败: {err}，回滚")
                continue  # retry with feedback to LLM

            # 4. Rerun
            engine.config = new_config
            engine.analyze()  # only re-analyze, no reload
            cur_result = self._evaluate(engine, round_num)

            # 5. Record & check convergence
            self.history.append(RoundRecord(round_num, new_config.to_dict(),
                                             cur_result, advice))
            if cur_result.composite > self.best_score:
                self.best_config = deepcopy(new_config)
                self.best_score = cur_result.composite

            if self._has_converged(cur_result.composite, self.best_score):
                self._log(f"Round {round_num}: 收敛 (Δ<{self.convergence_threshold})")
                break

        return self._final_report()

    def _evaluate(self, engine, round_num: int) -> EvalResult:
        """Build EvalResult from engine output."""
        from tests.eval.runner import EvalRunner
        # Map AnalysisResult to generic output dict
        output = {
            "output_parameters": engine.result.parameters,
            "parameters_used": engine.config.to_dict(),
        }
        # Build a minimal EvalCase for compute_metrics
        case = EvalCase(
            case_id=f"live_{self.polymer_name}_{self.technique}",
            technique=self.technique,
            submodule=self.submodule,
            data_file=self.data_file,
            polymer_name=self.polymer_name,
            polymer_phase=None,
            config_overrides={},
            ground_truth=GroundTruth(),  # empty — no ground truth available live
            source="expert_review",
            notes="live orchestration",
        )
        return EvalRunner().compute_metrics(case, output)

    def _has_converged(self, current: float, best: float) -> bool:
        if best <= 0 or current <= 0:
            return False
        return (current - best) / best < self.convergence_threshold

    def _build_agent_state(self, engine, round_num: int) -> dict:
        return {
            "technique": self.technique,
            "polymer_name": self.polymer_name,
            "params": engine.config.to_dict(),
            "output_parameters": engine.result.parameters,
            "round": round_num,
            "previous_score": self.best_score,
        }
```

### 15.5.3 收敛判断的两种模式

| 条件 | 动作 |
|------|------|
| `ΔEvalScore < 1%` | 正常收敛，输出最优 Config |
| Agent 返回空 `changes` | 提前终止，标记 `converged: optimal` |
| `apply_changes` 返回 error | 回滚到 best_config，向 LLM 反馈错误原因，继续下一轮 |
| 新结果 PHYS 下降 | 回滚到 best_config，标记该方向为 `rejected` |
| 达到 `max_rounds` | 强制终止，输出 best_config |

### 15.5.4 产出报告

```json
{
  "technique": "waxs",
  "polymer_name": "PA6",
  "data_file": "测试数据/waxs/普通广角/PA6.raw",
  "rounds": 3,
  "converged": true,
  "best_config": { "peak_function": "pseudo_voigt", "amorphous_n_peaks": 2, ... },
  "improvement": { "composite": "0.78 → 0.94 (+20.5%)" },
  "history": [ ... ]
}
```

## 15.6 Entry Points

### 15.6.1 CLI — `--ai-tune`

在 `polynexus/__main__.py` 增加：

```python
# 新增参数
p.add_argument('--ai-tune', action='store_true', help='AI-assisted parameter tuning')
p.add_argument('--max-rounds', type=int, default=5, help='Max tuning rounds')
p.add_argument('--polymer', default='', help='Polymer name for RAG lookup')

# 执行逻辑
if args.ai_tune:
    from polynexus.orchestrator import ParameterOrchestrator
    orch = ParameterOrchestrator(
        technique=args.cmd,
        submodule=getattr(args, 'type', 'static'),
        data_file=args.input,
        polymer_name=args.polymer or 'unknown',
        max_rounds=args.max_rounds,
    )
    report = orch.run()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return
```

用法：

```
polynexus waxs 测试数据/waxs/普通广角/PA6.raw --ai-tune --polymer PA6 --max-rounds 5
```

### 15.6.2 GUI — "AI 调参"按钮

在 `main_window.py` 的分析结果面板（右侧参数展示区）底部加一个 `QPushButton("🧠 AI 调参")`：

- 点击 → `QProgressDialog` 显示当前轮数和分数
- 每轮更新 UI：刷新拟合图 + 参数表
- 完成后弹出 `QDialog`：
  - 显示每轮 r²/EvalScore 变化折线
  - 显示建议的参数变更（旧值 → 新值 + 原因）
  - 两个按钮：**[应用最优参数]** / **[取消]**
- "应用最优参数"→ 写回 GUI 的 Config 控件 → 触发重新分析

```python
def on_ai_tune_clicked(self):
    from polynexus.orchestrator import ParameterOrchestrator

    progress = QProgressDialog("AI 正在分析...", "取消", 0, self.max_rounds, self)
    progress.setWindowTitle("AI 调参进行中")

    def run_tuning():
        orch = ParameterOrchestrator(
            technique=self.current_technique,
            data_file=self.current_data_file,
            polymer_name=self.current_polymer_name,
            max_rounds=self.max_rounds,
        )
        for round_num, record in enumerate(orch.run_with_progress()):
            progress.setValue(round_num + 1)
            progress.setLabelText(f"第 {round_num+1} 轮: EvalScore={record.eval_result.composite:.3f}")
            if progress.wasCanceled():
                break

        # Show final report dialog
        self._show_tuning_report(orch.final_report())

    QtCore.QThreadPool.globalInstance().start(run_tuning)
```

## 15.7 实施顺序与验证门

| 步骤 | 内容 | 验证方式 | 预估时间 |
|------|------|---------|---------|
| **Bridge 1** | Engine Bridge：`_run_real_engine()` + `run_pipeline_from_arrays()` + `ResidualAnalyzer`（残差模式自动分析） | `python -m tests.eval.runner --cases-dir tests/eval/cases/synth/` 输出真实引擎结果 | 2.5 天 |
| **Bridge 2** | Config Bridge：`TECHNIQUE_CONFIG_MAP` + `apply_changes()` + 修改 Advisor prompt | 单元测试：输入 `{"peak_function":"pseudo_voigt"}` → 检查 `WAXSConfig.peak_function` 改变 | 1.5 天 |
| **Bridge 3** | Orchestrator：`ParameterOrchestrator` + 收敛 + 回滚 + 与 Advisor 双向通信 + 集成测试 | 单元测试 + 对一个合成 case 跑 3 轮确认 r² 单调不降 + 回滚场景覆盖 | 3 天 |
| **Bridge 4a** | CLI `--ai-tune` | `polynexus waxs tests/eval/synth_data/waxs_synth_pa6_alpha.xy --ai-tune` | 0.5 天 |
| **Bridge 4b** | GUI "AI 调参"按钮 | 手动在 GUI 中点击，确认进度条、报告对话框、参数回写 | 1.5 天 |

**总计**：~9 天（含 Bridge 3 多 1 天用于收敛/回滚/双向通信的充分测试）。Phase 4b（桥接层）嵌入在 Phase 4 和 Phase 5 之间，不单独占一个 Phase。

---

# 附录

---

## 附录 C：EvalCase JSON schema 完整定义

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "EvalCase",
  "type": "object",
  "required": ["case_id", "technique", "data_file", "polymer_name", "ground_truth", "source"],
  "properties": {
    "case_id": {
      "type": "string",
      "description": "唯一标识，如 waxs_synth_pa6_alpha_001"
    },
    "technique": {
      "type": "string",
      "enum": ["waxs", "dsc", "saxs", "ir", "nmr"]
    },
    "submodule": {
      "type": "string",
      "description": "static | strain | temperature | isothermal | nonisothermal | liquid_h | liquid_c | solid_h | solid_c"
    },
    "data_file": {
      "type": "string",
      "description": "相对 测试数据/ 的路径，如 waxs/普通广角/PA6.raw；合成数据以 synth: 前缀"
    },
    "polymer_name": { "type": "string" },
    "polymer_phase": { "type": ["string", "null"] },
    "config_overrides": {
      "type": "object",
      "description": "覆盖默认 Config 的参数"
    },
    "ground_truth": {
      "type": "object",
      "properties": {
        "Xc_pct": {
          "type": "array",
          "minItems": 2, "maxItems": 2,
          "items": { "type": "number" },
          "description": "[min, max] 范围，null 表示不检查"
        },
        "peak_centers": {
          "type": "array",
          "items": {
            "type": "array",
            "minItems": 2, "maxItems": 2,
            "items": { "type": "number" }
          },
          "description": "WAXS: [(19.7, 20.3), (23.7, 24.3)]; IR: [(1630, 1645)]; NMR: [(170, 175)]"
        },
        "D_Scherrer_nm": { "type": "array", "minItems": 2, "maxItems": 2, "items": { "type": "number" } },
        "crystal_form": { "type": ["string", "null"] },
        "Tm_peak_C": { "type": "array", "minItems": 2, "maxItems": 2, "items": { "type": "number" } },
        "DHm_Jg": { "type": "array", "minItems": 2, "maxItems": 2, "items": { "type": "number" } },
        "Tg_C": { "type": "array", "minItems": 2, "maxItems": 2, "items": { "type": "number" } },
        "Tc_peak_C": { "type": "array", "minItems": 2, "maxItems": 2, "items": { "type": "number" } },
        "L_nm": { "type": "array", "minItems": 2, "maxItems": 2, "items": { "type": "number" } },
        "lc_nm": { "type": "array", "minItems": 2, "maxItems": 2, "items": { "type": "number" } },
        "Rg_nm": { "type": "array", "minItems": 2, "maxItems": 2, "items": { "type": "number" } },
        "phi_c": { "type": "array", "minItems": 2, "maxItems": 2, "items": { "type": "number" }, "description": "SAXS 结晶度" }
      }
    },
    "source": {
      "type": "string",
      "enum": ["synthetic", "literature", "cross_validation", "expert_review"],
      "description": "ground truth 来源"
    },
    "notes": { "type": "string" }
  }
}
```

### 示例：合成 WAXS case

```json
{
  "case_id": "waxs_synth_pa6_alpha_001",
  "technique": "waxs",
  "submodule": "static",
  "data_file": "synth:waxs_pa6_alpha_001",
  "polymer_name": "PA6",
  "polymer_phase": "alpha",
  "config_overrides": {
    "polymer_type": "PA6_alpha"
  },
  "ground_truth": {
    "Xc_pct": [42, 48],
    "peak_centers": [[19.85, 20.15], [23.85, 24.15]],
    "D_Scherrer_nm": [8, 15],
    "crystal_form": "alpha"
  },
  "source": "synthetic",
  "notes": "合成数据：PA6 α 晶型双峰 + 1 非晶 halo，Poisson 噪声，rng_seed=42"
}
```

---

## 附录 D：各技术可调参数完整列表

### D.1 WAXS — WAXSConfig 可调参数

| # | 字段 | 类型 | 默认值 | 范围/选项 | 所属阶段 | 风险 |
|---|------|------|--------|----------|---------|------|
| 1 | `wavelength_A` | float | 1.5406 | 0.5–2.5 | preprocess | 低 |
| 2 | `polarisation_factor` | float | 0.0 | 0.0–1.0 | preprocess | 低 |
| 3 | `background_method` | str | linear | linear/polynomial/spline/chebyshev | preprocess | 中 |
| 4 | `background_order` | int | 1 | 1–5 | preprocess | 中 |
| 5 | `smooth_method` | str | savgol | savgol/none | preprocess | 低 |
| 6 | `smooth_window` | int | 5 | 3–15 (奇数) | preprocess | 中 |
| 7 | `smooth_order` | int | 3 | 1–5 | preprocess | 低 |
| 8 | `peak_function` | str | pseudo_voigt | gaussian/lorentzian/pseudo_voigt | analyze | 低 |
| 9 | `peak_height_min` | float | 0.01 | 0.005–0.10 | analyze | 中 |
| 10 | `peak_distance` | float | 0.8 | 0.3–2.0 | analyze | 低 |
| 11 | `max_peaks` | int | 8 | 4–12 | analyze | 高 |
| 12 | `min_two_theta` | float | 8.0 | 5.0–15.0 | analyze | 低 |
| 13 | `arpls_lam` | float | 1e5 | 1e4–1e8 | preprocess | 高 |
| 14 | `arpls_diff_order` | int | 2 | 1–2 | preprocess | 低 |
| 15 | `crystallinity_method` | str | peak_deconvolution | peak_deconvolution/peak_area/ruland | analyze | 低 |
| 16 | `polymer_type` | str | "" | PA6_alpha/PA6_gamma/PE/iPP_alpha/... | analyze | 低 |
| 17 | `amorphous_n_peaks` | int | 2 | 1–2 | analyze | 中 |
| 18 | `amorphous_subtraction` | str | polynomial | spline/polynomial/manual | analyze | 中 |
| 19 | `crystallinity_min_two_theta` | float | 15.0 | 10.0–20.0 | analyze | 低 |
| 20 | `crystallinity_max_two_theta` | float | 35.0 | 25.0–45.0 | analyze | 低 |
| 21 | `two_theta_offset` | float | 0.0 | -0.5–0.5 | preprocess | 低 |
| 22 | `scherrer_K` | float | 0.9 | 0.8–1.0 | analyze | 低 |

B 层闭环覆盖 #8–#20（analyze 阶段）；C 层闭环扩展为全部。

### D.2 SAXS — SAXSConfig 可调参数（部分）

| # | 字段 | 类型 | 默认值 | 范围/选项 | 所属阶段 | 风险 |
|---|------|------|--------|----------|---------|------|
| 1 | `baseline_method` | str | normalize | subtract/normalize/none | preprocess | 低 |
| 2 | `smooth_window` | int | 7 | 3–31 | preprocess | 中 |
| 3 | `q_range_min` | float | 0.01 | 0.001–1.0 | analyze | 中 |
| 4 | `q_range_max` | float | 2.0 | 0.1–10.0 | analyze | 中 |
| 5 | `use_pyfai` | bool | false | true/false | preprocess | 低 |
| 6 | `n_pt` | int | 1000 | 200–5000 | preprocess | 低 |

### D.3 DSC — DSCConfig 可调参数（部分）

| # | 字段 | 类型 | 默认值 | 范围/选项 | 风险 |
|---|------|------|--------|----------|------|
| 1 | `baseline_corr` | str | tangential | linear/tangential/sigmoid | 低 |
| 2 | `Tg_method` | str | half_height | half_height/inflection/onset | 低 |
| 3 | `smooth_window` | int | 5 | 3–15 | 中 |
| 4 | `smooth_order` | int | 3 | 1–5 | 低 |
| 5 | `crystallinity_std` | float | auto | 80–330 J/g | 低 |

### D.4 IR — IRConfig 可调参数（部分）

| # | 字段 | 类型 | 默认值 | 范围/选项 | 风险 |
|---|------|------|--------|----------|------|
| 1 | `baseline_method` | str | als | rubberband/linear/polynomial/als | 低 |
| 2 | `smooth_window` | int | 5 | 3–15 | 中 |
| 3 | `lineshape` | str | lorentzian | lorentzian/gaussian/pseudo_voigt | 低 |
| 4 | `freq_correction_factor` | float | 0.9613 | 0.90–1.00 | 低 |
| 5 | `peak_distance` | float | 10.0 | 5–50 cm⁻¹ | 低 |

### D.5 NMR — NMRConfig 可调参数（部分）

| # | 字段 | 类型 | 默认值 | 范围/选项 | 风险 |
|---|------|------|--------|----------|------|
| 1 | `baseline_method` | str | polynomial | polynomial/linear/spline | 低 |
| 2 | `baseline_order` | int | 5 | 1–9 | 中 |
| 3 | `lb_Hz` | float | 5.0 | 1–20 | 中 |
| 4 | `deconvolution_method` | str | mixed | lorentzian/gaussian/mixed | 低 |

---

## 附录 E：Agent prompt 示例——一次完整的 WAXS 调参对话

### Round 0: Baseline

**输入（User Prompt，精简版）：**

```
## 当前任务
聚合物: PA6 (alpha)
技术: WAXS (static)
数据文件: 测试数据/waxs/普通广角/PA6.raw

## 当前参数
| 参数 | 值 |
|------|-----|
| peak_function | gaussian |
| smooth_window | 5 |
| background_method | linear |
| arpls_lam | 1e5 |
| amorphous_subtraction | polynomial |
| amorphous_n_peaks | 1 |
| peak_distance | 0.8 |
| two_theta_offset | 0.0 |
| max_peaks | 8 |

## 分析结果
- 结晶度 Xc: 38.2%（方法: peak_deconvolution）
- 拟合 R²: 0.986
- Reduced χ²: 2.34
- 检测到 4 个衍射峰
- 晶粒尺寸 D_Scherrer: 10.5 nm
- 质量标记: OK
- 残差模式: 20-25° 区间有微弱系统偏置（非随机），噪声水平正常

## 峰详情
| # | 2θ (°) | d (Å) | FWHM (°) | 归属 | 面积 |
|---|--------|-------|----------|------|------|
| 0 | 20.05 | 4.42 | 0.82 | 200 | 145.2 |
| 1 | 24.02 | 3.70 | 0.95 | 002/202 | 112.8 |
| 2 | 21.30 | 4.17 | 6.50 | (非晶) | 210.5 |
| 3 | 11.20 | 7.89 | 3.20 | (未归属) | 18.3 |

## 参考知识（PA6 alpha）
- 参考峰: 200 @ 20.0° (I=100), 002/202 @ 24.0° (I=80)
- 典型结晶度: 35-55%
- 非晶 halo: 1-2 个宽峰 (中心 ~21°, sigma 5-15°)
- 峰位偏差: 200 峰 Δ=0.05°, 002/202 峰 Δ=0.02° → 均 OK

## 历史成功案例
- PA6 α WAXS: peak_function=pseudo_voigt, amorphous_n_peaks=2,
  smooth_window=5, arpls_lam=1e5 → R²=0.997, Xc=43.2%
- PA6 α WAXS: peak_function=pseudo_voigt, amorphous_n_peaks=2,
  smooth_window=7, arpls_lam=5e5 → R²=0.995, Xc=44.8%

## 可调参数白名单
| 参数 | 当前值 | 范围 | 风险 |
|------|--------|------|------|
| peak_function | gaussian | gaussian/lorentzian/pseudo_voigt | 低 |
| smooth_window | 5 | 3-15 | 中 |
| background_method | linear | linear/polynomial/spline/chebyshev | 中 |
| arpls_lam | 1e5 | 1e4-1e8 | 高 |
| amorphous_subtraction | polynomial | spline/polynomial/manual | 中 |
| amorphous_n_peaks | 1 | 1-2 | 中 |
| peak_distance | 0.8 | 0.3-2.0 | 低 |
| two_theta_offset | 0.0 | -0.5-0.5 | 低 |
| max_peaks | 8 | 4-12 | 高 |
```

**DeepSeek 输出（JSON）：**

```json
{
  "analysis": "当前 R²=0.986 尚可但未达最佳。主要问题：\n
    1. 残差在 20-25° 有系统结构 → 1 个 halo 不足以描述非晶散射，PA6 的非晶包络通常需要 2 个宽峰\n
    2. 结晶度 38.2% 偏 PA6 α 典型范围的下限（35-55%），可能与 halo 模型不充分有关（部分 halo 面积应归为晶峰）\n
    3. gaussian 峰函数对实测峰形的尾部拟合不够（实测峰通常有 Lorentzian 分量）\n
    4. 峰 3 (11.2°) 面积极小 (2.6%)，可能是基线残留而非真实峰\n
    5. 峰位偏差极小（< 0.05°）→ 校准正确，不需要调整 two_theta_offset",
  "changes": {
    "peak_function": "pseudo_voigt",
    "amorphous_n_peaks": 2
  },
  "reasoning": {
    "peak_function": "pseudo_voigt 结合 Gaussian 和 Lorentzian，更准确地描述聚合物 WAXS 峰的 Voigt 特征。历史成功案例全部使用 pseudo_voigt，R² 达 0.995-0.997",
    "amorphous_n_peaks": "PA6 非晶散射已知具双峰结构（~21° + ~24° 低宽肩）。当前 1 个 halo (FWHM=6.5°) 无法分辨此结构，导致残差 20-25° 系统偏置。加第 2 个 halo 预期消除此结构，同时 Xc 回升至 42%+"
  },
  "expected_improvement": {
    "r_squared": "0.986 → 0.993+",
    "Xc_pct": "38.2% → 42-46%"
  },
  "risk": "low",
  "risk_note": "两个改动都是低风险：pseudo_voigt 只增 1 个 fraction 参数；第 2 个 halo 增 3 个参数。对 600+ 数据点的 WAXS 谱而言，4 个额外参数不会导致过拟合。无需触碰高风险参数 (arpls_lam, max_peaks)"
}
```

### Round 1: 应用 + 重分析

参数变更：`peak_function` → pseudo_voigt, `amorphous_n_peaks` → 2。重跑 analyze。

**新结果：**
- R²: 0.994（↑ 0.008）
- Xc: 44.1%（进入 42-46% 预期）
- 残差模式: 随机分布（无系统结构）✅
- PHYS: 100%
- PEAK: Δ2θ 均 < 0.1°

收敛判定：EvalScore 改善 > 1%，但残差已随机 → **建议收敛**。

Agent 输出最终参数并标记为推荐方案。

---

*文档结束*
*本方案为 PolyNexus v4.1 AI 增强补充方案，需 v4.0 框架作为前置基础。*
